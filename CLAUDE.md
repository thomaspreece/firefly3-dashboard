# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server
python manage.py runserver

# Discover account IDs from your Firefly III instance
python list_accounts.py

# Run tests
python manage.py test
```

## Environment

Requires a `.env` file in the project root:

```env
FIREFLY_BASE_URL=https://your-firefly-instance.example.com
FIREFLY_TOKEN=your_personal_access_token
DJANGO_SECRET_KEY=your_secret_key
FIREFLY_VANITY_URL=https://public-url.example.com  # optional, defaults to FIREFLY_BASE_URL
DEBUG=True
```

## Architecture

A single-app Django project with no database — all data is fetched live from the Firefly III REST API on each page load.

### Key files

- **`core/firefly_client.py`** — Thin `FireflyClient` wrapper around the Firefly III API. Handles Bearer auth and pagination via `_get_all_pages()`. All API interaction goes through here.
- **`core/account_config.py`** — Hardcoded `JOINT_ACCOUNT_IDS` and `INDIVIDUAL_ACCOUNT_IDS` lists. Edit this to configure which Firefly accounts appear in each dashboard view. Use `python list_accounts.py` to discover IDs.
- **`core/calculators.py`** — Pure functions (`calculate_subscriptions`, `calculate_spent`, `calculate_in_out`, `calculate_category_breakdown`) that process transactions into dashboard figures. No I/O — easy to test.
- **`core/views.py`** — All views. The `dashboard` view is the main entry point; the remaining views are POST-only JSON endpoints. AI features call the `claude` CLI via `subprocess`.
- **`core/templates/core/dashboard.html`** — Single-page template. All interactivity (category editing, AI analysis, rule running) is vanilla JS at the bottom of the file, communicating with POST endpoints via `fetch`.

### Views / URL structure

| URL | Handler | Purpose |
|---|---|---|
| `/joint/` | `dashboard(view_type="joint")` | Main dashboard for joint accounts |
| `/individual/` | `dashboard(view_type="individual")` | Main dashboard for individual accounts |
| `/update-category/` | `update_category` | Set category on a transaction |
| `/update-rule/` | `update_rule` | Set category + add trigger to existing rule |
| `/identify-transaction/` | `identify_transaction` | AI-powered transaction decoder (calls `claude` CLI) |
| `/analyse-spending/` | `analyse_spending` | AI spending analysis (calls `claude` CLI, caches to `analysis_cache/`) |
| `/run-rules/` | `run_rules` | Re-run all category rules over a date range |

### Bill classification

Bills are split into joint vs individual by their **object group** in Firefly III. A bill with `object_group_title == "Joint"` appears on the joint view; all others on individual.

### AI features

`identify_transaction` and `analyse_spending` shell out to the `claude` CLI (`subprocess.run(["claude", "-p", prompt])`). These require Claude Code to be installed. Analysis results are persisted as JSON in `analysis_cache/{view_type}_{YYYY-MM}.json` and loaded back on page load.

### Frontend

Bootstrap 5.3 and `marked.js` loaded from CDN. No build step. All JS is inline in `dashboard.html`.
