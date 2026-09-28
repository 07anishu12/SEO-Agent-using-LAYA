"""Seeded, disk-streamed fixtures derived from observed crawl route/metadata exemplars."""
import argparse
import hashlib
import html
import json
import sqlite3
from pathlib import Path

KINDS = ('variant', 'city-price', 'comparison', 'brand', 'listing', 'blog')
CITIES = ('Delhi', 'Mumbai', 'Bengaluru', 'Chennai', 'Hyderabad', 'Pune', 'Kolkata', 'Jaipur', 'Ahmedabad', 'Lucknow', 'Kochi', 'Surat', 'Indore', 'Bhopal', 'Patna', 'Nagpur', 'Nashik', 'Mysuru', 'Agra', 'Kanpur')
DEFECTS = ('missing_title', 'duplicate_title', 'thin_content', 'bad_canonical', 'broken_schema', 'orphan_page', 'wrong_city_title', 'price_mismatch', 'noindex_money')


def exemplars(db, crawl_id):
    predicates = ("page_type='model' AND url LIKE '%/bikes/%' AND url NOT LIKE '%/price' AND url NOT LIKE '%/images'",
                  "url LIKE '%/price%'", "page_type='comparison'", "page_type='brand'",
                  "page_type='listing'", "page_type='article'")
    with sqlite3.connect(Path(db).resolve().as_uri() + '?mode=ro', uri=True) as conn:
        conn.row_factory = sqlite3.Row
        result = {}
        for kind, predicate in zip(KINDS, predicates):
            row = conn.execute(f"SELECT url,title,description,h1_text,template_id FROM pages WHERE crawl_id=? AND ({predicate}) ORDER BY LENGTH(title)=0,url LIMIT 1", (crawl_id,)).fetchone()
            if row is None:
                raise ValueError(f'Existing crawl lacks a {kind} exemplar')
            result[kind] = dict(row)
        return result


def unit(seed, index, label):
    return int(hashlib.sha256(f'{seed}:{index}:{label}'.encode()).hexdigest()[:16], 16) / 2**64


def defects_at(index, kind, seed, rate):
    if index % 10 == 0:  # Reserved controls, never used for threshold calibration.
        return []
    applicable = [d for d in DEFECTS if d != 'noindex_money' or kind != 'blog']
    defects = [d for d in applicable if unit(seed, index, d) < rate]
    if 'missing_title' in defects:
        defects = [d for d in defects if d not in ('duplicate_title', 'wrong_city_title')]
    if 'duplicate_title' in defects:
        defects = [d for d in defects if d != 'wrong_city_title']
    return defects


def page_url(kind, city, variant):
    slug = city.lower()
    paths = {'variant': f'bikes/tvs/raider-125/variant-{variant}/{slug}',
             'city-price': f'bikes/tvs/raider-125/price/{slug}/{variant}',
             'comparison': f'compare/tvs-raider-125-vs-bajaj-pulsar-125/{slug}/{variant}',
             'brand': f'bikes/tvs/{slug}/{variant}', 'listing': f'bikes/under-{100000+variant*10000}/{slug}',
             'blog': f'featured-stories/commuting-in-{slug}-{variant}'}
    return 'https://synthetic.drivio.test/' + paths[kind]


def generate(db, crawl_id, output, cities=20, price_variants=4, seed=42, defect_rate=.12, templates=KINDS, limit=500):
    if cities < 1 or price_variants < 1 or cities > len(CITIES) or not 0 <= defect_rate <= 1:
        raise ValueError('Invalid city count, price variants or defect rate')
    total = len(templates) * cities * price_variants
    if total > min(limit, 5000):
        raise ValueError('Synthetic size exceeds configured limit (absolute ceiling 5000)')
    refs = exemplars(db, crawl_id)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'pages').mkdir()
    counts = dict.fromkeys(DEFECTS, 0)
    clean = 0
    # Deterministic index mapping lets links exclude orphan targets without a site-sized list.
    def coordinates(i):
        return templates[i // (cities*price_variants)], CITIES[(i // price_variants) % cities], i % price_variants
    with (output / 'ground_truth.json').open('w') as truth, (output / 'manifest.jsonl').open('w') as manifest:
        truth.write('{\n')
        for index in range(total):
            kind, city, variant = coordinates(index)
            defects = defects_at(index, kind, seed, defect_rate)
            # Ensure a duplicate is actually shared even in a tiny fixture.
            if 'duplicate_title' in defects and sum('duplicate_title' in defects_at(j, coordinates(j)[0], seed, defect_rate) for j in range(total)) < 2:
                defects.remove('duplicate_title')
            for defect in defects:
                counts[defect] += 1
            clean += not defects
            url = page_url(kind, city, variant)
            price = 95000 + variant*12000 + CITIES.index(city)*850
            emi = round(price*.8 * (.10/12) / (1-(1+.10/12)**-36))
            subject = {'variant': 'TVS Raider 125', 'city-price': 'TVS Raider 125 on-road price', 'comparison': 'TVS Raider 125 vs Bajaj Pulsar 125', 'brand': 'TVS bikes', 'listing': 'Best commuter bikes', 'blog': 'Two-wheeler commuting guide'}[kind]
            title_city = CITIES[(CITIES.index(city)+1) % len(CITIES)] if 'wrong_city_title' in defects else city
            title = f'{subject} in {title_city} — option {variant+1} | Drivio'
            if 'duplicate_title' in defects:
                title = 'Two-wheeler prices and EMI | Drivio'
            if 'missing_title' in defects:
                title = ''
            heading = f'{subject} in {city}, option {variant+1}'
            description = f'Explore {subject.lower()} in {city}: ₹{price:,} on-road, monthly EMI ₹{emi:,}, mileage, specifications, ownership costs and local dealer information.'
            paragraphs = [f'{heading}. The local on-road price is INR {price}. Estimated EMI is INR {emi} for 36 months with 20 percent down payment at 10 percent annual interest. Insurance, registration and dealer charges vary by city; this illustration separates these costs for {city} buyers.',
                f'For daily journeys in {city}, compare seat comfort, braking performance, fuel economy and service availability. The {subject} selection includes practical commuter choices. Check the quoted ex-showroom amount, registration costs, insurance coverage and accessories before choosing option {variant+1}.',
                f'Test ride in normal traffic and on uneven roads. Ask the dealer in {city} about warranty coverage, service intervals and available colours. Compare total repayment over the full loan period instead of using monthly EMI alone. Review the written quotation and confirm current delivery estimates.',
                f'Ownership in {city} includes fuel, routine maintenance, insurance renewals and parking. A lightweight commuter can simplify short daily trips; a larger motorcycle may suit longer journeys. Compare usable performance, riding position and pillion comfort against your own travel needs before selecting this {subject.lower()}.',
                'Frequently asked questions: Does the price include registration? Yes, the displayed illustration is on-road. Can the loan term change? The estimate uses 36 months; lenders may offer other terms. Is insurance included? The quote includes an illustrative policy. Confirm final pricing directly with the dealer before purchase.']
            body = '<p>Contact the dealer.</p>' if 'thin_content' in defects else ''.join('<p>'+html.escape(p)+'</p>' for p in paragraphs)
            schema = {'@context': 'https://schema.org', '@type': 'Article' if kind == 'blog' else 'Product', 'name': heading, 'url': url}
            if kind != 'blog':
                schema['offers'] = {'@type': 'Offer', 'priceCurrency': 'INR', 'price': price+17000 if 'price_mismatch' in defects else price, 'availability': 'https://schema.org/InStock', 'url': url}
            elif 'price_mismatch' in defects:
                # Blog contains a quoted example price too; mismatch is observable in text.
                body += f'<p>Price summary: INR {price+17000}</p>'
            schema_text = '{"@type":' if 'broken_schema' in defects else json.dumps(schema)
            canonical = 'https://unrelated.invalid/removed' if 'bad_canonical' in defects else url
            links = []
            # Every non-orphan has an inbound ring link; orphan pages may link outward.
            for offset in range(1, total+1):
                j = (index+offset) % total
                k, c, v = coordinates(j)
                if 'orphan_page' not in defects_at(j, k, seed, defect_rate):
                    links.append(f'<a href="{page_url(k,c,v)}">{html.escape(k+" in "+c)}</a>')
                    break
            robots = 'noindex,follow' if 'noindex_money' in defects else 'index,follow'
            document = f'<!doctype html><html lang="en"><head><title>{html.escape(title)}</title><meta name="description" content="{html.escape(description,quote=True)}"><meta name="robots" content="{robots}"><link rel="canonical" href="{canonical}"><script type="application/ld+json">{schema_text}</script></head><body><main><h1>{html.escape(heading)}</h1>{body}</main><nav>{"".join(links)}</nav></body></html>'
            filename = f'pages/{index:06d}.html'
            (output / filename).write_text(document)
            manifest.write(json.dumps(dict(url=url, template=kind, city=city, price=price, file=filename, source=refs[kind]))+'\n')
            truth.write((',' if index else '') + json.dumps(url)+':'+json.dumps(defects)+'\n')
        truth.write('}\n')
    metadata = dict(seed=seed, pages=total, clean_pages=clean, planted_counts=counts, requested_rate=defect_rate,
                    rate_definition='Independent per eligible non-control page; mutually exclusive title defects; every tenth page reserved clean', exemplars=refs)
    (output / 'generation.json').write_text(json.dumps(metadata, indent=2))
    return metadata


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', required=True); p.add_argument('--crawl-id', required=True)
    p.add_argument('--output', required=True); p.add_argument('--cities', type=int, default=20)
    p.add_argument('--price-variants', type=int, default=4); p.add_argument('--seed', type=int, default=42)
    p.add_argument('--defect-rate', type=float, default=.12)
    p.add_argument('--templates', nargs='+', choices=KINDS, default=KINDS)
    p.add_argument('--limit', type=int, default=500)
    a = p.parse_args()
    result = generate(a.db, a.crawl_id, a.output, a.cities, a.price_variants, a.seed, a.defect_rate, a.templates, a.limit)
    print(json.dumps({k:v for k,v in result.items() if k != 'exemplars'}))
