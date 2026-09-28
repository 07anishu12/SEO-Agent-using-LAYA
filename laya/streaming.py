"""Disk-backed candidate reduction preserving established prompts and membership."""
from collections import Counter
from contextlib import closing
import json
import sqlite3
import time
from engine.id_system import IDSystem
from engine.template_families import template_family
from .candidates import candidate_key, samples
from .decision import LayaCandidateInput, LayaDecision


def iter_candidates(db_path, run_id):
    """SQL grouping, at most five sample pages and one candidate retained at a time."""
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA temp_store=FILE')
        conn.execute('PRAGMA cache_size=-2048')
        conn.executescript('''CREATE TABLE IF NOT EXISTS candidate_membership(
            run_id TEXT,opportunity_id TEXT,candidate_id TEXT,PRIMARY KEY(run_id,opportunity_id));
            CREATE TEMP TABLE fingerprints(fingerprint TEXT PRIMARY KEY,candidate_id TEXT);
            CREATE TEMP TABLE keyed_opportunities(key TEXT, payload TEXT,opportunity_id TEXT);''')
        conn.execute('DELETE FROM candidate_membership WHERE run_id=?',(run_id,))
        # The original reducer considers all opportunity template IDs when matching fingerprints.
        templates = [r[0] for r in conn.execute("SELECT DISTINCT j.value FROM opportunities o,json_each(COALESCE(o.affected_templates_json,'[]')) j WHERE run_id=?",(run_id,))]
        for row in conn.execute('SELECT cluster_id FROM issue_clusters WHERE crawl_id=? ORDER BY id',(run_id,)):
            cid=row[0]; key=candidate_key(cluster_id=cid)
            conn.execute('INSERT OR REPLACE INTO fingerprints VALUES (?,?)',(IDSystem.generate_fingerprint(cid,'site','site-wide'),key))
            conn.executemany('INSERT OR REPLACE INTO fingerprints VALUES (?,?)',((IDSystem.generate_fingerprint(cid,t,'template-aggregate'),key) for t in templates))
        for row in conn.execute('SELECT * FROM opportunities WHERE run_id=? ORDER BY opportunity_id',(run_id,)):
            opportunity=dict(row)
            match=conn.execute('SELECT candidate_id FROM fingerprints WHERE fingerprint=?',(opportunity.get('fingerprint'),)).fetchone()
            key=match[0] if match else candidate_key(opportunity)
            conn.execute('INSERT INTO candidate_membership VALUES (?,?,?)',(run_id,opportunity['opportunity_id'],key))
            if not match:
                conn.execute('INSERT INTO keyed_opportunities VALUES (?,?,?)',(key,json.dumps(opportunity),opportunity['opportunity_id']))
        conn.commit()

        def evidence(template, urls):
            marks=','.join('?' for _ in urls)
            query=f'SELECT * FROM pages WHERE crawl_id=? AND url IN ({marks}) ORDER BY url'
            rows=conn.execute(query,(run_id,*urls))
            first=rows.fetchone()
            if first is None:
                rows=conn.execute('SELECT * FROM pages WHERE crawl_id=? AND template_id=? ORDER BY url',(run_id,template))
                first=rows.fetchone()
            from itertools import chain
            cohort=chain([first],rows) if first is not None else ()
            status, canonical=Counter(),Counter()
            n=indexable=words=links=hashes=0
            minwords=None
            # DISTINCT content hashes are stored by SQLite, not a Python site-sized set.
            conn.execute('CREATE TEMP TABLE IF NOT EXISTS cohort_hashes(hash TEXT PRIMARY KEY)')
            conn.execute('DELETE FROM cohort_hashes')
            for p in cohort:
                n+=1; w=int(p['word_count'] or 0); words+=w
                minwords=w if minwords is None else min(w,minwords)
                indexable+=bool(p['is_indexable']); links+=int(p['internal_links_count'] or 0)
                status[str(p['status_code'] or 0)]+=1; canonical[p['canonical_status'] or 'unknown']+=1
                if p['content_hash']:
                    hashes+=1; conn.execute('INSERT OR IGNORE INTO cohort_hashes VALUES (?)',(p['content_hash'],))
            unique=conn.execute('SELECT COUNT(*) FROM cohort_hashes').fetchone()[0]
            indexability=dict(indexable=indexable,non_indexable=n-indexable,canonical_statuses=dict(canonical))
            return dict(status_distribution=dict(status),indexability=indexability,canonical_relationship=indexability,
                        content_metrics=dict(pages=n,min_words=minwords or 0,avg_words=round(words/max(n,1),1),unique_content_hashes=unique,duplicate_content_pages=hashes-unique),
                        link_metrics=dict(avg_internal_links=round(links/max(n,1),1)))

        for row in conn.execute('SELECT * FROM issue_clusters WHERE crawl_id=? ORDER BY id',(run_id,)):
            c=dict(row); template=c.get('primary_affected_template') or 'default'
            urls=sorted(set(samples(c.get('sample_urls'))))[:5]
            yield LayaCandidateInput(cluster_id=candidate_key(cluster_id=c['cluster_id']),template_id=template,issue_type=c['issue'],page_count=c['affected_urls_count'],sample_urls=urls,
                 severity_hint=c.get('severity') or 'medium',category_hint=c.get('category') or 'technical',evidence_refs=[c.get('evidence_summary') or ''],**evidence(template,urls))
        for (key,) in conn.execute('SELECT DISTINCT key FROM keyed_opportunities ORDER BY key'):
            first=None; urls=set(); count=0
            for (payload,) in conn.execute('SELECT payload FROM keyed_opportunities WHERE key=? ORDER BY opportunity_id',(key,)):
                o=json.loads(payload)
                if first is None: first=o
                # Only the lexicographically first five URLs are model-visible in the old reducer.
                urls=set(sorted(urls | set(samples(o.get('sample_urls_json'))))[:5])
                count+=int(o.get('affected_urls_count') or 1)
            templates_for_first=samples(first.get('affected_templates_json'))
            template=templates_for_first[0] if templates_for_first else first.get('implementation_location') or 'default'
            urls=sorted(urls)
            yield LayaCandidateInput(cluster_id=key,template_id=template,issue_type=first.get('observation') or first['type'],page_count=count,sample_urls=urls,
                 severity_hint=(first.get('opportunity_tier') or 'medium').lower(),category_hint=first['type'],evidence_refs=[first.get('hypothesis') or ''],**evidence(template,urls))
        conn.commit()


class LocalMLXService:
    def __init__(self, config, guard, cache_db=None):
        from .analyzer import LayaSEOAnalyzer
        from .worker_pool import LayaWorkerPool
        guard.checkpoint(reserve_mb=1024)
        self.guard=guard
        self.analyzer=LayaSEOAnalyzer.get_singleton(options={'memory_guard':guard})
        self.analyzer.get_backend().guard=guard
        self.checkpoint_id=self.analyzer.preflight()['checkpoint_id']
        self.pool=LayaWorkerPool(cache_db_path=cache_db,settings=config.get('laya',{}),num_workers=1)
        self.pool._analyzer=self.analyzer
        self.throttle=config['runtime']['throttle_seconds']

    def submit_batch(self, candidates, run_id=''):
        decisions=[]
        for candidate in candidates:
            self.guard.checkpoint()
            decision=self.pool._make_decision(candidate,run_id)
            self.pool._persist_decision(decision)
            decisions.append(decision)
            if self.throttle:
                time.sleep(self.throttle)
        return decisions


def class_record(candidate, checkpoint_id):
    # Families partition work; exact prompt identity alone permits decision reuse.
    family=template_family(candidate.sample_urls[0], 'candidate') if candidate.sample_urls else candidate.template_id
    return dict(class_id=candidate.compute_hash(checkpoint_id),family=family,candidate=candidate.to_dict())


def fan_out(decision, member):
    return LayaDecision.from_dict({**decision.to_dict(), 'cluster_id':member['candidate_id'],
                                  'affected_count':member['affected_count'], 'evidence_refs':member['evidence_refs']})


def decide_classes(candidates, service, store, guard, run_id):
    """Durable, idempotent class decisions with explicit candidate membership."""
    total=unique=0
    store.clear('members:'+run_id)
    for candidate in candidates:
        guard.checkpoint()
        record=class_record(candidate,service.checkpoint_id)
        key=record['class_id']
        member=dict(class_id=key,candidate_id=candidate.cluster_id,affected_count=candidate.page_count,
                    sample_urls=candidate.sample_urls,evidence_refs=candidate.evidence_refs)
        store.put('members:'+run_id,candidate.cluster_id,member)
        contract_key=key+':'+json.dumps(service.pool.settings['confidence'],sort_keys=True)
        cached=store.get('decisions',contract_key)
        if cached is None:
            result=service.submit_batch([candidate],run_id)[0]
            store.put('classes',key,record)
            store.put('decisions',contract_key,result.to_dict())
            unique+=1
        else:
            result=LayaDecision.from_dict({**cached,'run_id':run_id,'from_cache':True})
        total+=1
        yield fan_out(result,member)
    distinct=store.count_classes('members:'+run_id)
    store.put('metrics',run_id,dict(candidates=total,unique_classes=distinct,new_class_decisions=unique,
                                  cache_reuses=total-unique,dedupe_ratio=1-distinct/max(total,1)))


def class_opportunities(db_path, run_id):
    """One work order input per decision class, with explicit opportunity membership."""
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory=sqlite3.Row
        conn.execute('CREATE TABLE IF NOT EXISTS work_order_membership(run_id TEXT,class_id TEXT,opportunity_id TEXT,PRIMARY KEY(run_id,class_id,opportunity_id))')
        conn.execute('DELETE FROM work_order_membership WHERE run_id=?',(run_id,))
        conn.execute('INSERT INTO work_order_membership SELECT run_id,laya_decision_id,opportunity_id FROM opportunities WHERE run_id=? AND laya_validated=1',(run_id,))
        conn.commit()
        for (class_id,) in conn.execute('SELECT DISTINCT class_id FROM work_order_membership WHERE run_id=? ORDER BY class_id',(run_id,)):
            first=None; count=0; urls=set(); affected=0
            for row in conn.execute('SELECT * FROM opportunities WHERE run_id=? AND laya_decision_id=? AND laya_validated=1 ORDER BY opportunity_id',(run_id,class_id)):
                row=dict(row)
                if first is None:first=row
                count+=1;affected=max(affected,int(row.get('affected_urls_count') or 1))
                urls=set(sorted(urls | set(samples(row.get('sample_urls_json'))))[:5])
            # The class candidate count is authoritative; summed overlapping opportunities are not.
            decision=conn.execute('SELECT affected_count FROM laya_decisions WHERE crawl_id=? AND decision_id=?',(run_id,class_id)).fetchone()
            yield {**first,'class_id':class_id,'member_count':count,
                   'affected_urls_count':decision[0] if decision else affected,'sample_urls_json':json.dumps(sorted(urls))}
