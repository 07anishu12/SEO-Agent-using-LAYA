from scripts.evaluate_laya_dev import confusion


def test_noise_metrics_include_clean_false_positives_and_suppressed_defects():
    metrics=confusion([(True,True),(True,False),(False,True),(False,False)])
    assert metrics==dict(tp=1,fp=1,fn=1,tn=1,precision=.5,recall=.5,clean_suppression=.5)
    assert confusion([])['precision'] is None
    assert confusion([(True,False)])['recall']==0
