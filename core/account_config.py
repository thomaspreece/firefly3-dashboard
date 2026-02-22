"""
Hardcoded account ID lists for each dashboard view type.

Run the helper script to discover your account IDs:
    python list_accounts.py

Then fill in the IDs below.
"""

# Firefly III account IDs (integers) included in the "Joint" view
JOINT_ACCOUNT_IDS = [387]  # Nationwide Joint Current Account

INDIVIDUAL_ACCOUNT_IDS = [1, 9, 12, 380, 382]  # Halifax Current, Halifax Credit Card, Nationwide Current, Vanguard Stocks & Shares, Barclays Current

ACCOUNT_GROUPS = {
    "joint": JOINT_ACCOUNT_IDS,
    "individual": INDIVIDUAL_ACCOUNT_IDS,
}
