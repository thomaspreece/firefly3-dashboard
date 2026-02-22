"""
Thin wrapper around the Firefly III REST API.
"""
import requests
from django.conf import settings


class FireflyClient:
    def __init__(self):
        self.base_url = settings.FIREFLY_BASE_URL.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {settings.FIREFLY_TOKEN}",
            "Accept": "application/json",
        })

    def _get_all_pages(self, endpoint, params=None):
        """Fetch all pages from a paginated Firefly endpoint."""
        params = dict(params or {})
        params["limit"] = 100
        page = 1
        results = []

        while True:
            params["page"] = page
            response = self.session.get(f"{self.base_url}{endpoint}", params=params)
            response.raise_for_status()
            data = response.json()
            results.extend(data.get("data", []))
            meta = data.get("meta", {}).get("pagination", {})
            if page >= meta.get("total_pages", 1):
                break
            page += 1

        return results

    def get_transactions(self, start_date, end_date, account_ids=None):
        """
        Fetch all transactions between start_date and end_date.
        Optionally filter to transactions involving specific account IDs.
        start_date / end_date: date objects or YYYY-MM-DD strings.
        """
        params = {
            "start": str(start_date),
            "end": str(end_date),
            "type": "all",
        }
        raw = self._get_all_pages("/api/v1/transactions", params)

        transactions = []
        for item in raw:
            for split in item.get("attributes", {}).get("transactions", []):
                transactions.append(split)

        if account_ids is not None:
            account_ids_set = set(str(i) for i in account_ids)
            transactions = [
                t for t in transactions
                if str(t.get("source_id")) in account_ids_set
                or str(t.get("destination_id")) in account_ids_set
            ]

        return transactions

    def get_bills(self, start_date, end_date):
        """
        Fetch all bills and annotate each with whether it was paid in
        the given date range.
        start_date / end_date: date objects or YYYY-MM-DD strings.
        """
        params = {
            "start": str(start_date),
            "end": str(end_date),
        }
        raw = self._get_all_pages("/api/v1/bills", params)
        return [item.get("attributes", {}) | {"id": item.get("id")} for item in raw]

    def get_categories(self):
        """Fetch all categories."""
        raw = self._get_all_pages("/api/v1/categories")
        return sorted(
            [item.get("attributes", {}) | {"id": item.get("id")} for item in raw],
            key=lambda c: c.get("name", ""),
        )

    def update_transaction_category(self, journal_id, category_name):
        """Update the category of a transaction journal."""
        response = self.session.put(
            f"{self.base_url}/api/v1/transactions/{journal_id}",
            json={"transactions": [{"category_name": category_name}]},
        )
        response.raise_for_status()
        return response.json()

    def get_accounts(self):
        """Fetch all asset accounts."""
        raw = self._get_all_pages("/api/v1/accounts", {"type": "asset"})
        return [item.get("attributes", {}) | {"id": item.get("id")} for item in raw]
