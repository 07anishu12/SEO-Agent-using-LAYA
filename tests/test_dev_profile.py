import sqlite3
import pytest
from engine.dev_sample import sample_urls
from engine.profiles import resolve_profile
from engine.template_families import template_family


def test_sampler_covers_families_and_is_seeded():
    conn=sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE pages(crawl_id,url,page_type,template_id)')
    for kind,n in [('price',250),('images',80),('specifications',3),('variants',2)]:
        conn.executemany('INSERT INTO pages VALUES (?,?,?,?)',(('r',f'https://x/bikes/tvs/raider-{i}/{kind}','model',kind) for i in range(n)))
    picked=sample_urls(conn,'r',100,42)
    assert picked==sample_urls(conn,'r',100,42)
    assert picked!=sample_urls(conn,'r',100,43)
    assert len(picked)==100
    for suffix, minimum in [('price',3),('images',3),('specifications',3),('variants',2)]:
        assert sum(u.endswith('/'+suffix) for u in picked)>=minimum
    with pytest.raises(ValueError): sample_urls(conn,'r',5)


def test_profile_caps_env(monkeypatch):
    monkeypatch.setenv('SEOJEV_MAX_URLS','5000000')
    monkeypatch.setenv('SEOJEV_MAX_WORKERS','32')
    assert resolve_profile()['runtime']['max_urls']==500
    assert resolve_profile()['runtime']['max_workers']==2
    assert resolve_profile(profile='prod')['runtime']['max_workers']==32


def test_mask_preserves_routes():
    family=lambda path:template_family('https://x/'+path,'model')
    assert family('bikes/tvs/raider-125/price/delhi')==family('bikes/honda/shine-150/price/mumbai')
    assert len({family('bikes/tvs/raider-125/'+s) for s in ['price','images','specifications','variants']})==4
    assert family('bike/tvs/raider-125/specifications')!=family('bikes/tvs/raider-125/specifications')
    assert family('news/article')!=family('news/article/nested/url')
    assert family('bikes/a/b?sort=price')!=family('bikes/a/b?sort=mileage')
