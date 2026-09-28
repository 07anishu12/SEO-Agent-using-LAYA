import pytest
from engine.evaluation import empty_equivalence,compare_decision,require_safe_batch


def test_counts_both_heads_independently_and_stops_on_first_mismatch():
    counts=empty_equivalence()
    compare_decision(counts,dict(choice='retain',gate='SUPPRESS'),dict(choice='retain',gate='SUPPRESS'))
    with pytest.raises(AssertionError,match='mismatch'):
        compare_decision(counts,dict(choice='retain',gate='SUPPRESS'),dict(choice='retain',gate='HUMAN_REVIEW'))
    assert counts==dict(total_comparisons=2,choice_matches=2,choice_mismatches=0,gate_matches=1,gate_mismatches=1,missing_decisions=0)


def test_missing_decision_fails():
    counts=empty_equivalence()
    with pytest.raises(AssertionError,match='Missing'):compare_decision(counts,None,dict(choice='retain',gate='SUPPRESS'))
    assert counts['missing_decisions']==1 and counts['total_comparisons']==0


def test_unsafe_autotune_blocks_before_model_load():
    with pytest.raises(RuntimeError,match='No measured safe'):
        require_safe_batch(dict(checkpoint_id='same',safe_batch_size=None),'same')
    with pytest.raises(ValueError,match='checkpoint'):
        require_safe_batch(dict(checkpoint_id='changed',safe_batch_size=8),'same')
