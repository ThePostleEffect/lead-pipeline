# Lead Pipeline

Private-company lead discovery, enrichment, filtering, scoring, and export.

CLI-first design for use by OpenClaw agents.

## Setup

```bash
pip install -r requirements.txt
```

## Quick Start

```bash
# Collect leads for a lane (outputs JSON to stdout)
python -m app.main collect --lane bankruptcy --limit 25 --format json

# Collect with minimum quality filter
python -m app.main collect --lane capital_seeking --limit 25 --min-quality mid_level --format json

# Save collected leads to a file
python -m app.main collect --lane charged_off --format json --output data/output/leads.json

# Summarize top leads
python -m app.main summarize --input data/output/leads.json --top 10

# Export to Excel workbook
python -m app.main export --input data/output/leads.json --xlsx data/output/leads.xlsx

# Print current pipeline rules
python -m app.main rules

# Filter existing leads
python -m app.main filter --input data/output/leads.json --lane bankruptcy --min-quality best_case

# Rank leads by quality and confidence
python -m app.main rank --input data/output/leads.json
```

## Lead Lanes

| Lane | Description | Excluded States |
|------|-------------|-----------------|
| `charged_off` | Private companies selling/buying charged-off debt | TX, NC, SC, PA, AZ, CA |
| `bankruptcy` | Private companies with bankruptcy opportunities | (none) |
| `performing` | Private companies with performing portfolios | (none) |
| `capital_seeking` | Private companies seeking capital/financing | HI, AK |

## Quality Tiers

- **best_case** — company_name, website, business_phone, reason_qualified, named_contact, contact_title all present
- **mid_level** — company_name, website, business_phone, reason_qualified all present
- **weak** — missing critical fields → automatically discarded

## Discard Rules

1. `quality_tier == weak` → discard
2. State excluded for the lead's lane → discard
3. `public_company_confirmed == true` → discard
4. `trustee_related == true` → discard

## Scoring (0–100)

| Field | Points |
|-------|--------|
| company_name | +15 |
| website | +15 |
| business_phone | +15 |
| reason_qualified | +15 |
| named_contact | +10 |
| contact_title | +10 |
| employee_estimate 10–50 | +10 |
| distress_signal | +5 |
| financing_signal | +5 |

## Project Structure

```
app/
  main.py              CLI entrypoint
  config.py            Config loader
  models.py            Pydantic data models
  rules.py             Rules engine
  scoring.py           Confidence scoring
  dedupe.py            Deduplication
  exporter.py          Excel workbook exporter
  logging_utils.py     Logging setup
  commands/
    collect.py         Collect command
    filter.py          Filter command
    rank.py            Rank command
    summarize.py       Summarize command
    export.py          Export command
    rules_cmd.py       Rules command
  sources/
    base.py            Abstract source base class
    manual_input.py    JSON file loader
    public_web.py      Public web stub
    pacer_stub.py      PACER interface stub
  enrich/
    company_enrichment.py   Company enrichment stub
    contact_enrichment.py   Contact enrichment stub
  utils/
    urls.py            URL normalization
    phones.py          Phone normalization
    states.py          State validation
config/
  rules.yaml           Lane/state/quality/scoring rules
data/
  input/               Raw lead input files
  output/              Processed output files
```

## OpenClaw Integration

OpenClaw invokes this pipeline via CLI. It can:

- Request a specific lane
- Set a lead count limit
- Set minimum quality
- Receive structured JSON on stdout
- Request a compact summary
- Request an Excel export

All structured output goes to **stdout**. Logging goes to **stderr**.
