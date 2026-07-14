#!/usr/bin/env python3
"""Passive SystemMonitor bridge for JANUS A18.43.

Lineage: Hawkar-usls/Janus-Demiurge system_monitor.py.
Reuses passive OHM/NVML/nvidia-smi/psutil collection patterns only.
"""
from __future__ import annotations
import argparse, json, platform, subprocess
from typing import Any
SCHEMA="JANUS/A18.43/system-monitor-bridge/v0.1.1"
OHM_NAMESPACE="root/OpenHardwareMonitor"

def _f(v:Any)->float|None:
    try:
        if v is None or str(v).strip() in {'','N/A','[N/A]'}: return None
        return float(v)
    except (TypeError,ValueError): return None

def normalize_ohm(payload:Any)->list[dict[str,Any]]:
    if isinstance(payload,dict): payload=[payload]
    if not isinstance(payload,list): return []
    rows=[]
    for x in payload:
        if not isinstance(x,dict): continue
        rows.append({'name':x.get('Name'),'identifier':x.get('Identifier'),'parent':x.get('Parent'),'sensor_type':x.get('SensorType'),'value':_f(x.get('Value')),'min':_f(x.get('Min')),'max':_f(x.get('Max')),'index':x.get('Index'),'source':'OpenHardwareMonitor'})
    return sorted(rows,key=lambda r:(str(r['sensor_type']),str(r['identifier'])))

def query_ohm(timeout:float=15.0)->tuple[list[dict[str,Any]],str|None]:
    if platform.system()!='Windows': return [],'WINDOWS_REQUIRED'
    ps=r"""$ErrorActionPreference='Stop'; try {$r=@(Get-CimInstance -Namespace 'root/OpenHardwareMonitor' -ClassName 'Sensor' -ErrorAction Stop|Select-Object Name,Identifier,Parent,SensorType,Value,Min,Max,Index)} catch {$r=@(Get-WmiObject -Namespace 'root\OpenHardwareMonitor' -Class 'Sensor' -ErrorAction Stop|Select-Object Name,Identifier,Parent,SensorType,Value,Min,Max,Index)}; $r|ConvertTo-Json -Depth 4 -Compress"""
    cp=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,check=False)
    if cp.returncode!=0:return [],(cp.stderr or cp.stdout or 'OHM_QUERY_FAILED').strip()[-1200:]
    try:return normalize_ohm(json.loads(cp.stdout.strip())) if cp.stdout.strip() else [],None
    except Exception as e:return [],f'OHM_JSON_ERROR:{e}'

def query_nvml()->tuple[list[dict[str,Any]],str|None]:
    try:
        import pynvml
        pynvml.nvmlInit(); out=[]
        try:
            for i in range(pynvml.nvmlDeviceGetCount()):
                h=pynvml.nvmlDeviceGetHandleByIndex(i); u=pynvml.nvmlDeviceGetUtilizationRates(h); m=pynvml.nvmlDeviceGetMemoryInfo(h)
                def safe(fn):
                    try:return fn()
                    except Exception:return None
                name=safe(lambda:pynvml.nvmlDeviceGetName(h)); name=name.decode(errors='replace') if isinstance(name,bytes) else name
                uuid=safe(lambda:pynvml.nvmlDeviceGetUUID(h)); uuid=uuid.decode(errors='replace') if isinstance(uuid,bytes) else uuid
                out.append({'index':i,'name':name,'uuid':uuid,'gpu_util_percent':_f(u.gpu),'memory_util_percent':_f(u.memory),'memory_used_mb':m.used/1024**2,'memory_total_mb':m.total/1024**2,'temperature_c':_f(safe(lambda:pynvml.nvmlDeviceGetTemperature(h,pynvml.NVML_TEMPERATURE_GPU))),'power_w':(_f(safe(lambda:pynvml.nvmlDeviceGetPowerUsage(h))) or 0)/1000.0 if safe(lambda:pynvml.nvmlDeviceGetPowerUsage(h)) is not None else None,'fan_percent':_f(safe(lambda:pynvml.nvmlDeviceGetFanSpeed(h))),'source':'NVML'})
        finally:pynvml.nvmlShutdown()
        return out,None
    except Exception as e:return [],f'NVML_UNAVAILABLE:{e}'

def query_nvidia_smi()->tuple[list[dict[str,Any]],str|None]:
    cmd=['nvidia-smi','--query-gpu=index,name,uuid,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw,fan.speed,clocks.current.graphics,clocks.current.memory','--format=csv,noheader,nounits']
    try:cp=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=8,check=False)
    except Exception as e:return [],f'NVIDIA_SMI_UNAVAILABLE:{e}'
    if cp.returncode!=0:return [],(cp.stderr or 'NVIDIA_SMI_FAILED').strip()[-800:]
    out=[]
    for line in cp.stdout.splitlines():
        p=[x.strip() for x in line.split(',')]
        if len(p)<12:continue
        out.append({'index':int(p[0]),'name':p[1],'uuid':p[2],'gpu_util_percent':_f(p[3]),'memory_util_percent':_f(p[4]),'memory_used_mb':_f(p[5]),'memory_total_mb':_f(p[6]),'temperature_c':_f(p[7]),'power_w':_f(p[8]),'fan_percent':_f(p[9]),'graphics_clock_mhz':_f(p[10]),'memory_clock_mhz':_f(p[11]),'source':'nvidia-smi'})
    return out,None

def query_psutil()->tuple[dict[str,Any],str|None]:
    try:
        import psutil
        freq=psutil.cpu_freq(); mem=psutil.virtual_memory()
        return {'cpu_percent_total':psutil.cpu_percent(interval=None),'cpu_percent_per_core':psutil.cpu_percent(interval=None,percpu=True),'logical_cpus':psutil.cpu_count(logical=True),'physical_cpus':psutil.cpu_count(logical=False),'cpu_frequency_mhz':freq.current if freq else None,'memory_percent':mem.percent,'memory_used_gb':mem.used/1024**3,'memory_total_gb':mem.total/1024**3,'source':'psutil'},None
    except Exception as e:return {},f'PSUTIL_UNAVAILABLE:{e}'

def _score(row:dict[str,Any], terms:list[str])->int:
    text=(str(row.get('name'))+' '+str(row.get('identifier'))+' '+str(row.get('parent'))).lower(); return sum(10 for t in terms if t in text)

def choose(rows:list[dict[str,Any]], sensor_type:str, terms:list[str])->dict[str,Any]|None:
    c=[r for r in rows if str(r.get('sensor_type')).lower()==sensor_type.lower() and r.get('value') is not None]
    if not c:return None
    c.sort(key=lambda r:(_score(r,terms),-int(r.get('index') or 0)),reverse=True); return c[0]

def metric(value:Any,source:str,identifier:Any=None,name:Any=None)->dict[str,Any]|None:
    v=_f(value); return None if v is None else {'value':v,'source':source,'identifier':identifier,'name':name}

def snapshot()->dict[str,Any]:
    ohm,ohm_err=query_ohm(); nv,nv_err=query_nvml(); smi=[]; smi_err=None
    if not nv:smi,smi_err=query_nvidia_smi()
    gpu=(nv or smi); g=gpu[0] if gpu else {}
    ps,ps_err=query_psutil()
    cpu_temp=choose(ohm,'Temperature',['cpu package','package','cpu total','cpu']); gpu_temp=choose(ohm,'Temperature',['gpu core','gpu','nvidia']);
    gpu_power=choose(ohm,'Power',['gpu power','gpu package','gpu']); cpu_power=choose(ohm,'Power',['cpu package','package','cpu']); system_power=choose(ohm,'Power',['system total','total system','wall','input power'])
    gpu_load=choose(ohm,'Load',['gpu core','gpu']); fan_rpm=choose(ohm,'Fan',['gpu','fan']); fan_control=choose(ohm,'Control',['gpu','fan'])
    canonical={
      'cpu_package_temp_c':metric(cpu_temp.get('value'),'OpenHardwareMonitor',cpu_temp.get('identifier'),cpu_temp.get('name')) if cpu_temp else None,
      'gpu_core_temp_c':metric(gpu_temp.get('value'),'OpenHardwareMonitor',gpu_temp.get('identifier'),gpu_temp.get('name')) if gpu_temp else metric(g.get('temperature_c'),g.get('source','GPU'),g.get('uuid'),g.get('name')),
      'gpu_power_w':metric(gpu_power.get('value'),'OpenHardwareMonitor',gpu_power.get('identifier'),gpu_power.get('name')) if gpu_power else metric(g.get('power_w'),g.get('source','GPU'),g.get('uuid'),g.get('name')),
      'cpu_package_power_w':metric(cpu_power.get('value'),'OpenHardwareMonitor',cpu_power.get('identifier'),cpu_power.get('name')) if cpu_power else None,
      'system_total_power_w':metric(system_power.get('value'),'OpenHardwareMonitor',system_power.get('identifier'),system_power.get('name')) if system_power else None,
      'gpu_load_percent':metric(gpu_load.get('value'),'OpenHardwareMonitor',gpu_load.get('identifier'),gpu_load.get('name')) if gpu_load else metric(g.get('gpu_util_percent'),g.get('source','GPU'),g.get('uuid'),g.get('name')),
      'cpu_load_percent':metric(ps.get('cpu_percent_total'),'psutil',None,'CPU Total'),
      'gpu_fan_rpm':metric(fan_rpm.get('value'),'OpenHardwareMonitor',fan_rpm.get('identifier'),fan_rpm.get('name')) if fan_rpm else None,
      'gpu_fan_percent':metric(fan_control.get('value'),'OpenHardwareMonitor',fan_control.get('identifier'),fan_control.get('name')) if fan_control else metric(g.get('fan_percent'),g.get('source','GPU'),g.get('uuid'),g.get('name')),
      'gpu_memory_used_mb':metric(g.get('memory_used_mb'),g.get('source','GPU'),g.get('uuid'),g.get('name')),
      'gpu_memory_total_mb':metric(g.get('memory_total_mb'),g.get('source','GPU'),g.get('uuid'),g.get('name')),
    }
    identity={'ohm_identifiers':[r.get('identifier') for r in ohm],'gpu_identities':[x.get('uuid') or x.get('index') for x in gpu]}
    return {'schema':SCHEMA,'providers':{'openhardwaremonitor':{'status':'PASS' if ohm else 'UNAVAILABLE','error':ohm_err,'sensors':ohm},'gpu':{'status':'PASS' if gpu else 'UNAVAILABLE','error':nv_err if not nv else None,'fallback_error':smi_err,'devices':gpu},'psutil':{'status':'PASS' if ps else 'UNAVAILABLE','error':ps_err,'metrics':ps}},'canonical':canonical,'identity':identity}

def self_test()->int:
    mock=normalize_ohm({'Name':'CPU Package','Identifier':'/amdcpu/0/temperature/0','Parent':'/amdcpu/0','SensorType':'Temperature','Value':55,'Min':40,'Max':60,'Index':0}); assert choose(mock,'Temperature',['cpu package'])['value']==55
    assert _f('N/A') is None and _f('12.5')==12.5
    print(json.dumps({'schema':SCHEMA,'status':'PASS','tests':3},sort_keys=True)); return 0

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--self-test',action='store_true'); a=p.parse_args();
    if a.self_test:return self_test()
    print(json.dumps(snapshot(),ensure_ascii=False)); return 0
if __name__=='__main__':raise SystemExit(main())
