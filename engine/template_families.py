"""Route-family grouping; dynamic slots never erase static route suffixes."""
import json
import re
from urllib.parse import parse_qsl, unquote, urlsplit

CITIES = ('new-delhi', 'delhi', 'mumbai', 'bengaluru', 'bangalore', 'chennai', 'hyderabad', 'pune', 'kolkata', 'jaipur', 'ahmedabad', 'lucknow', 'kochi', 'surat', 'indore', 'bhopal', 'patna', 'nagpur', 'nashik', 'mysuru', 'agra', 'kanpur')
STATIC = {'price', 'on-road-price', 'images', 'specifications', 'reviews', 'variants', 'colours', 'mileage', 'videos', 'dealers', 'compare', 'comparison'}
CATALOG = {'bike', 'bikes', 'scooters', 'electric-vehicles'}
EDITORIAL = {'news', 'featured-stories', 'expert-articles', 'reviews', 'blog'}


def mask_tokens(text):
    for city in sorted(CITIES, key=len, reverse=True):
        text = re.sub(r'(?<![a-z])' + re.escape(city) + r'(?![a-z])', '{city}', text, flags=re.I)
    return re.sub(r'\d+(?:[.,]\d+)*', '{number}', text)


def template_family(url, page_type='other'):
    parsed = urlsplit(url)
    parts = unquote(parsed.path).strip('/').split('/') if parsed.path.strip('/') else []
    if parts:
        root = parts[0].lower()
        if root in EDITORIAL and len(parts) >= 2:
            # Keep malformed nested editorial routes separate from ordinary articles.
            parts[1] = '{article}'
        elif root in CATALOG:
            for index in range(1, min(len(parts), 3)):
                if parts[index] not in STATIC:
                    parts[index] = '{brand}' if index == 1 else '{model}'
        elif root in ('compare', 'comparison') and len(parts) >= 2:
            parts[1] = '{comparison}'
        elif len(parts) == 1 and re.search(r'-(?:bikes|scooters|ev)$', root):
            parts[0] = '{brand}-' + root.rsplit('-', 1)[1]
        elif page_type in ('listing', 'model', 'brand') and len(parts) == 2 and root not in EDITORIAL:
            parts = ['{brand}', '{model}']
    route = '/'.join(mask_tokens(part.lower()) for part in parts)
    # Query keys affect route behavior; retain unknown values conservatively.
    query = [(k, '{city}' if k.lower() == 'city' else mask_tokens(v)) for k,v in sorted(parse_qsl(parsed.query, keep_blank_values=True))]
    return json.dumps([page_type, route, query], separators=(',', ':'))
