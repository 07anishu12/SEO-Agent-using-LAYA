import json
import sqlite3
from crawler.storage import CrawlStorage
from crawler.migrations import MigrationRunner
from laya.candidates import build_candidates
from laya.streaming import iter_candidates, fan_out, class_record
from laya.prompt import issue_data, normalized_prompt
from laya.decision import LayaCandidateInput
from engine.id_system import IDSystem


def test_stream_matches_existing_reducer(tmp_path):
    db=str(tmp_path/'sample.db');storage=CrawlStorage(db);MigrationRunner(db).run_migrations()
    from models.page import PageData
    from models.issue import SEOIssue
    # Insert minimal records using schema defaults; no network or model required.
    with sqlite3.connect(db) as c:
        c.row_factory=sqlite3.Row
        for i in range(5):
            c.execute('INSERT INTO pages(crawl_id,url,template_id,word_count,is_indexable,status_code,canonical_status,content_hash,internal_links_count) VALUES (?,?,?,?,?,?,?,?,?)',('r',f'https://x/{i}','tpl',100+i,1,200,'self','same',2))
        c.execute('INSERT INTO issue_clusters(crawl_id,cluster_id,issue,category,priority,primary_affected_template,affected_urls_count,sample_urls) VALUES (?,?,?,?,?,?,?,?)',('r','cluster1','missing_title','technical','High','tpl',5,'["https://x/0"]'))
        for i in range(3):
            opp=dict(opportunity_id=f'o{i}',display_id=f'OPP-{i}',run_id='r',fingerprint=IDSystem.generate_fingerprint('cluster1','tpl','template-aggregate') if i==0 else f'fp{i}',type='TPL',affected_templates_json='["tpl"]',sample_urls_json=json.dumps([f'https://x/{i}']),action='fix',observation='check',diagnosis='check',hypothesis='check',opportunity_tier='Medium',confidence_tier='High',effort='S',affected_urls_count=1,implementation_location='tpl')
            c.execute(f'INSERT INTO opportunities({",".join(opp)}) VALUES ({",".join("?" for _ in opp)})',tuple(opp.values()))
        pages=[dict(r) for r in c.execute('SELECT * FROM pages')]
        clusters=[dict(r) for r in c.execute('SELECT * FROM issue_clusters')]
        opportunities=[dict(r) for r in c.execute('SELECT * FROM opportunities')]
    old,members=build_candidates(clusters,pages,opportunities)
    new={c.cluster_id:c for c in iter_candidates(db,'r')}
    assert {k:normalized_prompt(issue_data(v)) for k,v in old.items()}=={k:normalized_prompt(issue_data(v)) for k,v in new.items()}
    with sqlite3.connect(db) as c:
        actual=dict(c.execute('SELECT opportunity_id,candidate_id FROM candidate_membership'))
    from laya.candidates import opportunity_candidate_key
    assert actual=={o['opportunity_id']:opportunity_candidate_key(o,members) for o in opportunities}


def test_class_identity_does_not_erase_outliers():
    a=LayaCandidateInput(cluster_id='a',content_metrics={'min_words':500})
    b=LayaCandidateInput(cluster_id='a',content_metrics={'min_words':5})
    assert class_record(a,'checkpoint')['class_id']!=class_record(b,'checkpoint')['class_id']
    assert a.compute_hash('checkpoint')!=a.compute_hash('other')


def test_fanout_uses_explicit_member(monkeypatch):
    # Exercise fan-out identity without pretending a fabricated head is a model result.
    from types import SimpleNamespace
    from laya import streaming
    monkeypatch.setattr(streaming.LayaDecision,'from_dict',lambda row:row)
    original=SimpleNamespace(to_dict=lambda:{'cluster_id':'representative','choice':'keep','gate':'SUPPRESS','affected_count':9,'evidence_refs':['representative']})
    result=streaming.fan_out(original,{'candidate_id':'member-7','affected_count':3,'evidence_refs':['member']})
    assert result['cluster_id']=='member-7' and result['affected_count']==3
    assert (result['choice'],result['gate'])==('keep','SUPPRESS')
    assert result['evidence_refs']==['member']


def test_cache_key_matches_complete_prompt():
    from laya.prompt import prompt_hash
    from laya.decision import LAYA_PROMPT_VERSION
    a=LayaCandidateInput(cluster_id='same',sample_urls=['https://x/a'])
    b=LayaCandidateInput(cluster_id='same',sample_urls=['https://x/b'])
    assert a.compute_hash('checkpoint')==prompt_hash(issue_data(a),LAYA_PROMPT_VERSION,'checkpoint')
    assert a.compute_hash('checkpoint')==b.compute_hash('checkpoint')  # URLs are not sent by the established prompt.
