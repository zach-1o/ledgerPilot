import csv
import io
import json
import re
from typing import List, Dict, Tuple, Any, Optional
from backend.schemas import Invoice, Payment, Settlement, BankTransaction

def clean_amount(val: Any) -> float:
    if val is None or val == "":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace("₹", "").replace(",", "").replace("$", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0

def find_col(row: Dict[str, Any], candidates: List[str]) -> Optional[str]:
    keys = list(row.keys())
    for cand in candidates:
        for k in keys:
            if cand.lower() in k.lower().strip():
                return k
    return None

class UniversalParser:
    """Parses arbitrary merchant CSV or JSON exports into canonical Pydantic models."""
    
    @staticmethod
    def parse_invoices_csv(file_content: str) -> List[Invoice]:
        reader = csv.DictReader(io.StringIO(file_content))
        invoices = []
        for idx, row in enumerate(reader, 1):
            inv_col = find_col(row, ["invoice_id", "inv_id", "invoice", "number", "id"]) or list(row.keys())[0]
            ord_col = find_col(row, ["order_id", "ord_id", "order", "ref"]) or inv_col
            cust_col = find_col(row, ["customer_id", "cust_id", "customer", "client"]) or "CUST-001"
            date_col = find_col(row, ["date", "created", "time"]) or list(row.keys())[1]
            amount_col = find_col(row, ["gross_amount", "amount", "net_amount", "total"]) or list(row.keys())[-1]
            
            gross = clean_amount(row.get(amount_col, 0.0))
            tax = round(gross * 0.18, 2)
            
            invoices.append(Invoice(
                invoice_id=str(row.get(inv_col, f"INV-{idx:04d}")).strip(),
                order_id=str(row.get(ord_col, f"ORD-{idx:04d}")).strip(),
                customer_id=str(row.get(cust_col, "CUST-DEFAULT")).strip(),
                invoice_date=str(row.get(date_col, "2026-08-01 10:00:00")).strip(),
                gross_amount=gross,
                tax_amount=tax,
                net_amount=gross
            ))
        return invoices

    @staticmethod
    def parse_payments_csv(file_content: str) -> List[Payment]:
        reader = csv.DictReader(io.StringIO(file_content))
        payments = []
        for idx, row in enumerate(reader, 1):
            pay_col = find_col(row, ["payment_id", "pay_id", "payment", "id"]) or list(row.keys())[0]
            ord_col = find_col(row, ["order_id", "ord_id", "order"]) or pay_col
            date_col = find_col(row, ["date", "created", "captured_at"]) or list(row.keys())[1]
            gross_col = find_col(row, ["gross_amount", "amount", "total"]) or list(row.keys())[-1]
            fee_col = find_col(row, ["fee", "pg_fee", "commission"])
            
            gross = clean_amount(row.get(gross_col, 0.0))
            fee = clean_amount(row.get(fee_col, round(gross * 0.02, 2))) if fee_col else round(gross * 0.02, 2)
            tax_on_fee = round(fee * 0.18, 2)
            net = round(gross - (fee + tax_on_fee), 2)
            
            payments.append(Payment(
                payment_id=str(row.get(pay_col, f"pay_{idx:04d}")).strip(),
                order_id=str(row.get(ord_col, f"ORD-{idx:04d}")).strip(),
                gateway_txn_id=f"gtw_{idx}",
                payment_date=str(row.get(date_col, "2026-08-01 10:05:00")).strip(),
                gross_amount=gross,
                fee=fee,
                tax_on_fee=tax_on_fee,
                net_amount=net
            ))
        return payments

    @staticmethod
    def parse_settlements_csv(file_content: str) -> List[Settlement]:
        reader = csv.DictReader(io.StringIO(file_content))
        settlements = []
        for idx, row in enumerate(reader, 1):
            setl_col = find_col(row, ["settlement_id", "setl_id", "settlement", "id"]) or list(row.keys())[0]
            pay_col = find_col(row, ["payment_id", "pay_id", "payment"]) or setl_col
            utr_col = find_col(row, ["bank_reference", "utr", "reference", "utr_number"]) or list(row.keys())[-1]
            amount_col = find_col(row, ["net_amount", "payout", "amount", "settled_amount"]) or list(row.keys())[-2]
            
            net = clean_amount(row.get(amount_col, 0.0))
            gross = round(net / 0.9764, 2)  # Estimate gross if only net provided
            fee = round(gross * 0.02, 2)
            tax = round(fee * 0.18, 2)
            
            settlements.append(Settlement(
                settlement_id=str(row.get(setl_col, f"setl_{idx:04d}")).strip(),
                payment_id=str(row.get(pay_col, f"pay_{idx:04d}")).strip(),
                settlement_date=str(row.get(find_col(row, ["date", "time"]) or "settlement_date", "2026-08-01 14:00:00")).strip(),
                gross_amount=gross,
                fee=fee,
                tax=tax,
                adjustment=clean_amount(row.get(find_col(row, ["adjustment", "reserve"]), 0.0)),
                net_amount=net,
                bank_reference=str(row.get(utr_col, f"UTR{idx:08d}")).strip()
            ))
        return settlements

    @staticmethod
    def parse_bank_csv(file_content: str) -> List[BankTransaction]:
        reader = csv.DictReader(io.StringIO(file_content))
        bank_txns = []
        for idx, row in enumerate(reader, 1):
            txn_col = find_col(row, ["bank_txn_id", "txn_id", "transaction_id", "id"]) or f"BANK-{idx:04d}"
            date_col = find_col(row, ["date", "value_date", "time"]) or list(row.keys())[0]
            utr_col = find_col(row, ["reference", "utr", "description", "remarks"]) or list(row.keys())[1]
            credit_col = find_col(row, ["credit", "deposit", "amount"]) or list(row.keys())[-1]
            
            ref_val = str(row.get(utr_col, "")).strip()
            # Extract UTR pattern if embedded inside description
            utr_match = re.search(r'(UTR[A-Za-z0-9]+|[0-9]{9,12})', ref_val)
            extracted_utr = utr_match.group(1) if utr_match else ref_val
            
            bank_txns.append(BankTransaction(
                bank_txn_id=str(row.get(txn_col, f"BANK-{idx:04d}")).strip(),
                transaction_date=str(row.get(date_col, "2026-08-01 15:00:00")).strip(),
                reference=extracted_utr,
                credit=clean_amount(row.get(credit_col, 0.0)),
                debit=0.0,
                balance=500000.0,
                description=ref_val
            ))
        return bank_txns
