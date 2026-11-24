# Order Ops Analytics

A reproducible retail order pipeline that rejects bad records before reporting business metrics. Python + SQLite + SQL window functions + plain JavaScript. No paid services or runtime Python dependencies.

**AI-assisted portfolio project, November 2026. Synthetic data, not a client engagement or employment record.** The implementation was generated and tested with AI assistance. A candidate should understand and be able to modify it before presenting it as evidence of their own skills.

## Run in five commands

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
order-ops --generate
python -m http.server 8000 --directory site
```

Open http://localhost:8000. Test with `python -m pytest -q`. Python 3.10 or newer. For your own input use `order-ops --source your.csv` without `--generate`. The CSV must match the field order in the sample generated at `data/orders.csv`. Every input is a complete snapshot, not an incremental feed.

Docker alternative: `docker build -t order-ops .` then `docker run --rm -p 8000:8000 order-ops`. Dockerfile supplied, but Docker runtime was not available for build validation in this environment.

## Reproduced results

- 2,405 generated input rows, 2,400 accepted and 5 quarantined.
- One rejected record for each seeded defect: duplicate ID, negative quantity, non-finite price, impossible date, unknown region.
- 16 pytest tests pass, including reconciliation, repeated-run stability, invalid schema preserving the old snapshot, numerical validation and delivered-only accounting.
- Browser checks cover region filtering, CSV export, desktop/mobile rendering and no page errors.
- Displayed sales are synthetic EGP metrics, not measured business impact.

## Data flow

```text
Seeded CSV -> schema contract -> row validation -> accepted records -> atomic SQLite snapshot
                                        |                                |
                                        +-> quarantine.json             +-> monthly SQL view
                                                                         +-> data.json -> browser filters
```

Validation happens before the database transaction. A malformed schema raises an error without deleting the previous snapshot. Invalid rows are quarantined, not silently fixed. The complete valid snapshot is replaced in one transaction. A SHA-256 source digest and row reconciliation are recorded in `runs` and `site/quality.json`. A repeat source does not duplicate orders.

## Metric definitions

| Metric | Definition |
|---|---|
| Delivered revenue | Sum of discounted `net_cents` for status=delivered, divided by100 |
| Average order value | Delivered revenue / delivered order count |
| Return rate | Returned orders / all valid orders, including pending and cancelled |
| Monthly revenue | Delivered revenue grouped by order month, not delivery month |

Prices are integer piastres in storage. Discount multiplication uses Decimal and rounds half-even to the nearest piastre. This simplified demo does not model tax, partial refunds, shipping fees, currency conversion or payment reconciliation. Never use its metrics as audited accounting.

`sql/business_questions.sql` contains month-over-month growth, return rate by region, repeat customers and category contribution queries. `monthly_revenue` uses a CTE and LAG. Missing months in external inputs are not filled, so LAG means previous observed month.

## Files

- `src/order_ops/pipeline.py`: generator, validation, transaction and exports.
- `tests/test_pipeline.py`: isolated temporary-database tests.
- `data/orders.csv`: synthetic input generated locally by `order-ops --generate`.
- `site/`: static dashboard. Run `order-ops --generate` to create its data artifacts before opening it.
- `sql/business_questions.sql`: analyst-facing questions and SQL.
- `docs/WALKTHROUGH.ar.md`: Arabic study guide and honest interview talking points.

## Limits and next steps

Complete in-memory CSV processing suits a small demo, not huge files. Duplicate conflict policy accepts the first valid row. The UI exports only validated, filtered rows. No actual API integration, scheduler deployment, user authentication, Power BI file, real customers or production usage is claimed. Next: incremental ingestion with explicit upsert semantics, warehouse migrations, source freshness alerts, refund events and a real-world licensed dataset.

## Why this project

Employer requirements reviewed24November2026: Wallets asks cleaning/reporting/dashboard work and SQL/PowerBI as a plus; Beseha asks Python,SQL,Git,tests and clear documentation; HireHangar asks metric monitoring and definitions. These are requirement signals, not employer endorsement.

- https://walletsproperties.com/careers/data-analyst-intern
- https://beseha.com/careers/jobs/tech-data-automation-intern-beseha-academy/
- https://jobs.ashbyhq.com/hirehangar/3c708fbc-3ef1-437f-b45b-7277ed2e3adf/application
- SQLite Python reference: https://docs.python.org/3/library/sqlite3.html
