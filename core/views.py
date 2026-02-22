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


def dashboard(request, view_type="joint"):
    month_str = request.GET.get("month", "")
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
                "source_name": t.get("source_name", ""),
            }
            for t in transactions
            if t.get("type") == "withdrawal" and str(t.get("source_id")) in account_ids_set
        ],
        key=lambda x: x["date"],
        reverse=True,
    )

    categories = client.get_categories()
    rules = client.get_rules()
    category_rules = {}
    for rule in rules:
        for action in rule.get("actions", []):
            if action.get("type") == "set_category" and action.get("value"):
                cat = action["value"]
                category_rules.setdefault(cat, [])
                for trigger in rule.get("triggers", []):
                    category_rules[cat].append({
                        "type": trigger.get("type", ""),
                        "value": trigger.get("value", ""),
                    })
    all_accounts = client.get_accounts()
    accounts = [
        a for a in all_accounts
        if str(a.get("id")) in account_ids_set and float(a.get("current_balance", 0)) != 0
    ]
    total_wealth = sum(float(a.get("current_balance", 0)) for a in accounts)

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
        "total_wealth": total_wealth,
        "accounts": accounts,
        "category_rules_json": category_rules,
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


@require_POST
def update_rule(request):
    body = json.loads(request.body)
    journal_id = body.get("journal_id")
    category_name = body.get("category_name")
    trigger_value = body.get("trigger_value", "").strip()
    trigger_type = body.get("trigger_type", "description_is")
    valid_trigger_types = {"description_starts", "description_contains", "description_is"}
    if trigger_type not in valid_trigger_types:
        trigger_type = "description_starts"
    if not journal_id or not category_name or not trigger_value:
        return JsonResponse({"error": "Missing required fields"}, status=400)
    try:
        client = FireflyClient()
        client.update_transaction_category(journal_id, category_name)

        rules = client.get_rules()
        matching_rule = next(
            (r for r in rules
             if any(a.get("type") == "set_category" and a.get("value") == category_name
                    for a in r.get("actions", []))),
            None,
        )
        if not matching_rule:
            return JsonResponse({"error": f"No rule found for category '{category_name}'"}, status=404)

        new_trigger = {
            "type": trigger_type,
            "value": trigger_value,
            "prohibited": False,
            "active": True,
            "stop_processing": False,
        }
        rule_data = {
            "title": matching_rule["title"],
            "description": matching_rule.get("description", ""),
            "rule_group_id": matching_rule["rule_group_id"],
            "trigger": matching_rule.get("trigger", "store-journal"),
            "active": matching_rule.get("active", True),
            "strict": matching_rule.get("strict", False),
            "stop_processing": matching_rule.get("stop_processing", False),
            "triggers": matching_rule.get("triggers", []) + [new_trigger],
            "actions": matching_rule.get("actions", []),
        }
        client.update_rule(matching_rule["id"], rule_data)
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
