#!/usr/bin/env python3
"""A18.43 package preflight. Never launches a miner or controls hardware."""
from __future__ import annotations
import argparse, hashlib, json, platform, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
SCHEMA='JANUS/A18.43/preflight/v0.1.1'
def utc_now():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def sha(path:Path):return hashlib.sha256(path.read_bytes()).hexdigest()
def verify(root:Path)->list[dict[str,Any]]:
    m=json.loads((root/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8')); out=[]
    for e in m.get('files',[]):
        p=root/e['path']; actual=sha(p) if p.is_file() else None; out.append({'path':e['path'],'expected':e['sha256'],'actual':actual,'match':actual==e['sha256']})
    return out
def test(root:Path,script:str):
    c=subprocess.run([sys.executable,str(root/script),'--self-test'],capture_output=True,text=True,encoding='utf-8',errors='replace',check=False);return {'script':script,'exit_code':c.returncode,'stdout':c.stdout.strip(),'stderr':c.stderr.strip(),'pass':c.returncode==0}
def self_test():assert SCHEMA.endswith('v0.1.1');print(json.dumps({'schema':SCHEMA,'status':'PASS','tests':1},sort_keys=True));return 0
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default=str(Path(__file__).resolve().parent/'output'));p.add_argument('--duration-seconds',type=float,default=20.0);p.add_argument('--interval-seconds',type=float,default=0.5);p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:return self_test()
    root=Path(__file__).resolve().parent;out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True);checks=verify(root);tests=[test(root,x) for x in ['a18_43_preservation_metrics.py','a18_43_system_monitor_bridge.py','a18_43_hardware_sensor_probe.py']]
    gate={'schema':SCHEMA,'generated_at_utc':utc_now(),'phase':'PREFLIGHT_ONLY','platform':platform.platform(),'python':sys.version,'windows':platform.system()=='Windows','package_manifest_pass':all(x['match'] for x in checks),'manifest_checks':checks,'self_tests':tests,'self_tests_pass':all(x['pass'] for x in tests),'no_miner_launched':True,'no_hardware_control_performed':True};(out/'PACKAGE_PREFLIGHT.json').write_text(json.dumps(gate,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if not gate['windows'] or not gate['package_manifest_pass'] or not gate['self_tests_pass']:print(json.dumps(gate,ensure_ascii=False));return 4
    return subprocess.run([sys.executable,str(root/'a18_43_hardware_sensor_probe.py'),'--output',str(out),'--duration-seconds',str(a.duration_seconds),'--interval-seconds',str(a.interval_seconds)],check=False).returncode
if __name__=='__main__':raise SystemExit(main())
