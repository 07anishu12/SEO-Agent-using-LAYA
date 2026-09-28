"""Offline ≤500 URL audit and exact old/new prompt equivalence preparation."""
import argparse
import asyncio
import json
import logging
from pathlib import Path
import sqlite3
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import yaml
from engine.memory_guard import MemoryGuard
from engine.pipeline import SEOJEVPipeline
from engine.chunks import SQLiteStageStore
from laya.candidates import build_candidates
from laya.streaming import iter_candidates
from laya.prompt import issue_data, normalized_prompt


async def prepare(args):
    config=yaml.safe_load(Path(args.config).read_text())
    config.setdefault('storage',{})['store_dir']=args.store
    limits=config['profiles']['dev']
    guard=MemoryGuard(limits['memory_budget_mb'],batch_size=limits['batch_size'],min_available_mb=limits['min_available_mb'])
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    try:
        with guard.stage('ingest'):
            pipeline=SEOJEVPipeline('https://www.drivio.in/',crawl_id=args.crawl_id,db_path=args.db,
                                    output_dir=str(output),config=config,options={'profile':'dev','performance_sample':0})
            pipeline.memory_guard=guard
        with guard.stage('evidence'):
            p2=await pipeline.run_pass_2_signals()
        with guard.stage('template_grouping_and_candidates'):
            await pipeline.run_pass_3_search_opportunities(p2)
            del p2
        with guard.stage('equivalence_prompt_check'):
            # Reference reducer is retained solely for the bounded equivalence oracle.
            with sqlite3.connect(pipeline.db_path) as conn:
                conn.row_factory=sqlite3.Row
                opportunities=[dict(r) for r in conn.execute('SELECT * FROM opportunities WHERE run_id=?',(pipeline.crawl_id,))]
            old,members=build_candidates(pipeline.storage.get_all_issue_clusters(pipeline.crawl_id),pipeline.storage.get_all_pages(pipeline.crawl_id),opportunities)
            baseline=SQLiteStageStore(pipeline.db_path)
            for key,candidate in old.items():baseline.put('baseline_candidates',key,candidate.to_dict())
            del old, members, opportunities
            matched=0
            for candidate in iter_candidates(pipeline.db_path,pipeline.crawl_id):
                from laya.decision import LayaCandidateInput
                prior=LayaCandidateInput(**baseline.get('baseline_candidates',candidate.cluster_id))
                if normalized_prompt(issue_data(prior)) != normalized_prompt(issue_data(candidate)):
                    raise AssertionError('Changed prompt: '+candidate.cluster_id)
                matched+=1
            with sqlite3.connect(pipeline.db_path) as conn:
                count=conn.execute("SELECT COUNT(*) FROM chunk_records WHERE stage='baseline_candidates'").fetchone()[0]
            assert matched==count
        manifest=dict(db=pipeline.db_path,crawl_id=pipeline.crawl_id,config=config,source_db=args.db,
                      source_crawl=args.crawl_id,urls=500,prompt_equivalence=dict(matched=matched,total=count),
                      stages=guard.stages,peak_rss_mb=guard.peak_rss_mb,seconds=time.monotonic()-start)
        (output/'prepared.json').write_text(json.dumps(manifest,indent=2))
        print(json.dumps({k:v for k,v in manifest.items() if k not in ('config',)},indent=2),flush=True)
    except Exception as exc:
        (output/'failure.json').write_text(json.dumps(dict(error=str(exc),stages=guard.stages,peak_rss_mb=guard.peak_rss_mb),indent=2))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',required=True);p.add_argument('--crawl-id',required=True)
    p.add_argument('--store',required=True);p.add_argument('--output',required=True)
    p.add_argument('--config',default='config.yaml')
    args=p.parse_args();logging.basicConfig(level=logging.WARNING)
    asyncio.run(prepare(args))
