#!/usr/bin/env python3
"""Pure deterministic metrics for JANUS A18.43. No hardware writes."""
from __future__ import annotations
import argparse, json, math, statistics
from typing import Any, Iterable
SCHEMA = "JANUS/A18.43/preservation-metrics/v0.1.1"

def _numbers(values: Iterable[Any]) -> list[float]:
    return [float(v) for v in values if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(float(v))]

def trapezoid_integral(samples:list[dict[str,Any]], value_key:str)->float|None:
    rows=sorted([(float(r['t_monotonic']),float(r[value_key])) for r in samples if isinstance(r.get('t_monotonic'),(int,float)) and isinstance(r.get(value_key),(int,float))],key=lambda x:x[0])
    if len(rows)<2:return None
    total=0.0
    for (t0,v0),(t1,v1) in zip(rows,rows[1:]):
        dt=t1-t0
        if dt>0: total += dt*(v0+v1)/2.0
    return total

def thermal_degree_seconds(samples:list[dict[str,Any]], value_key:str, threshold_c:float)->float|None:
    rows=[{'t_monotonic':r.get('t_monotonic'),'excess':max(0.0,float(r[value_key])-threshold_c)} for r in samples if isinstance(r.get(value_key),(int,float))]
    return trapezoid_integral(rows,'excess')

def derived_cpu_percent(samples:list[dict[str,Any]], logical_cpus:int)->float|None:
    rows=sorted([(float(r['t_monotonic']),float(r['process_tree_cpu_seconds_total'])) for r in samples if isinstance(r.get('t_monotonic'),(int,float)) and isinstance(r.get('process_tree_cpu_seconds_total'),(int,float))],key=lambda x:x[0])
    if len(rows)<2 or logical_cpus<=0:return None
    elapsed=rows[-1][0]-rows[0][0]; delta=rows[-1][1]-rows[0][1]
    return None if elapsed<=0 or delta<0 else 100.0*delta/(elapsed*logical_cpus)

def coefficient_of_variation(values:Iterable[Any])->float|None:
    rows=_numbers(values)
    if len(rows)<2:return None
    mean=statistics.fmean(rows)
    return None if mean==0 else statistics.pstdev(rows)/abs(mean)

def summarize_series(values:Iterable[Any])->dict[str,float|int|None]:
    rows=_numbers(values)
    return {'count':len(rows),'min':min(rows) if rows else None,'max':max(rows) if rows else None,'mean':statistics.fmean(rows) if rows else None,'stdev':statistics.pstdev(rows) if len(rows)>1 else 0.0 if rows else None}

def waste_summary(counts:dict[str,Any])->dict[str,Any]:
    useful=int(counts.get('useful_completed_batches') or 0)
    fields=['post_target_overflow_batches','stale_batches','duplicate_batches','reconnect_invalidated_batches','queue_overshoot_batches','shutdown_latency_batches','unaccountable_batches']
    waste={f:int(counts.get(f) or 0) for f in fields}; total=sum(waste.values()); all_work=useful+total
    return {'schema':SCHEMA,'useful_completed_batches':useful,'waste_batches':waste,'total_waste_batches':total,'all_accounted_batches':all_work,'useful_work_fraction':useful/all_work if all_work else None,'waste_work_fraction':total/all_work if all_work else None}

def claim_readiness(cap:dict[str,bool], stable_identity:bool, sample_count:int)->dict[str,Any]:
    enough=sample_count>=30 and stable_identity
    thermal=enough and cap.get('has_temperature',False) and cap.get('has_load',False)
    component_energy=thermal and (cap.get('has_gpu_power',False) or cap.get('has_cpu_package_power',False))
    whole_system=thermal and cap.get('has_system_total_power',False)
    fan=thermal and cap.get('has_fan',False)
    return {'thermal_challenge_ready':thermal,'component_energy_claim_ready':component_energy,'whole_system_energy_claim_ready':whole_system,'fan_wear_metrics_ready':fan,'component_energy_scope':['GPU' if cap.get('has_gpu_power') else None,'CPU_PACKAGE' if cap.get('has_cpu_package_power') else None],'whole_system_energy_block_reason':None if whole_system else 'NO_EXTERNAL_OR_TOTAL_SYSTEM_POWER_SENSOR','hardware_lifetime_claim_ready':False,'hardware_lifetime_claim_block_reason':'REQUIRES_LONGITUDINAL_DEVICE_HEALTH_HISTORY'}

def self_test()->int:
    assert abs((trapezoid_integral([{'t_monotonic':0,'p':100},{'t_monotonic':1,'p':100},{'t_monotonic':2,'p':200}],'p') or 0)-250)<1e-9
    assert abs((thermal_degree_seconds([{'t_monotonic':0,'t':70},{'t_monotonic':1,'t':80},{'t_monotonic':2,'t':80}],'t',75) or 0)-7.5)<1e-9
    assert abs((derived_cpu_percent([{'t_monotonic':0,'process_tree_cpu_seconds_total':10},{'t_monotonic':2,'process_tree_cpu_seconds_total':18}],4) or 0)-100)<1e-9
    assert waste_summary({'useful_completed_batches':8,'post_target_overflow_batches':2})['useful_work_fraction']==0.8
    r=claim_readiness({'has_temperature':True,'has_load':True,'has_gpu_power':True,'has_fan':True},True,40); assert r['component_energy_claim_ready'] and not r['whole_system_energy_claim_ready']
    assert summarize_series([1,2,3])['mean']==2
    print(json.dumps({'schema':SCHEMA,'status':'PASS','tests':6},sort_keys=True)); return 0

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--self-test',action='store_true'); a=p.parse_args(); return self_test() if a.self_test else 0
if __name__=='__main__': raise SystemExit(main())
