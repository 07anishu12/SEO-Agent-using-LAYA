import json
import sqlite3
from pathlib import Path
from scripts.gen_synthetic_site import generate, KINDS


def source(path):
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE pages(crawl_id,url,title,description,h1_text,template_id,page_type)')
        for url,kind in [('bikes/tvs/raider','model'),('bikes/tvs/raider/price','model'),('compare','comparison'),('bikes/tvs','brand'),('bikes','listing'),('news/article','article')]:
            c.execute('INSERT INTO pages VALUES (?,?,?,?,?,?,?)',('r','https://x/'+url,kind,'description',kind,kind,kind))


def test_generator_deterministic_and_labelled(tmp_path):
    db=tmp_path/'source.db';source(db)
    a,b=tmp_path/'a',tmp_path/'b'
    for out in (a,b):generate(db,'r',out,cities=2,price_variants=4,defect_rate=.4)
    assert {str(p.relative_to(a)):p.read_bytes() for p in a.rglob('*') if p.is_file()} == {str(p.relative_to(b)):p.read_bytes() for p in b.rglob('*') if p.is_file()}
    truth=json.loads((a/'ground_truth.json').read_text())
    assert len(truth)==48 and any(not d for d in truth.values())
    assert set(d for ds in truth.values() for d in ds)==set(__import__('scripts.gen_synthetic_site',fromlist=['DEFECTS']).DEFECTS)
    from bs4 import BeautifulSoup
    inbound=set();titles={}
    for line in (a/'manifest.jsonl').read_text().splitlines():
        row=json.loads(line); soup=BeautifulSoup((a/row['file']).read_text(),'html.parser')
        inbound.update(a['href'] for a in soup.find_all('a',href=True));titles[row['url']]=soup.title.text
    for url,labels in truth.items():
        assert (url not in inbound)==('orphan_page' in labels)
        if 'duplicate_title' in labels:assert list(titles.values()).count(titles[url])>=2
