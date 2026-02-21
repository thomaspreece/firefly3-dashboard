"""
Pure functions for calculating dashboard figures from Firefly III data.
"""
from decimal import Decimal


def _amount(transaction, key="amount"):
    try:
        return Decimal(str(transaction.get(key) or "0"))
    except Exception:
        return Decimal("0")


JOINT_GROUP_TITLE = "Joint"


def calculate_subscriptions(bills, view_type):
    """
    Return unpaid bills for the queried period filtered by view_type.

    A bill is "joint" if its object_group_title in Firefly III is "Joint".
    All other bills (ungrouped or in any other group) are "individual".
    """
    unpaid = []
    for b in bills:
        if b.get("paid_dates"):
            continue
        is_joint = b.get("object_group_title") == JOINT_GROUP_TITLE
        if view_type == "joint" and not is_joint:
            continue
        if view_type == "individual" and is_joint:
            continue
        unpaid.append(b)

    total = sum(Decimal(str(b.get("amount_max") or b.get("amount_min") or "0")) for b in unpaid)
    return {
        "bills": unpaid,
        "count": len(unpaid),
        "total": total,
    }


LARGE_TRANSACTION_THRESHOLD = Decimal("300")


def calculate_spent(transactions, account_ids):
    """
    Sum of withdrawal transactions where the source account is in account_ids.
    Also returns individual transactions over £300, sorted largest first.
    """
    account_ids_set = set(str(i) for i in account_ids)
    total = Decimal("0")
    large = []
    for t in transactions:
        if t.get("type") == "withdrawal" and str(t.get("source_id")) in account_ids_set:
            amt = _amount(t)
            total += amt
            if amt >= LARGE_TRANSACTION_THRESHOLD:
                large.append({"description": t.get("description", ""), "amount": amt})
    large.sort(key=lambda x: x["amount"], reverse=True)
    return {"total": total, "large_transactions": large}


def calculate_category_breakdown(transactions, account_ids):
    """
    Sum withdrawals by category for the given accounts.
    Returns a list of {category, total} dicts sorted largest first.
    Uncategorised transactions are grouped under 'Uncategorised'.
    """
    account_ids_set = set(str(i) for i in account_ids)
    totals = {}
    for t in transactions:
        if t.get("type") == "withdrawal" and str(t.get("source_id")) in account_ids_set:
            category = t.get("category_name") or "Uncategorised"
            totals[category] = totals.get(category, Decimal("0")) + _amount(t)
    return sorted(
        [{"category": k, "total": v} for k, v in totals.items()],
        key=lambda x: (x["category"] == "Uncategorised", -x["total"]),
    )


def calculate_in_out(transactions, account_ids):
    """
    Calculate income, expenses, and net for the given accounts.

    - income:   deposits where destination_id is in account_ids
    - expenses: withdrawals where source_id is in account_ids
    - net:      income - expenses
    """
    account_ids_set = set(str(i) for i in account_ids)
    income = Decimal("0")
    expenses = Decimal("0")

    for t in transactions:
        tx_type = t.get("type")
        if tx_type == "deposit" and str(t.get("destination_id")) in account_ids_set:
            income += _amount(t)
        elif tx_type == "withdrawal" and str(t.get("source_id")) in account_ids_set:
            expenses += _amount(t)

    return {
        "income": income,
        "expenses": expenses,
        "net": income - expenses,
    }
