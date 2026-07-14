#!/usr/bin/env python3
"""Passive SystemMonitor bridge for JANUS A18.43.

V0.1.2 fixes strict sensor-domain mapping. A CPU package sensor can never be
relabelled as GPU power or whole-system power merely because it is the only
Power row available.

Lineage: Hawkar-usls/Janus-Demiurge system_monitor.py.
Reuses passive OHM/NVML/nvidia-smi/psutil collection patterns only.
"""
from __future__ import annotations
import argparse, json, platform, subprocess
from typing import Any
SCHEMA="JANUS/A18.43/system-monitor-bridge/v0.1.2"
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
                raw_power=safe(lambda:pynvml.nvmlDeviceGetPowerUsage(h))
                out.append({'index':i,'name':name,'uuid':uuid,'gpu_util_percent':_f(u.gpu),'memory_util_percent':_f(u.memory),'memory_used_mb':m.used/1024**2,'memory_total_mb':m.total/1024**2,'temperature_c':_f(safe(lambda:pynvml.nvmlDeviceGetTemperature(h,pynvml.NVML_TEMPERATURE_GPU))),'power_w':(_f(raw_power)/1000.0) if _f(raw_power) is not None else None,'fan_percent':_f(safe(lambda:pynvml.nvmlDeviceGetFanSpeed(h))),'source':'NVML'})
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
        return {'cpu_percent_total':psutil.cpu_percent(interval=0.1),'cpu_percent_per_core':psutil.cpu_percent(interval=0.1,percpu=True),'logical_cpus':psutil.cpu_count(logical=True),'physical_cpus':psutil.cpu_count(logical=False),'cpu_frequency_mhz':freq.current if freq else None,'memory_percent':mem.percent,'memory_used_gb':mem.used/1024**3,'memory_total_gb':mem.total/1024**3,'source':'psutil'},None
    except Exception as e:return {},f'PSUTIL_UNAVAILABLE:{e}'

def _text(row:dict[str,Any])->str:
    return ' '.join(str(row.get(k) or '') for k in ('name','identifier','parent')).lower()

def choose_strict(rows:list[dict[str,Any]], sensor_type:str, include_terms:list[str], *, parent_prefixes:tuple[str,...]=(), exclude_terms:tuple[str,...]=())->dict[str,Any]|None:
    candidates=[]
    for row in rows:
        if str(row.get('sensor_type')).lower()!=sensor_type.lower() or row.get('value') is None: continue
        text=_text(row)
        parent=str(row.get('parent') or '').lower()
        if parent_prefixes and not any(parent.startswith(prefix.lower()) for prefix in parent_prefixes): continue
        if any(term.lower() in text for term in exclude_terms): continue
        score=sum(10 for term in include_terms if term.lower() in text)
        if score<=0: continue
        candidates.append((score,-int(row.get('index') or 0),row))
    return max(candidates,key=lambda item:(item[0],item[1]))[2] if candidates else None

def metric(value:Any,source:str,identifier:Any=None,name:Any=None)->dict[str,Any]|None:
    v=_f(value); return None if v is None else {'value':v,'source':source,'identifier':identifier,'name':name}

def validate_mapping(canonical:dict[str,Any])->dict[str,Any]:
    checks={}
    def ident(key):
        item=canonical.get(key)
        return str(item.get('identifier') or '').lower() if isinstance(item,dict) else ''
    checks['gpu_power_domain_valid']=canonical.get('gpu_power_w') is None or '/nvidiagpu/' in ident('gpu_power_w') or canonical['gpu_power_w'].get('source') in {'NVML','nvidia-smi'}
    checks['cpu_power_domain_valid']=canonical.get('cpu_package_power_w') is None or '/amdcpu/' in ident('cpu_package_power_w')
    checks['system_power_domain_valid']=canonical.get('system_total_power_w') is None or all(x not in ident('system_total_power_w') for x in ('/amdcpu/','/nvidiagpu/'))
    checks['no_power_alias_collision']=not (canonical.get('gpu_power_w') and canonical.get('cpu_package_power_w') and ident('gpu_power_w')==ident('cpu_package_power_w'))
    checks['pass']=all(checks.values())
    return checks

def snapshot()->dict[str,Any]:
    ohm,ohm_err=query_ohm(); nv,nv_err=query_nvml(); smi=[]; smi_err=None
    if not nv:smi,smi_err=query_nvidia_smi()
    gpu=(nv or smi); g=gpu[0] if gpu else {}
    ps,ps_err=query_psutil()
    cpu_temp=choose_strict(ohm,'Temperature',['cpu package','cpu ccd'],parent_prefixes=('/amdcpu/',))
    gpu_temp=choose_strict(ohm,'Temperature',['gpu core','gpu'],parent_prefixes=('/nvidiagpu/',))
    gpu_power=choose_strict(ohm,'Power',['gpu power','gpu package','gpu board','gpu'],parent_prefixes=('/nvidiagpu/',))
    cpu_power=choose_strict(ohm,'Power',['cpu package'],parent_prefixes=('/amdcpu/',))
    system_power=choose_strict(ohm,'Power',['system total','total system','wall power','input power','psu power'],exclude_terms=('/amdcpu/','/nvidiagpu/'))
    gpu_load=choose_strict(ohm,'Load',['gpu core','gpu'],parent_prefixes=('/nvidiagpu/',))
    fan_rpm=choose_strict(ohm,'Fan',['gpu'],parent_prefixes=('/nvidiagpu/',))
    fan_control=choose_strict(ohm,'Control',['gpu fan','gpu'],parent_prefixes=('/nvidiagpu/',))
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
    return {'schema':SCHEMA,'providers':{'openhardwaremonitor':{'status':'PASS' if ohm else 'UNAVAILABLE','error':ohm_err,'sensors':ohm},'gpu':{'status':'PASS' if gpu else 'UNAVAILABLE','error':nv_err if not nv else None,'fallback_error':smi_err,'devices':gpu},'psutil':{'status':'PASS' if ps else 'UNAVAILABLE','error':ps_err,'metrics':ps}},'canonical':canonical,'mapping_validation':validate_mapping(canonical),'identity':identity}

def self_test()->int:
    mock=normalize_ohm([
      {'Name':'CPU Package','Identifier':'/amdcpu/0/power/0','Parent':'/amdcpu/0','SensorType':'Power','Value':52,'Min':20,'Max':75,'Index':0},
      {'Name':'CPU Package','Identifier':'/amdcpu/0/temperature/0','Parent':'/amdcpu/0','SensorType':'Temperature','Value':55,'Min':40,'Max':60,'Index':0},
      {'Name':'GPU Core','Identifier':'/nvidiagpu/0/temperature/0','Parent':'/nvidiagpu/0','SensorType':'Temperature','Value':34,'Min':32,'Max':35,'Index':0},
    ])
    assert choose_strict(mock,'Power',['cpu package'],parent_prefixes=('/amdcpu/',))['value']==52
    assert choose_strict(mock,'Power',['gpu'],parent_prefixes=('/nvidiagpu/',)) is None
    assert choose_strict(mock,'Power',['system total'],exclude_terms=('/amdcpu/','/nvidiagpu/')) is None
    canonical={'gpu_power_w':None,'cpu_package_power_w':metric(52,'OpenHardwareMonitor','/amdcpu/0/power/0','CPU Package'),'system_total_power_w':None}
    assert validate_mapping(canonical)['pass']
    assert _f('N/A') is None and _f('12.5')==12.5
    print(json.dumps({'schema':SCHEMA,'status':'PASS','tests':5},sort_keys=True)); return 0

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--self-test',action='store_true'); a=p.parse_args()
    if a.self_test:return self_test()
    print(json.dumps(snapshot(),ensure_ascii=False)); return 0
if __name__=='__main__':raise SystemExit(main())
