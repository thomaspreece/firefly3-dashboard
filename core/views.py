from datetime import date
from calendar import monthrange

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .firefly_client import FireflyClient
from .account_config import ACCOUNT_GROUPS
from .calculators import calculate_subscriptions, calculate_spent, calculate_in_out, calculate_category_breakdown


def _parse_month(month_str):
    """Parse YYYY-MM string into (year, month) ints, defaulting to current month."""
    try:
        year, month = month_str.split("-")
        return int(year), int(month)
    except Exception:
        today = date.today()
        return today.year, today.month


def _month_bounds(year, month):
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _adjacent_month(year, month, delta):
    """Return (year, month) shifted by delta months."""
    month += delta
    if month > 12:
        year += 1
        month = 1
    elif month < 1:
        year -= 1
        month = 12
    return year, month


MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def dashboard(request):
    month_str = request.GET.get("month", "")
    view_type = request.GET.get("view_type", "joint")
    if view_type not in ACCOUNT_GROUPS:
        view_type = "joint"

    year, month = _parse_month(month_str)
    month_start, month_end = _month_bounds(year, month)

    account_ids = ACCOUNT_GROUPS[view_type]

    client = FireflyClient()
    transactions = client.get_transactions(month_start, month_end, account_ids)
    bills = client.get_bills(month_start, month_end)

    subscriptions = calculate_subscriptions(bills, view_type)
    spent = calculate_spent(transactions, account_ids)
    in_out = calculate_in_out(transactions, account_ids)
    category_breakdown = calculate_category_breakdown(transactions, account_ids)

    account_ids_set = set(str(i) for i in account_ids)
    withdrawal_transactions = sorted(
        [
            {
                "journal_id": t.get("transaction_journal_id"),
                "date": t["date"][:10],
                "description": t.get("description", ""),
                "category": t.get("category_name") or "Uncategorised",
                "amount": t.get("amount", "0"),
            }
            for t in transactions
            if t.get("type") == "withdrawal" and str(t.get("source_id")) in account_ids_set
        ],
        key=lambda x: x["date"],
        reverse=True,
    )

    categories = client.get_categories()

    dates = [t["date"] for t in withdrawal_transactions]
    latest_transaction_date = max(dates) if dates else None

    prev_year, prev_month = _adjacent_month(year, month, -1)
    next_year, next_month = _adjacent_month(year, month, 1)

    context = {
        "month_label": f"{MONTH_NAMES[month]} {year}",
        "month_str": f"{year}-{month:02d}",
        "prev_month": f"{prev_year}-{prev_month:02d}",
        "next_month": f"{next_year}-{next_month:02d}",
        "view_type": view_type,
        "subscriptions": subscriptions,
        "spent": spent,
        "in_out": in_out,
        "account_ids_configured": bool(account_ids),
        "category_breakdown": category_breakdown,
        "latest_transaction_date": latest_transaction_date,
        "transaction_count": len(transactions),
        "withdrawal_transactions": withdrawal_transactions,
        "categories": categories,
    }
    return render(request, "core/dashboard.html", context)


import json

@require_POST
def update_category(request):
    body = json.loads(request.body)
    journal_id = body.get("journal_id")
    category_name = body.get("category_name")
    if not journal_id or not category_name:
        return JsonResponse({"error": "Missing journal_id or category_name"}, status=400)
    try:
        FireflyClient().update_transaction_category(journal_id, category_name)
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
