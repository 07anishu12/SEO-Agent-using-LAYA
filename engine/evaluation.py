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
