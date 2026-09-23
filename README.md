# SEOJEV — Universal Scalable SEO Intelligence & Audit Engine

SEOJEV is a production-quality, scalable, reusable SEO crawling and intelligence system built for universal website auditing. It operates asynchronously, extracts comprehensive on-page and technical SEO signals, clusters pages into architectural templates, models internal link graphs using NetworkX, evaluates representative Core Web Vitals via Playwright, and employs local Apple Silicon MLX inference using `aac6fef/laya-mlx` for structured issue classification and prioritization.

## Key Features

- **Universal Architecture**: Works against any website URL (`python main.py https://example.com/`).
- **Scale**: Capable of indexing 10,000+ URLs with SQLite WAL persistence, bounded memory footprints, and asynchronous HTTP connection pooling.
- **Protocol & Compliance**: Full `/robots.txt` directive parsing, recursive XML sitemap index processing, and canonical normalization.
- **Selective Rendering**: Playwright headless browser rendering triggered dynamically on JavaScript-heavy or thin initial HTML payloads.
- **Internal Link Graph**: NetworkX graph computation evaluating page structural importance, crawl depth, and orphan page detection.
- **Template Clustering**: Automatically clusters URLs into template groups, calculating systemic health and aggregating issues at the template level.
- **Core Web Vitals**: Real browser performance auditing measuring TTFB, FCP, LCP, and CLS on representative stratified sample sets.
- **Local Laya MLX Model**: Fast on-device inference via `aac6fef/laya-mlx` for compact, structured issue classification and action prioritization.
- **Full Report Suite**: Generates a 14-section Word document (`seo-audit.docx`), CSV inventories, and strict JSON summaries.

## Usage

```bash
# Production crawl
python main.py https://www.drivio.in/ \
    --max-pages 5000 \
    --concurrency 10 \
    --render \
    --performance-sample 100 \
    --resume \
    --output reports/
```

### Options

- `--max-pages`: Maximum URLs to crawl (default: 5000)
- `--concurrency`: Concurrent asynchronous requests (default: 10)
- `--delay`: Delay between requests in seconds (default: 0.05)
- `--render`: Enable selective Playwright browser rendering
- `--performance-sample`: Number of URLs for representative Web Vitals audit (default: 100)
- `--resume`: Resume previous crawl from database
- `--fresh`: Start fresh crawl ignoring prior state
- `--output`: Deliverables output directory (default: `reports/`)

## Deliverables Generated

- `reports/seo-audit.docx`: 14-section executive Word audit report
- `reports/pages.csv`: Granular page-by-page SEO extraction inventory
- `reports/issues.csv`: Register of all detected issues, severities, and recommendations
- `reports/templates.csv`: Template clusters and health metrics
- `reports/internal-links.csv`: Internal link graph edge list
- `reports/performance.csv`: Representative browser Core Web Vitals sample
- `reports/laya-decisions.csv`: Local Laya MLX inference decisions and latency log
- `reports/summary.json`: High-level summary metrics
- `reports/crawl-summary.json`: Comprehensive crawl and distribution breakdown
- `data/site-profile.json`: Adaptive website profile
