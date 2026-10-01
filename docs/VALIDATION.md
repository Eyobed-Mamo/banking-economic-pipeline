# Validation record

Build validation: October 1, 2026.

## Executed checks

- Python 3.12 with pandas 2.3.3 and psycopg 3.3.6.
- All 23 tests passed, including integration tests against a separate local PostgreSQL 18 database.
- Tests cover FRED pagination, retry configuration, safe error messages, missing values, invalid records, duplicate conflicts, incremental windows, periodic full refreshes, upsert idempotency/revisions, yield-spread units, CPI calendar alignment, quarterly grain, failure isolation, and snapshot dates.
- Report field references and model relationships checked against the delivered model.
- All 40 Power BI definition files validated using Microsoft's published schemas and their referenced definitions, with zero errors.
- Synthetic demo loaded: **6,754 observations across seven series**, 2015–2025; all series completed successfully.
- Demo view counts: 792 monthly rows; 2,870 matched yield dates; 132 CPI months; 7 snapshot rows; 44 credit quarters; 574 mortgage-spread rows.

## Not verified here

- Live FRED requests with a user API key (none was available).
- Native Power BI Desktop rendering, DAX engine evaluation, or service publishing.
- Docker Compose execution (Docker was not installed in the build environment). The SQL implementation was exercised using native PostgreSQL.
- Daily operating-system scheduling or Power BI gateway refresh. Scripts and setup instructions are provided; no recurring task was installed.

These distinctions are intentional: schema validation does not prove a Power BI report renders correctly, and synthetic test data is not real economic evidence.
