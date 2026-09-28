"""Streaming acceptance accounting; no model, confidence or threshold policy here."""
import json


def empty_equivalence():
    return dict(total_comparisons=0,choice_matches=0,choice_mismatches=0,
                gate_matches=0,gate_mismatches=0,missing_decisions=0)


def compare_decision(counts, old, new):
    if old is None or new is None:
        counts['missing_decisions']+=1
        raise AssertionError('Missing old/new decision for stable candidate identity')
    counts['total_comparisons']+=1
    for field in ('choice','gate'):
        counts[field+('_matches' if old[field]==new[field] else '_mismatches')]+=1
    if old['choice']!=new['choice'] or old['gate']!=new['gate']:
        raise AssertionError(f'Old/new decision mismatch: old={old}, new={new}')


def require_safe_batch(report, checkpoint):
    if report.get('checkpoint_id')!=checkpoint:
        raise ValueError('Autotune checkpoint does not match the established checkpoint')
    size=report.get('safe_batch_size')
    if size not in (8,16,32,64):
        raise RuntimeError('No measured safe MLX batch; acceptance inference is blocked')
    if not any(r.get('batch_size')==size and r.get('safe') and not r.get('memory_guard_triggered') for r in report.get('results',[])):
        raise RuntimeError('Selected batch has no successful guarded measurement')
    return size


def stream_ground_truth(path):
    """Read the generator's one URL-entry-per-line JSON object without retaining the site."""
    with open(path) as source:
        if source.readline().strip()!='{':
            raise ValueError('Expected the existing generator ground-truth format')
        for line in source:
            line=line.strip()
            if line=='}':
                if source.read(1):
                    raise ValueError('Unexpected trailing ground-truth data')
                return
            if not line:continue
            entry=json.loads('{'+line.lstrip(',')+'}')
            if len(entry)!=1:raise ValueError('Expected one URL per ground-truth line')
            yield next(iter(entry.items()))
        raise ValueError('Incomplete ground-truth JSON object')


def score_synthetic(truth_path, store):
    """Page-level scoring; per-label recall means validation, not defect localization."""
    from collections import defaultdict
    counts=dict(tp=0,fp=0,tn=0,fn=0)
    per_defect=defaultdict(lambda:dict(positive_pages=0,validated=0,suppressed=0))
    pages=0
    for url,defects in stream_ground_truth(truth_path):
        row=store.get('synthetic_decisions',url)
        if row is None:raise AssertionError('Missing synthetic decision: '+url)
        if row['gate'] not in ('AUTO_ACCEPT','HUMAN_REVIEW','SUPPRESS'):
            raise ValueError('Unexpected decision gate')
        validated=bool(row['is_real_issue'] and row['gate'] in ('AUTO_ACCEPT','HUMAN_REVIEW'))
        actual=bool(defects)
        counts['tp' if actual and validated else 'fn' if actual else 'fp' if validated else 'tn']+=1
        for defect in defects:
            item=per_defect[defect];item['positive_pages']+=1
            item['validated' if validated else 'suppressed']+=1
        pages+=1
    if sum(1 for _ in store.rows('synthetic_decisions'))!=pages:
        raise AssertionError('Synthetic decision identities do not match ground truth')
    counts.update(precision=counts['tp']/(counts['tp']+counts['fp']) if counts['tp']+counts['fp'] else None,
                  recall=counts['tp']/(counts['tp']+counts['fn']) if counts['tp']+counts['fn'] else None,
                  pages=pages)
    for item in per_defect.values():item['page_validation_recall']=item['validated']/item['positive_pages']
    return dict(**counts,per_defect=dict(per_defect),
                per_defect_definition='Validation recall among pages with that planted label; overlaps retained; not localization precision')
