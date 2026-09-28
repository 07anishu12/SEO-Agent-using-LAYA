"""Real checkpoint equivalence, labelled noise evaluation and measured resource probes."""
import argparse
from contextlib import closing
import json
import logging
from pathlib import Path
import sqlite3
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine.chunks import SQLiteStageStore
from engine.memory_guard import MemoryGuard
from engine.evaluation import empty_equivalence, compare_decision, require_safe_batch, score_synthetic
from engine.profiles import resolve_profile
from laya.streaming import LocalMLXService, iter_candidates, decide_classes
from laya.decision import LayaCandidateInput, LayaDecision, LAYA_PROMPT_VERSION
from laya.prompt import issue_data
from scripts.gen_synthetic_site import generate


def confusion(records):
    tp=fp=fn=tn=0
    for actual,predicted in records:
        tp+=bool(actual and predicted);fp+=bool(not actual and predicted)
        fn+=bool(actual and not predicted);tn+=bool(not actual and not predicted)
    return dict(tp=tp,fp=fp,fn=fn,tn=tn,precision=tp/(tp+fp) if tp+fp else None,
                recall=tp/(tp+fn) if tp+fn else None,clean_suppression=tn/(tn+fp) if tn+fp else None)


def synthetic_candidates(directory, db_path):
    """Parse observed HTML and inbound links; ground truth is never opened here."""
    from bs4 import BeautifulSoup
    directory=Path(directory)
    with closing(sqlite3.connect(db_path)) as c:
        c.executescript('CREATE TABLE IF NOT EXISTS fixture_pages(url TEXT PRIMARY KEY,payload TEXT); CREATE TABLE IF NOT EXISTS fixture_links(source TEXT,target TEXT,PRIMARY KEY(source,target));')
        with (directory/'manifest.jsonl').open() as manifest:
            for line in manifest:
                row=json.loads(line)
                soup=BeautifulSoup((directory/row['file']).read_text(),'html.parser')
                for link in soup.find_all('a',href=True):c.execute('INSERT OR IGNORE INTO fixture_links VALUES (?,?)',(row['url'],link['href']))
                scripts=[s.get_text() for s in soup.find_all('script',type='application/ld+json')]
                schemas=[]; errors=[]
                for raw in scripts:
                    try:schemas.append(json.loads(raw))
                    except ValueError as exc:errors.append(str(exc))
                canonical=soup.find('link',rel='canonical')
                robots=soup.find('meta',attrs={'name':'robots'})
                observed=dict(url=row['url'],title=soup.title.get_text() if soup.title else '',
                    h1=[h.get_text() for h in soup.find_all('h1')],canonical=canonical.get('href') if canonical else '',
                    robots=robots.get('content','') if robots else '',city=row['city'],
                    body=soup.main.get_text(' ',strip=True),schema=schemas,schema_errors=errors,
                    outgoing_links=len(soup.find_all('a',href=True)),template=row['template'])
                c.execute('INSERT OR REPLACE INTO fixture_pages VALUES (?,?)',(row['url'],json.dumps(observed)))
        c.commit()
        c.execute('CREATE INDEX IF NOT EXISTS fixture_target ON fixture_links(target)')
        for url,payload in c.execute('SELECT url,payload FROM fixture_pages ORDER BY url'):
            observed=json.loads(payload)
            observed['inbound_links']=c.execute('SELECT COUNT(*) FROM fixture_links WHERE target=?',(url,)).fetchone()[0]
            observed['title_occurrences']=c.execute("SELECT COUNT(*) FROM fixture_pages WHERE json_extract(payload,'$.title')=?",(observed['title'],)).fetchone()[0]
            # All observations are supplied, including clean pages; no labels or defect names.
            yield LayaCandidateInput(cluster_id='page:'+url,template_id=observed['template'],
                issue_type='Assess whether the observed page has a real SEO problem or is noise',page_count=1,
                sample_urls=[url],status_distribution={'200':1},category_hint='technical',
                canonical_relationship=dict(canonical=observed['canonical'],self_canonical=observed['canonical']==url,robots=observed['robots']),
                content_metrics=dict(words=len(observed['body'].split()),title=observed['title'],h1=observed['h1'],title_occurrences=observed['title_occurrences']),
                link_metrics=dict(inbound=observed['inbound_links'],outbound=observed['outgoing_links']),
                schema_metrics=dict(schemas=observed['schema'],errors=observed['schema_errors']),
                evidence_refs=[json.dumps(dict(city=observed['city'],text=observed['body']),sort_keys=True)])


def evaluate(args):
    prepared=json.loads(Path(args.prepared).read_text())
    config=resolve_profile(prepared['config'],'dev');limits=config['runtime']
    from scripts.laya_acceptance import CHECKPOINT, load_prepared
    load_prepared(args.prepared)  # Verify the existing DB, never create a replacement sample.
    autotune=json.loads(Path(args.autotune_report).read_text())
    limits['batch_size']=require_safe_batch(autotune,CHECKPOINT)
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    result_path=output/'measurements.json'
    prior=json.loads(result_path.read_text()) if result_path.exists() else None
    if prior and (prior['status']=='completed' or not args.resume):
        raise ValueError('Evaluation already recorded; use --resume only for an incomplete run')
    guard=MemoryGuard(limits['memory_budget_mb'],batch_size=limits['batch_size'],min_available_mb=limits['min_available_mb'],pause_seconds=limits['pause_seconds'])
    result=dict(status='running',urls=prepared['urls'],preparation=prepared,policy=config['laya']['confidence'])
    store=SQLiteStageStore(prepared['db'])
    start=time.monotonic()
    try:
        with guard.stage('model_startup'):
            service=LocalMLXService(config,guard)
        result['checkpoint_id']=service.checkpoint_id
        if prior and prior.get('checkpoint_id',service.checkpoint_id)!=service.checkpoint_id:
            raise ValueError('Cannot resume equivalence with a different checkpoint')
        if prior and prior['policy']!=result['policy']:
            raise ValueError('Cannot resume with a different confidence policy')
        # Execute the old worker implementation from the recorded pre-change commit.
        # The unchanged analyzer/gates serve both implementations; no alternate model exists.
        import subprocess, types
        old_source=subprocess.check_output(['git','show','896b2dd:laya/worker_pool.py'],text=True)
        old_module=types.ModuleType('laya._acceptance_old_worker')
        old_module.__package__='laya'
        exec(compile(old_source,'896b2dd:laya/worker_pool.py','exec'),old_module.__dict__)
        old_pool=old_module.LayaWorkerPool(settings=config.get('laya',{}),cache_db_path=None,num_workers=1)
        old_pool._analyzer=service.analyzer
        result['old_pipeline_commit']='896b2dd'
        result['autotune']=autotune
        # Independent inference of old candidates; no analyzer or durable result reuse.
        with guard.stage('baseline_laya'):
            count=0
            for row in store.rows('baseline_candidates'):
                candidate=LayaCandidateInput(**row)
                if args.resume and store.get('baseline_decisions',candidate.cluster_id):
                    count+=1
                    continue
                service.analyzer.reset_metrics_for_test()
                guard.checkpoint()
                decision=old_pool._make_decision(candidate,'baseline')
                time.sleep(limits['throttle_seconds'])
                store.put('baseline_decisions',candidate.cluster_id,dict(choice=decision.choice,gate=decision.gate))
                count+=1
            result['baseline_candidates']=count
        with guard.stage('laya'):
            service.analyzer.reset_metrics_for_test()
            counts=empty_equivalence()
            result['equivalence']=counts
            for decision in decide_classes(iter_candidates(prepared['db'],prepared['crawl_id']),service,store,guard,prepared['crawl_id']):
                previous=store.get('baseline_decisions',decision.cluster_id)
                new=dict(choice=decision.choice,gate=decision.gate)
                try:
                    compare_decision(counts,previous,new)
                except AssertionError:
                    store.put('equivalence_failures',decision.cluster_id,dict(old=previous,new=new))
                    result['failed_candidate_id']=decision.cluster_id
                    raise  # Stop on the first mismatch, before synthetic evaluation.
                store.put('run_decisions',decision.cluster_id,decision.to_dict())
            counts['missing_decisions']+=abs(count-counts['total_comparisons'])
            counts.update(total=count,matched=counts['choice_matches'] if not counts['gate_mismatches'] else 0,
                          mismatched=counts['choice_mismatches']+counts['gate_mismatches'],
                          passed=counts['total_comparisons']==count and not counts['missing_decisions'])
            if not counts['passed']:raise AssertionError('Incomplete old/new equivalence')
        result['deduplication']=store.get('metrics',prepared['crawl_id'])
        with guard.stage('fan_out_and_work_orders'):
            with closing(sqlite3.connect(prepared['db'])) as c:
                for row in store.rows('run_decisions'):
                    decision=LayaDecision.from_dict(row)
                    if not decision.is_real_issue or decision.gate=='SUPPRESS':continue
                    member_count=c.execute('SELECT COUNT(*) FROM candidate_membership WHERE run_id=? AND candidate_id=?',(prepared['crawl_id'],decision.cluster_id)).fetchone()[0]
                    candidate=store.get('baseline_candidates',decision.cluster_id)
                    store.put('class_work_orders',decision.input_hash,dict(class_id=decision.input_hash,
                        choice=decision.choice,gate=decision.gate,member_opportunities=member_count,
                        affected_urls_count=candidate['page_count'],sample_urls=candidate['sample_urls'],checkpoint_id=decision.checkpoint_id))
        synthetic=Path(args.synthetic_dir) if args.synthetic_dir else output/'synthetic'
        with guard.stage('synthetic_generation'):
            if (synthetic/'generation.json').exists() and (args.resume or args.synthetic_dir):
                generation=json.loads((synthetic/'generation.json').read_text())
            else:
                generation=generate(prepared['source_db'],prepared['source_crawl'],synthetic,cities=20,price_variants=4)
        result['synthetic_pages']=generation['pages']
        with guard.stage('synthetic_evidence_and_laya'):
            for candidate in synthetic_candidates(synthetic,output/'synthetic.db'):
                guard.checkpoint()
                if args.resume and store.get('synthetic_decisions',candidate.sample_urls[0]):
                    continue
                decision=service.submit_batch([candidate],'synthetic')[0]
                store.put('synthetic_decisions',candidate.sample_urls[0],dict(url=candidate.sample_urls[0],choice=decision.choice,gate=decision.gate,is_real_issue=decision.is_real_issue))
        with guard.stage('synthetic_scoring'):
            result['noise_detection']=score_synthetic(synthetic/'ground_truth.json',store)
        result['metric_definition']='Page-level: any planted defect is positive; validated requires real_issue and AUTO_ACCEPT/HUMAN_REVIEW. This does not establish per-defect localization accuracy.'
        result['status']='completed'
    except Exception as exc:
        result['status']='aborted';result['error']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        result.update(seconds=time.monotonic()-start,peak_rss_mb=guard.peak_rss_mb,stages=guard.stages)
        result_path.write_text(json.dumps(result,indent=2))
        print(json.dumps({k:v for k,v in result.items() if k not in ('preparation','autotune')},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--autotune-report',required=True)
    p.add_argument('--prepared',required=True);p.add_argument('--output',required=True)
    p.add_argument('--resume',action='store_true')
    p.add_argument('--synthetic-dir',help='Reuse an already generated fixture set; never regenerate it')
    args=p.parse_args();logging.basicConfig(level=logging.WARNING)
    evaluate(args)
