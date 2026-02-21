# Firefly III Dashboard - Implementation Plan

## Overview

A Django web application that connects to a Firefly III instance and presents a financial dashboard with key monthly figures, filterable by month and account group (joint vs individual).

---

## Tech Stack

- **Python 3.12+**
- **Django 5.x** — web framework + templating
- **requests** — HTTP client for Firefly III API calls
- **Bootstrap 5** — CSS framework (CDN, no build step needed)
- **python-dotenv** — environment variable management

---

## Project Structure

```
firefly3-dashboard/
├── manage.py
├── .env                          # API token, secret key (gitignored)
├── requirements.txt
├── dashboard/                    # Django project config
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── core/                         # Main Django app
    ├── __init__.py
    ├── urls.py
    ├── views.py
    ├── firefly_client.py         # Firefly III API wrapper
    ├── account_config.py         # Hardcoded joint/individual account lists
    ├── calculators.py            # Logic for each dashboard figure
    └── templates/
        └── core/
            ├── base.html
            └── dashboard.html
```

---

## Configuration

### `.env`
```
FIREFLY_BASE_URL=https://firefly3.thomaspreece.com
FIREFLY_TOKEN=<personal_access_token>
DJANGO_SECRET_KEY=<secret>
DEBUG=True
```

### `account_config.py`
Hardcoded account name/ID lists. This is the source of truth for which Firefly accounts belong to each group.

```python
# Account IDs from Firefly III (integers)
JOINT_ACCOUNT_IDS = [1, 2, 3]       # e.g. joint current account, joint savings
INDIVIDUAL_ACCOUNT_IDS = [4, 5]     # e.g. personal current account
```

---

## Firefly III API Integration

### `firefly_client.py`
A thin wrapper around the Firefly III REST API.

Key methods:
- `get_transactions(start_date, end_date, account_ids)` — fetches all transactions in a date range for given accounts
- `get_bills(start_date, end_date)` — fetches bills due in a date range

Authentication: `Authorization: Bearer <token>` header on all requests.

Pagination: Firefly III paginates at 50 results by default. The client must loop through all pages.

---

## Dashboard Figures

### 1. Subscriptions to Pay
- Source: Firefly III `/api/v1/bills` endpoint
- Filter: bills with `paid_dates` NOT containing a date in the selected month, and `next_expected_match` falls within the selected month
- Display: count + total amount of unpaid bills

### 2. Spent
- Source: transactions of type `withdrawal` in the selected month
- Filter: only transactions whose `source_account_id` is in the selected account group (joint or individual)
- Display: sum of amounts

### 3. In + Out
- Source: all transactions in the selected month for the selected account group
- Calculation:
  - **In**: sum of `deposit` transactions where `destination_account_id` is in the group
  - **Out**: sum of `withdrawal` transactions where `source_account_id` is in the group
  - **Net**: In − Out
- Display: In, Out, and Net as three sub-values

### `calculators.py`
Contains pure functions:
- `calculate_subscriptions(bills, month_start, month_end)` → `{count, total}`
- `calculate_spent(transactions)` → `Decimal`
- `calculate_in_out(transactions)` → `{income, expenses, net}`

---

## Django Views

### `views.py` — single view: `dashboard`

1. Parse `month` from GET params (default: current month). Format: `YYYY-MM`.
2. Parse `view_type` from GET params (default: `joint`). Values: `joint` or `individual`.
3. Derive `month_start` and `month_end` dates from the `month` param.
4. Select account IDs from `account_config` based on `view_type`.
5. Call `firefly_client` to fetch transactions and bills.
6. Pass data through `calculators` to produce the three figures.
7. Render `dashboard.html` with context.

---

## Templates

### `base.html`
- Bootstrap 5 via CDN
- Navbar with app title
- `{% block content %}` slot

### `dashboard.html`
Layout:
```
┌─────────────────────────────────────────────────┐
│  [← Prev Month]  February 2026  [Next Month →]  │
│  View: [Joint]  [Individual]                     │
├────────────────┬────────────────┬────────────────┤
│ Subscriptions  │     Spent      │    In + Out     │
│  to Pay        │                │                 │
│  3 bills       │   £1,234.56    │ In:  £2,000     │
│  £87.00 total  │                │ Out: £1,234     │
│                │                │ Net: +£766      │
└────────────────┴────────────────┴────────────────┘
```

- Month navigation: `<a>` links that update the `month` query param
- Joint/Individual toggle: links or a form that updates the `view_type` query param
- Three Bootstrap cards for the three figures

---

## URL Routing

```
/              → dashboard view (current month, joint)
/?month=2026-01&view_type=individual  → dashboard with params
```

---

## Implementation Order

1. **Project scaffolding** — `django-admin startproject`, `startapp`, install deps, `.env` setup
2. **`firefly_client.py`** — implement API calls, test against live Firefly instance
3. **`account_config.py`** — populate with real account IDs from Firefly
4. **`calculators.py`** — implement the three calculation functions with unit tests
5. **`views.py`** — wire together client + calculators, handle month/type params
6. **`templates/`** — build base + dashboard HTML with Bootstrap
7. **URL routing** — connect view to URLs
8. **Manual testing** — verify figures match what Firefly shows in its UI
9. **Deployment** — gunicorn + nginx or simple `python manage.py runserver` behind a reverse proxy

---

## Requirements File

```
Django>=5.0
requests>=2.31
python-dotenv>=1.0
```

---

## Out of Scope (for now)

- Database models / ORM (no local data persistence needed)
- User authentication (single-user tool, API token is sufficient)
- Caching (fetch fresh on each page load)
- Charts / graphs
- Mobile-specific layout
