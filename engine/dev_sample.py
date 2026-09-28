"""Read-only, seeded stratification; only selected page payloads leave SQLite."""
import hashlib
import sqlite3
from pathlib import Path


def sample_urls(conn, crawl_id, limit=500, seed=42):
    if not 1 <= limit <= 500:
        raise ValueError('Development samples must contain 1..500 URLs')
    counts = dict(conn.execute("SELECT COALESCE(template_id,'unknown'),COUNT(*) FROM pages WHERE crawl_id=? GROUP BY COALESCE(template_id,'unknown') ORDER BY 1", (crawl_id,)))
    quotas = {t: min(3, n) for t, n in counts.items()}
    if sum(quotas.values()) > limit:
        raise ValueError('500 URL cap cannot cover every template with min(3, available); select a smaller source cohort explicitly')
    target = min(limit, sum(counts.values()))
    # Largest deficit allocation preserves minimum representation and proportionality.
    while sum(quotas.values()) < target:
        eligible = [t for t in counts if quotas[t] < counts[t]]
        t = max(eligible, key=lambda t: (target * counts[t] / sum(counts.values()) - quotas[t], t))
        quotas[t] += 1
    conn.create_function('sample_rank', 1, lambda u: hashlib.sha256(f'{seed}:{u}'.encode()).hexdigest(), deterministic=True)
    selected = []
    for template, n in quotas.items():
        selected.extend(r[0] for r in conn.execute("SELECT url FROM pages WHERE crawl_id=? AND COALESCE(template_id,'unknown')=? ORDER BY sample_rank(url),url LIMIT ?", (crawl_id, template, n)))
    return sorted(selected)


def build_sample(source, destination, crawl_id=None, limit=500, seed=42, target=None):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or destination.exists():
        raise ValueError('Sample destination must be a new file distinct from source')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src:
        src.execute('PRAGMA temp_store=FILE')
        src.execute('PRAGMA cache_size=-2048')
        if crawl_id is None:
            row = src.execute('SELECT crawl_id FROM crawl_runs WHERE (? IS NULL OR target_url=?) AND EXISTS (SELECT 1 FROM pages p WHERE p.crawl_id=crawl_runs.crawl_id) ORDER BY start_time DESC LIMIT 1', (target, target)).fetchone()
            if row is None:
                raise ValueError('No existing crawl with pages; development never starts a crawl')
            crawl_id = row[0]
        urls = sample_urls(src, crawl_id, limit, seed)
        if not urls:
            raise ValueError('Source crawl has no pages')
        src.execute('CREATE TEMP TABLE selected(url TEXT PRIMARY KEY)')
        src.executemany('INSERT INTO selected VALUES (?)', ((u,) for u in urls))
        with sqlite3.connect(destination) as dst:
            tables = dict(src.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
            # Rebuild downstream evidence on the sample; never copy stale full-site aggregates.
            for table in ('crawl_runs', 'pages', 'urls', 'issues', 'links', 'images', 'schemas', 'performance'):
                if table not in tables:
                    continue
                dst.execute(tables[table])
                columns = [r[1] for r in src.execute(f'PRAGMA table_info("{table}")')]
                if 'crawl_id' not in columns:
                    continue
                urlcol = next((c for c in ('url', 'source_url', 'page_url') if c in columns), None)
                clause = f' AND "{urlcol}" IN (SELECT url FROM selected)' if urlcol else ''
                if table != 'crawl_runs' and not urlcol:
                    continue
                query = f'SELECT * FROM "{table}" WHERE crawl_id=?{clause}'
                dst.executemany(f'INSERT INTO "{table}" VALUES ({",".join("?" for _ in columns)})', src.execute(query, (crawl_id,)))
            dst.execute('UPDATE crawl_runs SET max_pages=?,concurrency=2', (len(urls),))
    return crawl_id, urls
