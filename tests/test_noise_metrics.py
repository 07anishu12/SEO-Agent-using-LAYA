from scripts.evaluate_laya_dev import confusion


def test_noise_metrics_include_clean_false_positives_and_suppressed_defects():
    metrics=confusion([(True,True),(True,False),(False,True),(False,False)])
    assert metrics==dict(tp=1,fp=1,fn=1,tn=1,precision=.5,recall=.5,clean_suppression=.5)
    assert confusion([])['precision'] is None
    assert confusion([(True,False)])['recall']==0


def test_streamed_ground_truth_scores_missing_and_overlapping_defects(tmp_path):
    import json
    import pytest
    from engine.chunks import SQLiteStageStore
    from engine.evaluation import score_synthetic,stream_ground_truth
    truth=tmp_path/'ground_truth.json'
    truth.write_text('{\n"clean":[]\n,"a":["missing_title"]\n,"b":["thin_content","missing_title"]\n}\n')
    assert list(stream_ground_truth(truth))==[('clean',[]),('a',['missing_title']),('b',['thin_content','missing_title'])]
    store=SQLiteStageStore(tmp_path/'decisions.db')
    for url,gate,real in [('clean','SUPPRESS',False),('a','AUTO_ACCEPT',True),('b','SUPPRESS',True)]:
        store.put('synthetic_decisions',url,dict(gate=gate,is_real_issue=real))
    result=score_synthetic(truth,store)
    assert {k:result[k] for k in ('tp','fp','tn','fn','precision','recall')}==dict(tp=1,fp=0,tn=1,fn=1,precision=1,recall=.5)
    assert result['per_defect']['missing_title']['page_validation_recall']==.5
    assert result['per_defect']['thin_content']['page_validation_recall']==0
    store.clear('synthetic_decisions')
    with pytest.raises(AssertionError,match='Missing'):score_synthetic(truth,store)
