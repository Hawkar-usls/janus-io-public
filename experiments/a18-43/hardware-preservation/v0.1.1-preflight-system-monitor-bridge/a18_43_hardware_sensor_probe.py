#!/usr/bin/env python3
"""Read-only hybrid hardware baseline probe for JANUS A18.43."""
from __future__ import annotations
import argparse, json, os, platform, sys, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from a18_43_preservation_metrics import claim_readiness, trapezoid_integral, thermal_degree_seconds, coefficient_of_variation, summarize_series
from a18_43_system_monitor_bridge import snapshot
SCHEMA="JANUS/A18.43/hardware-sensor-probe/v0.1.1"
def utc_now():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def atomic_json(path:Path,payload:Any):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.replace(tmp,path)
def append_jsonl(path:Path,payload:Any):
    with path.open('a',encoding='utf-8',newline='\n') as h:h.write(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n')
def flat(snapshot_row:dict[str,Any],t:float)->dict[str,Any]:
    out={'t_monotonic':t}
    for k,v in snapshot_row.get('canonical',{}).items():out[k]=v.get('value') if isinstance(v,dict) else None
    return out

def run_probe(output:Path,duration:float,interval:float)->dict[str,Any]:
    output.mkdir(parents=True,exist_ok=True); samples_path=output/'HARDWARE_SAMPLES.jsonl'; samples_path.unlink(missing_ok=True)
    first=snapshot(); ohm=first['providers']['openhardwaremonitor']['sensors'];
    if not ohm:raise RuntimeError('OPENHARDWAREMONITOR_RETURNED_NO_SENSORS')
    first_identity=json.dumps(first['identity'],sort_keys=True); inventory={'schema':'JANUS/A18.43/sensor-inventory/v0.1.1','generated_at_utc':utc_now(),'system_monitor_lineage':{'repository':'Hawkar-usls/Janus-Demiurge','path':'system_monitor.py','blob_sha':'7deec130091d3fe8c62375e32472326887159f42'},'providers':first['providers'],'canonical_mapping':first['canonical']}
    atomic_json(output/'SENSOR_INVENTORY.json',inventory)
    compatibility={'schema':'JANUS/A18.43/system-monitor-compatibility/v0.1.1','status':'PASS','reused':['OpenHardwareMonitor WMI','NVML','nvidia-smi fallback','psutil'],'intentionally_excluded':['CacheProbe','AudioSpectrumAnalyzer','ScreenMonitor','KeyboardMonitor','MouseMonitor','TachyonicRegulator','JanusVault control loop'],'source_blob_sha':'7deec130091d3fe8c62375e32472326887159f42'}
    atomic_json(output/'SYSTEM_MONITOR_COMPATIBILITY.json',compatibility)
    started=time.monotonic(); rows=[]; count=0; stable=True; changes=0; prev={k:(v or {}).get('value') if isinstance(v,dict) else None for k,v in first['canonical'].items()}
    while True:
        s=snapshot(); now=time.monotonic(); stable=stable and json.dumps(s['identity'],sort_keys=True)==first_identity
        cur={k:(v or {}).get('value') if isinstance(v,dict) else None for k,v in s['canonical'].items()}; changes+=sum(1 for k,v in cur.items() if k in prev and v!=prev[k]); prev=cur
        record={'schema':'JANUS/A18.43/hardware-sample/v0.1.1','ts_utc':utc_now(),'t_monotonic':now,'sample_index':count,**s}; append_jsonl(samples_path,record); rows.append(flat(s,now)); count+=1
        if now-started>=duration:break
        time.sleep(max(0.05,interval))
    cap={'has_temperature':any(any(isinstance(r.get(k),(int,float)) for r in rows) for k in ['cpu_package_temp_c','gpu_core_temp_c']),'has_load':any(any(isinstance(r.get(k),(int,float)) for r in rows) for k in ['cpu_load_percent','gpu_load_percent']),'has_gpu_power':any(isinstance(r.get('gpu_power_w'),(int,float)) for r in rows),'has_cpu_package_power':any(isinstance(r.get('cpu_package_power_w'),(int,float)) for r in rows),'has_system_total_power':any(isinstance(r.get('system_total_power_w'),(int,float)) for r in rows),'has_fan':any(any(isinstance(r.get(k),(int,float)) for r in rows) for k in ['gpu_fan_rpm','gpu_fan_percent'])}
    ready=claim_readiness(cap,stable,count)
    summary={'schema':'JANUS/A18.43/hardware-baseline-summary/v0.1.1','sample_count':count,'duration_seconds':time.monotonic()-started,'identity_stable':stable,'series':{k:summarize_series([r.get(k) for r in rows]) for k in rows[0] if k!='t_monotonic'},'integrals':{'gpu_energy_joules':trapezoid_integral(rows,'gpu_power_w'),'cpu_package_energy_joules':trapezoid_integral(rows,'cpu_package_power_w'),'system_total_energy_joules':trapezoid_integral(rows,'system_total_power_w'),'cpu_thermal_degree_seconds_above_75c':thermal_degree_seconds(rows,'cpu_package_temp_c',75.0),'gpu_thermal_degree_seconds_above_75c':thermal_degree_seconds(rows,'gpu_core_temp_c',75.0)},'fan_variability':{'gpu_fan_rpm_cv':coefficient_of_variation([r.get('gpu_fan_rpm') for r in rows]),'gpu_fan_percent_cv':coefficient_of_variation([r.get('gpu_fan_percent') for r in rows])},'claim_readiness':ready}
    atomic_json(output/'HARDWARE_BASELINE_SUMMARY.json',summary)
    if ready['component_energy_claim_ready'] and ready['thermal_challenge_ready']:status='PASS_COMPONENT_ENERGY_AND_THERMAL_BASELINE'
    elif ready['thermal_challenge_ready']:status='PASS_THERMAL_BASELINE_COMPONENT_ENERGY_BLOCKED'
    else:status='FAIL_CLOSED_INSUFFICIENT_SENSOR_BASELINE'
    report={'schema':SCHEMA,'generated_at_utc':utc_now(),'status':status,'platform':platform.platform(),'python':sys.version,'sample_count':count,'duration_seconds':summary['duration_seconds'],'sensor_identity_stable':stable,'changed_value_observations':changes,'capabilities':cap,'claim_readiness':ready,'energy_scope_note':'GPU/CPU package component energy is not wall energy.','no_miner_launched':True,'no_hardware_control_performed':True,'outputs':{'inventory':str(output/'SENSOR_INVENTORY.json'),'samples':str(samples_path),'baseline_summary':str(output/'HARDWARE_BASELINE_SUMMARY.json'),'compatibility':str(output/'SYSTEM_MONITOR_COMPATIBILITY.json')}}
    atomic_json(output/'A18_43_PREFLIGHT_REPORT.json',report); return report

def self_test()->int:
    s={'canonical':{'gpu_power_w':{'value':100},'gpu_core_temp_c':{'value':60}}}; f=flat(s,1.0); assert f['gpu_power_w']==100 and f['gpu_core_temp_c']==60
    print(json.dumps({'schema':SCHEMA,'status':'PASS','tests':2},sort_keys=True)); return 0

def main()->int:
    p=argparse.ArgumentParser();p.add_argument('--output',default=str(Path(__file__).resolve().parent/'output'));p.add_argument('--duration-seconds',type=float,default=20.0);p.add_argument('--interval-seconds',type=float,default=0.5);p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:return self_test()
    try:
        r=run_probe(Path(a.output).resolve(),a.duration_seconds,a.interval_seconds);print(json.dumps(r,ensure_ascii=False,sort_keys=True));return 0 if r['status'].startswith('PASS') else 4
    except Exception as e:
        out=Path(a.output).resolve(); fail={'schema':SCHEMA,'generated_at_utc':utc_now(),'status':'FAIL_CLOSED','error':str(e),'no_miner_launched':True,'no_hardware_control_performed':True,'recovery':['Run OpenHardwareMonitor.exe as Administrator.','Keep it running.','Install psutil if missing: python -m pip install psutil','Run PREFLIGHT_ONLY.cmd again.']};atomic_json(out/'A18_43_PREFLIGHT_REPORT.json',fail);print(json.dumps(fail,ensure_ascii=False));return 4
if __name__=='__main__':raise SystemExit(main())
