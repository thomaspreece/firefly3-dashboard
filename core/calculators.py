"""
Pure functions for calculating dashboard figures from Firefly III data.
"""
from datetime import date
from decimal import Decimal


def _amount(transaction, key="amount"):
    try:
        return Decimal(str(transaction.get(key) or "0"))
    except Exception:
        return Decimal("0")


JOINT_GROUP_TITLE = "Joint"


def _filter_date_entries(entries, start_date, end_date):
    """Return only entries whose date falls within [start_date, end_date].

    Entries can be dicts with a 'date' key (paid_dates) or plain date strings (pay_dates).
    """
    filtered = []
    for entry in entries:
        if isinstance(entry, dict):
            d = entry.get("date", "")[:10]
        else:
            d = str(entry)[:10]
        try:
            parsed = date.fromisoformat(d)
        except (ValueError, TypeError):
            continue
        if start_date <= parsed <= end_date:
            filtered.append(entry)
    return filtered


def calculate_subscriptions(bills, view_type, start_date=None, end_date=None, transactions=None):
    """
    Return unpaid bills for the queried period filtered by view_type.

    A bill is "joint" if its object_group_title in Firefly III is "Joint".
    All other bills (ungrouped or in any other group) are "individual".
    """
    tx_by_journal = {}
    tx_by_bill_date = {}
    if transactions:
        for t in transactions:
            jid = str(t.get("transaction_journal_id", ""))
            if jid:
                tx_by_journal[jid] = t
            bill_id = t.get("bill_id")
            if bill_id:
                tx_date = (t.get("date") or "")[:10]
                tx_by_bill_date.setdefault((str(bill_id), tx_date), []).append(t)

    unpaid = []
    paid = []
    for b in bills:
        is_joint = b.get("object_group_title") == JOINT_GROUP_TITLE
        if view_type == "joint" and not is_joint:
            continue
        if view_type == "individual" and is_joint:
            continue
        paid_dates = b.get("paid_dates") or []
        pay_dates = b.get("pay_dates") or []
        if start_date and end_date:
            paid_dates = _filter_date_entries(paid_dates, start_date, end_date)
            pay_dates = _filter_date_entries(pay_dates, start_date, end_date)
        if paid_dates:
            for pd in paid_dates:
                jid = str(pd.get("transaction_journal_id", ""))
                pd_date = pd.get("date", "")[:10]
                tx = tx_by_journal.get(jid)
                if not tx:
                    matches = tx_by_bill_date.get((str(b.get("id", "")), pd_date), [])
                    tx = matches[0] if matches else None
                if tx:
                    paid_amount = _amount(tx)
                else:
                    paid_amount = Decimal(str(b.get("amount_max") or b.get("amount_min") or "0"))
                paid.append(b | {"paid_date": pd.get("date", "")[:10], "paid_amount": paid_amount})
        elif pay_dates:
            for pd in pay_dates:
                expected = pd[:10] if isinstance(pd, str) else str(pd)[:10]
                unpaid.append(b | {"expected_date": expected})

    total = sum(Decimal(str(b.get("amount_max") or b.get("amount_min") or "0")) for b in unpaid)
    paid_total = sum(b["paid_amount"] for b in paid)
    return {
        "bills": unpaid,
        "count": len(unpaid),
        "total": total,
        "paid_bills": paid,
        "paid_count": len(paid),
        "paid_total": paid_total,
    }


LARGE_TRANSACTION_THRESHOLD = Decimal("300")


def calculate_spent(transactions, account_ids):
    """
    Sum of withdrawal transactions where the source account is in account_ids.
    Also returns individual transactions over £300, sorted largest first.
    """
    account_ids_set = set(str(i) for i in account_ids)
    total = Decimal("0")
    total_excl_bills = Decimal("0")
    large = []
    for t in transactions:
        if t.get("type") == "withdrawal" and str(t.get("source_id")) in account_ids_set:
            amt = _amount(t)
            total += amt
            if not t.get("bill_id"):
                total_excl_bills += amt
            if amt >= LARGE_TRANSACTION_THRESHOLD:
                large.append({"description": t.get("description", ""), "amount": amt, "journal_id": t.get("transaction_journal_id")})
    large.sort(key=lambda x: x["amount"], reverse=True)
    return {"total": total, "total_excl_bills": total_excl_bills, "large_transactions": large}


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
    large_income = []

    for t in transactions:
        tx_type = t.get("type")
        if tx_type == "deposit" and str(t.get("destination_id")) in account_ids_set:
            amt = _amount(t)
            income += amt
            if amt >= LARGE_TRANSACTION_THRESHOLD:
                large_income.append({"description": t.get("description", ""), "amount": amt, "journal_id": t.get("transaction_journal_id")})
        elif tx_type == "withdrawal" and str(t.get("source_id")) in account_ids_set:
            expenses += _amount(t)

    large_income.sort(key=lambda x: x["amount"], reverse=True)
    return {
        "income": income,
        "expenses": expenses,
        "net": income - expenses,
        "large_income": large_income,
    }
