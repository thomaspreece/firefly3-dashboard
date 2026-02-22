# Firefly III Dashboard

A Django dashboard for visualising monthly finances from a [Firefly III](https://www.firefly-iii.org/) instance.

## Features

- **Joint and individual views** at `/joint/` and `/individual/`
- **Month navigation** — browse any past or future month
- **In + Out** — net, income, and expenses summary
- **Subscriptions to Pay** — unpaid bills for the month, split by joint/individual via Firefly object groups
- **Spent** — total withdrawals and spend excluding subscriptions, with large transactions (>£300) listed
- **Income** — total deposits with large income transactions listed
- **Total Wealth** — sum of all accounts in the current view group, with per-account breakdown
- **Spending by Category** — table of withdrawal totals grouped by category
- **Transaction table** — filterable by category, click any row to reassign its category in Firefly III

## Requirements

- Python 3.10+
- A running Firefly III instance with a Personal Access Token

## Setup

1. **Clone the repo and install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Create a `.env` file** in the project root:

   ```env
   FIREFLY_BASE_URL=https://your-firefly-instance.example.com
   FIREFLY_TOKEN=your_personal_access_token
   DJANGO_SECRET_KEY=your_secret_key
   DEBUG=True
   ```

   Generate a secret key with:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

3. **Discover your account IDs:**

   ```bash
   python list_accounts.py
   ```

4. **Configure account groups** in `core/account_config.py`:

   ```python
   JOINT_ACCOUNT_IDS = [387]          # accounts included in the /joint/ view
   INDIVIDUAL_ACCOUNT_IDS = [1, 9, 12, 380, 382]  # accounts for /individual/
   ```

5. **Run the server:**

   ```bash
   python manage.py runserver
   ```

   Then open [http://localhost:8000](http://localhost:8000) — it redirects to `/joint/`.

## Bill Classification

Bills are classified as joint or individual based on their **object group** in Firefly III. Any bill in an object group named `Joint` is shown on the joint view; all others appear on the individual view.

## Project Structure

```
core/
  account_config.py   # hardcoded account ID lists
  firefly_client.py   # Firefly III API wrapper
  calculators.py      # calculation logic
  views.py            # Django views
  urls.py             # URL routing
  templates/core/
    base.html
    dashboard.html
dashboard/
  settings.py
  urls.py
list_accounts.py      # helper script to print account IDs
```
