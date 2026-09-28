"""Cold-process guarded acceptance; the supervisor never imports MLX."""
import argparse
from contextlib import closing
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import sqlite3
import subprocess
import sys
import threading
import time
import psutil
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CHECKPOINT = 'aac6fef/laya-mlx@20aed815fc6acde75733882e7ec0e3f28aeb9717'
SIZES = (8, 16, 32, 64)


def pressure_level():
    if platform.system() != 'Darwin':
        return None
    value = ctypes.c_int()
    size = ctypes.c_size_t(ctypes.sizeof(value))
    result = ctypes.CDLL(None).sysctlbyname(b'kern.memorystatus_vm_pressure_level', ctypes.byref(value), ctypes.byref(size), None, 0)
    if result:
        raise OSError('Cannot read macOS memory pressure')
    return value.value


def system_state():
    memory, swap = psutil.virtual_memory(), psutil.swap_memory()
    return dict(available_mb=memory.available / 2**20, memory_used_percent=memory.percent,
                pressure_level=pressure_level(), swap_used=swap.used, swap_out=swap.sout)


def unsafe_reason(state, before, limits, rss=0):
    if state['swap_used'] > before['swap_used']:
        return 'System swap grew (zero-growth guard)'
    if state['pressure_level'] is not None and state['pressure_level'] > 1:
        return 'macOS memory pressure rose above normal'
    if state['available_mb'] < limits['min_available_mb']:
        return 'System available memory fell below configured reserve'
    if rss > limits['memory_budget_mb']:
        return 'Process RSS exceeded configured memory budget'
    return None


def write_report(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)


def guarded_process(command, limits, report_path, log_path, batch_size=None):
    before = system_state()
    result = dict(batch_size=batch_size, baseline_rss_mb=None, peak_rss_mb=0.,
                  swap_before_mb=before['swap_used']/2**20, swap_after_mb=before['swap_used']/2**20,
                  peak_swap_mb=before['swap_used']/2**20, peak_system_memory_percent=before['memory_used_percent'],
                  peak_pressure_level=before['pressure_level'], min_available_mb=before['available_mb'],
                  memory_guard_triggered=False, safe=False, elapsed_seconds=0., checkpoint_id=CHECKPOINT)
    reason = unsafe_reason(before, before, limits)
    if reason:
        result.update(memory_guard_triggered=True, error=reason, started=False)
        write_report(report_path,result)
        return result
    stopped = threading.Event()
    start = time.monotonic()
    with open(log_path, 'w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   env={**os.environ, 'HF_HUB_OFFLINE':'1', 'TOKENIZERS_PARALLELISM':'false'})
        result['pid'] = process.pid
        def watch():
            child=psutil.Process(process.pid)
            while not stopped.is_set():
                try:
                    rss=child.memory_info().rss/2**20
                    if result['baseline_rss_mb'] is None:result['baseline_rss_mb']=rss
                    result['peak_rss_mb']=max(result['peak_rss_mb'],rss)
                    state=system_state()
                    result['peak_swap_mb']=max(result['peak_swap_mb'],state['swap_used']/2**20)
                    result['peak_system_memory_percent']=max(result['peak_system_memory_percent'],state['memory_used_percent'])
                    result['min_available_mb']=min(result['min_available_mb'],state['available_mb'])
                    if state['pressure_level'] is not None:
                        result['peak_pressure_level']=max(result['peak_pressure_level'] or 0,state['pressure_level'])
                    reason=unsafe_reason(state,before,limits,rss)
                    if reason:
                        result.update(memory_guard_triggered=True,error=reason)
                        process.terminate()
                        return
                except psutil.NoSuchProcess:
                    return
                except Exception as exc:
                    result.update(memory_guard_triggered=True,error=f'Memory monitor failed: {exc}')
                    process.terminate()
                    return
                stopped.wait(.05)  # Telemetry watchdog, not an inference retry/poll loop.
        monitor=threading.Thread(target=watch,daemon=True)
        monitor.start()
        try:
            return_code=process.wait()
        finally:
            stopped.set();monitor.join()
    after=system_state()
    result.update(elapsed_seconds=time.monotonic()-start,swap_after_mb=after['swap_used']/2**20,
                  swap_out_delta_mb=(after['swap_out']-before['swap_out'])/2**20,return_code=return_code,started=True)
    reason=unsafe_reason(after,before,limits,result['peak_rss_mb'])
    if reason:result.update(memory_guard_triggered=True,error=reason)
    child_path=Path(str(report_path)+'.child.json')
    if child_path.exists():
        child=json.loads(child_path.read_text());result['child']=child
        if child.get('baseline_rss_mb') is not None:
            result['spawn_rss_mb']=result['baseline_rss_mb']
            result['baseline_rss_mb']=child['baseline_rss_mb']
        if child.get('rss_after_load_mb') is not None:
            result['rss_after_load_mb']=child['rss_after_load_mb']
        if child.get('page_outs_before') is not None:
            result['page_outs_before']=child['page_outs_before']
            result['page_outs_after']=child.get('page_outs_after', after['swap_out'])
            result['swap_before_mb']=child.get('swap_before_mb', result['swap_before_mb'])
            result['swap_after_mb']=child.get('swap_after_mb', result['swap_after_mb'])
        result['peak_rss_mb']=max(result['peak_rss_mb'],child.get('peak_rss_mb',0))
        if child.get('memory_guard_triggered'):
            result.update(memory_guard_triggered=True,error=child.get('error','Child guard triggered'))
    result['safe']=return_code==0 and not result['memory_guard_triggered'] and result['peak_rss_mb']<=limits['memory_budget_mb']
    write_report(report_path,result)
    return result


def load_prepared(path):
    prepared=json.loads(Path(path).read_text())
    with closing(sqlite3.connect(Path(prepared['db']).resolve().as_uri()+'?mode=ro',uri=True)) as conn:
        count=conn.execute('SELECT COUNT(*) FROM pages').fetchone()[0]
    if not 1<=count<=500 or count!=prepared['urls']:
        raise ValueError('Prepared database must contain exactly the recorded <=500 URLs')
    from engine.profiles import resolve_profile
    return prepared,resolve_profile(prepared['config'],'dev')


def probe(args):
    # This is the single model-owning child, never a CPU pool worker.
    from engine.memory_guard import MemoryGuard, MemoryBudgetExceeded
    from engine.chunks import chunks
    from laya.streaming import LocalMLXService
    from laya.decision import LayaCandidateInput
    prepared,config=load_prepared(args.prepared)
    limits=config['runtime'];limits['batch_size']=args.batch_size
    guard=MemoryGuard(limits['memory_budget_mb'],batch_size=args.batch_size,
                      min_available_mb=limits['min_available_mb'],pause_seconds=limits['pause_seconds'])
    init_state = system_state()
    result=dict(batch_size=args.batch_size,baseline_rss_mb=guard.get_current_rss_mb(),
                swap_before_mb=init_state['swap_used']/2**20,page_outs_before=init_state['swap_out'],
                completed_candidates=0)
    start=time.monotonic()
    write_report(args.output,{**result,'status':'starting'})
    try:
        with guard.stage('model_startup'):
            service=LocalMLXService(config,guard)
            if service.checkpoint_id!=CHECKPOINT:raise RuntimeError('Checkpoint differs from the old pipeline')
        post_load = system_state()
        result.update(rss_after_load_mb=guard.get_current_rss_mb(),
                      swap_after_load_mb=post_load['swap_used']/2**20,
                      page_outs_after_load=post_load['swap_out'])
        guard.rebase_inference()
        with closing(sqlite3.connect(prepared['db'])) as conn:
            # Identical 64 longest saved inputs in every fresh process, ordered deterministically.
            rows=(r[0] for r in conn.execute("SELECT payload FROM chunk_records WHERE stage='baseline_candidates' ORDER BY LENGTH(payload) DESC,key LIMIT 64"))
            fingerprint=hashlib.sha256()
            with guard.stage('probe'):
                for batch in chunks(rows,args.batch_size):
                    for row in batch:fingerprint.update(row.encode())
                    candidates=[LayaCandidateInput(**json.loads(row)) for row in batch]
                    decisions=service.submit_batch(candidates,'autotune')
                    result['completed_candidates']+=len(decisions)
                    del decisions,candidates,batch
                    guard.checkpoint()
        result.update(status='completed',checkpoint_id=service.checkpoint_id,input_digest=fingerprint.hexdigest(),
                      native_question_batch_size=service.analyzer.get_backend()._agent.batch_size,
                      meaning='Bounded submission batch; native model settings and scalar predict API unchanged')
    except Exception as exc:
        result.update(status='aborted',error=f'{type(exc).__name__}: {exc}',memory_guard_triggered=isinstance(exc,MemoryBudgetExceeded))
        raise
    finally:
        high_water=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(2**20 if platform.system()=='Darwin' else 1024)
        end_state = system_state()
        result.update(elapsed_seconds=time.monotonic()-start,peak_rss_mb=max(high_water,guard.peak_rss_mb),
                      swap_after_mb=end_state['swap_used']/2**20,page_outs_after=end_state['swap_out'],
                      page_outs_delta=(end_state['swap_out']-init_state['swap_out']),stages=guard.stages)
        write_report(args.output,result)


def autotune(args):
    _,config=load_prepared(args.prepared)
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    summary_path=output/'autotune.json'
    if summary_path.exists():raise ValueError('Autotune already attempted; do not retry an unsafe batch')
    summary=dict(safe_batch_size=None,checkpoint_id=CHECKPOINT,results=[],sizes_requested=list(SIZES))
    for size in SIZES:
        path=output/f'batch-{size}.json'
        result=guarded_process([sys.executable,__file__,'probe','--prepared',args.prepared,'--batch-size',str(size),'--output',str(path)+'.child.json'],
                               config['runtime'],path,output/f'batch-{size}.log',size)
        summary['results'].append(result)
        if result['safe']:summary['safe_batch_size']=size
        write_report(summary_path,summary)
        print(json.dumps(dict(batch_size=size,safe=result['safe'],peak_rss_mb=result['peak_rss_mb'],elapsed_seconds=result['elapsed_seconds'],error=result.get('error'))),flush=True)
        if not result['safe']:break
    digests={r.get('child',{}).get('input_digest') for r in summary['results'] if r['safe']}
    if len(digests)>1:raise RuntimeError('Autotune inputs changed between sizes')


def guarded_evaluate(args):
    from engine.evaluation import require_safe_batch
    _,config=load_prepared(args.prepared)
    if not args.autotune_report:
        raise ValueError('--autotune-report is required for evaluation')
    measured=json.loads(Path(args.autotune_report).read_text())
    size=require_safe_batch(measured,CHECKPOINT)
    if not args.synthetic_dir or not (Path(args.synthetic_dir)/'generation.json').exists():
        raise ValueError('Use --synthetic-dir pointing to the existing generated dataset')
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    command=[sys.executable,str(Path(__file__).with_name('evaluate_laya_dev.py')),
             '--prepared',args.prepared,'--output',str(output),'--autotune-report',args.autotune_report,
             '--synthetic-dir',args.synthetic_dir]
    if args.resume:command.append('--resume')
    result=guarded_process(command,config['runtime'],output/'evaluation-watchdog.json',output/'evaluation.log',size)
    if not result['safe']:
        raise SystemExit('Evaluation aborted; inspect evaluation-watchdog.json before any further model work')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('autotune','probe','evaluate'))
    p.add_argument('--prepared',required=True);p.add_argument('--output',required=True)
    p.add_argument('--batch-size',type=int,choices=SIZES,default=8)
    p.add_argument('--autotune-report');p.add_argument('--synthetic-dir')
    p.add_argument('--resume',action='store_true')
    args=p.parse_args()
    {'autotune':autotune,'probe':probe,'evaluate':guarded_evaluate}[args.mode](args)
