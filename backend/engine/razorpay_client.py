import requests
from typing import List, Tuple, Dict
from backend.schemas import Payment, Settlement

class RazorpayClient:
    """Connects to Razorpay Test Mode API to fetch live merchant sandbox payments and settlements."""
    
    BASE_URL = "https://api.razorpay.com/v1"

    def __init__(self, key_id: str, key_secret: str):
        self.key_id = key_id
        self.key_secret = key_secret
        self.auth = (key_id, key_secret)

    def fetch_payments(self, count: int = 50) -> List[Payment]:
        url = f"{self.BASE_URL}/payments?count={count}"
        resp = requests.get(url, auth=self.auth, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("items", [])

        payments = []
        for p in data:
            gross = float(p.get("amount", 0)) / 100.0  # Razorpay returns amounts in paise
            fee = float(p.get("fee", round(gross * 0.02 * 100))) / 100.0
            tax = float(p.get("tax", round(fee * 0.18 * 100))) / 100.0
            net = gross - (fee + tax)

            payments.append(Payment(
                payment_id=p.get("id"),
                order_id=p.get("order_id") or f"ORD-{p.get('id')[-6:]}",
                gateway_txn_id=p.get("id"),
                payment_date=str(p.get("created_at")),
                gross_amount=gross,
                fee=fee,
                tax_on_fee=tax,
                net_amount=net,
                currency=p.get("currency", "INR"),
                status=p.get("status", "CAPTURED").upper()
            ))
        return payments

    def fetch_settlements(self, count: int = 50) -> List[Settlement]:
        url = f"{self.BASE_URL}/settlements?count={count}"
        resp = requests.get(url, auth=self.auth, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("items", [])

        settlements = []
        for s in data:
            net = float(s.get("amount", 0)) / 100.0
            gross = round(net / 0.9764, 2)
            fee = round(gross * 0.02, 2)
            tax = round(fee * 0.18, 2)

            settlements.append(Settlement(
                settlement_id=s.get("id"),
                payment_id=f"pay_{s.get('id')[-6:]}",
                settlement_date=str(s.get("created_at")),
                gross_amount=gross,
                fee=fee,
                tax=tax,
                adjustment=0.0,
                net_amount=net,
                bank_reference=s.get("utr") or f"UTR{s.get('id')[-8:]}",
                status=s.get("status", "SETTLED").upper()
            ))
        return settlements
