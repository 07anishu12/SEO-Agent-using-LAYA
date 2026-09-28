"""CPU-only JSONL chunk worker; importing this entry point cannot import MLX."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.chunks import chunks, open_store
from engine.profiles import resolve_profile
from engine.template_families import template_family
from engine.memory_guard import MemoryGuard


def ingest(rows):
    return [dict(row) for row in rows]


def evidence(rows):
    # Retain all upstream evidence; detectors can enrich this contract independently.
    return [dict(row, family=template_family(row['url'], row.get('page_type', 'other'))) for row in rows]


def fan_out(rows):
    output = []
    for row in rows:
        decision = row['decision']
        for member in row['members']:
            output.append(dict(member=member, decision=decision, class_id=row['class_id']))
    return output


def main():
    p = argparse.ArgumentParser()
    p.add_argument('stage', choices=('ingest','evidence','fan-out'))
    p.add_argument('--profile', choices=('dev','prod'), default='dev')
    p.add_argument('--input', required=True)
    a=p.parse_args()
    os.environ['SEOJEV_CPU_WORKER']='1'
    config=resolve_profile(profile=a.profile)
    store=open_store({**config['storage'], 'db_path':os.environ.get('SEOJEV_DB_PATH','data/chunks.db')})
    limits=config['runtime']
    guard=MemoryGuard(limits['memory_budget_mb'], batch_size=limits['batch_size'])
    fn={'ingest':ingest,'evidence':evidence,'fan-out':fan_out}[a.stage]
    count=0
    with open(a.input) as source, guard.stage(a.stage):
        for batch in chunks((json.loads(line) for line in source), limits['batch_size']):
            count+=len(batch)
            if count > limits['max_urls']:
                raise ValueError('Input exceeds profile limit')
            guard.checkpoint()
            store.run_chunk(a.stage, batch[0].get('url',str(count)),batch,fn,{'version':1})
    print(json.dumps(guard.stages))


if __name__=='__main__':
    main()
