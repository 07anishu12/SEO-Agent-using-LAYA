import pytest
from engine.memory_guard import MemoryGuard, MemoryBudgetExceeded, autotune_batches
from engine.chunks import SQLiteStageStore, chunks


def sample(rss=10, available=4000, swap=0):
    return dict(rss_mb=rss, available_mb=available, swap_used=swap, swap_out=0)


def test_guard_shrinks_pauses_aborts():
    readings=iter([sample(),sample(110),sample(110),sample(110)])
    pauses=[]
    g=MemoryGuard(100,batch_size=8,sample=lambda:next(readings),sleep=pauses.append)
    with pytest.raises(MemoryBudgetExceeded,match='batch shrink and pause'): g.checkpoint()
    assert g.batch_size==4 and pauses==[2]


def test_swap_growth_aborts_without_retry():
    readings=iter([sample(),sample(swap=1)])
    g=MemoryGuard(sample=lambda:next(readings),sleep=lambda _:pytest.fail('unexpected pause'))
    with pytest.raises(MemoryBudgetExceeded,match='swap grew'):g.checkpoint()


def test_low_available_triggers_even_with_small_rss():
    g=MemoryGuard(sample=lambda:sample(available=10),sleep=lambda _:None)
    with pytest.raises(MemoryBudgetExceeded):g.checkpoint()


def test_autotune_measures_all_sizes(tmp_path):
    measured=[]
    g=MemoryGuard(sample=sample)
    result=autotune_batches(measured.append,g,tmp_path/'tune.json',{'checkpoint':'test'})
    assert measured==[8,16,32,64] and result['safe_batch_size']==64


def test_resume_invalidation_and_range(tmp_path):
    store=SQLiteStageStore(tmp_path/'chunks.db'); calls=[]
    def transform(rows): calls.append(1);return rows
    for _ in range(2):store.run_chunk('evidence','b',[1],transform,{'version':1})
    assert len(calls)==1
    store.run_chunk('evidence','b',[2],transform,{'version':1})
    assert len(calls)==2 and list(store.rows('evidence','b','c'))==[[2]]
    assert list(chunks(range(5),2))==[[0,1],[2,3],[4]]
