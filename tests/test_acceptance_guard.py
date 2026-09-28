import json
import sys
from scripts.laya_acceptance import unsafe_reason,guarded_process,SIZES


def state(swap=0,pressure=1):
    return dict(available_mb=8000,memory_used_percent=50,pressure_level=pressure,swap_used=swap,swap_out=0)


def test_zero_swap_growth_and_pressure_stop():
    limits=dict(min_available_mb=1536,memory_budget_mb=4096)
    assert unsafe_reason(state(1),state(),limits)
    assert unsafe_reason(state(pressure=2),state(),limits)
    assert unsafe_reason(state(),state(),limits,4097)
    assert unsafe_reason(state(),state(),limits,100) is None
    assert SIZES==(8,16,32,64)


def test_supervisor_records_fresh_process_without_model(tmp_path,monkeypatch):
    monkeypatch.setattr('scripts.laya_acceptance.system_state',state)
    report=guarded_process([sys.executable,'-c','pass'],dict(min_available_mb=10,memory_budget_mb=4096),tmp_path/'report.json',tmp_path/'log',8)
    assert report['safe'] and not report['memory_guard_triggered']
    assert report['swap_before_mb']==report['swap_after_mb']==0
    assert report['elapsed_seconds']>0 and report['pid']>0
    assert json.loads((tmp_path/'report.json').read_text())==report
