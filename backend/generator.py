import json
import random
import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from backend.schemas import (
    Invoice, Payment, Settlement, BankTransaction, GroundTruth, MatchStatus, RootCause
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

def generate_synthetic_dataset(num_chains: int = 200) -> Tuple[List[Invoice], List[Payment], List[Settlement], List[BankTransaction], List[GroundTruth]]:
    random.seed(42)  # Deterministic seed for reproducible evaluation
    
    invoices: List[Invoice] = []
    payments: List[Payment] = []
    settlements: List[Settlement] = []
    bank_txns: List[BankTransaction] = []
    ground_truths: List[GroundTruth] = []
    
    base_date = datetime(2026, 8, 1, 10, 0, 0)
    
    for i in range(1, num_chains + 1):
        chain_id = f"CHAIN-{i:04d}"
        order_id = f"ORD-{1000 + i}"
        customer_id = f"CUST-{random.randint(100, 999)}"
        invoice_id = f"INV-{2000 + i}"
        payment_id = f"pay_{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')}{i:04d}"
        settlement_id = f"setl_{3000 + i}"
        utr = f"UTR{20260800 + i}X99"
        
        # Base amounts
        # Special case: Threshold Anomaly (₹9,999)
        if i > num_chains - 4:
            gross_amount = 9999.0
            scenario = "THRESHOLD_ANOMALY"
        elif i <= 140:
            gross_amount = float(random.choice([1500, 2500, 4999, 12500, 24000, 45000]))
            scenario = "CLEAN_MATCH"
        elif i <= 170:
            gross_amount = float(random.choice([2000, 5000, 10000, 15000]))
            scenario = "GATEWAY_FEE_GST"
        elif i <= 185:
            gross_amount = float(random.choice([3500, 8000, 18000]))
            scenario = "DATE_DRIFT"
        elif i <= 190:
            gross_amount = float(random.choice([25000, 50000]))
            scenario = "SETTLEMENT_ADJUSTMENT"
        elif i <= 194:
            gross_amount = float(random.choice([1200, 3400]))
            scenario = "DUPLICATE_PAYMENT"
        elif i <= 196:
            gross_amount = float(random.choice([6000, 15000]))
            scenario = "MISSING_SETTLEMENT"
        else:
            gross_amount = 9999.0
            scenario = "THRESHOLD_ANOMALY"
            
        tax_amount = round(gross_amount * 0.18, 2)
        net_invoice = gross_amount
        
        # Standard fee calculation: 2% PG Fee + 18% GST on Fee
        pg_fee = round(gross_amount * 0.02, 2)
        gst_on_fee = round(pg_fee * 0.18, 2)
        total_deduction = pg_fee + gst_on_fee
        net_payout = round(gross_amount - total_deduction, 2)
        
        txn_date = base_date + timedelta(hours=i * 2)
        
        # Build Invoice
        inv = Invoice(
            invoice_id=invoice_id,
            order_id=order_id,
            customer_id=customer_id,
            invoice_date=txn_date.strftime("%Y-%m-%d %H:%M:%S"),
            gross_amount=gross_amount,
            tax_amount=tax_amount,
            net_amount=net_invoice,
        )
        invoices.append(inv)
        
        # Scenario Logic
        if scenario == "CLEAN_MATCH":
            pay = Payment(
                payment_id=payment_id, order_id=order_id, gateway_txn_id=f"gtw_{i}",
                payment_date=txn_date.strftime("%Y-%m-%d %H:%M:%S"),
                gross_amount=gross_amount, fee=0.0, tax_on_fee=0.0, net_amount=gross_amount
            )
            setl = Settlement(
                settlement_id=settlement_id, payment_id=payment_id,
                settlement_date=(txn_date + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
                gross_amount=gross_amount, fee=0.0, tax=0.0, adjustment=0.0,
                net_amount=gross_amount, bank_reference=utr
            )
            bank = BankTransaction(
                bank_txn_id=f"BANK-{i:04d}",
                transaction_date=(txn_date + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
                reference=utr, credit=gross_amount, balance=500000.0 + (i * gross_amount),
                description=f"Razorpay Payout {utr}"
            )
            gt = GroundTruth(
                chain_id=chain_id, expected_status=MatchStatus.RECONCILED,
                expected_root_cause=RootCause.CLEAN_MATCH, expected_discrepancy=0.0,
                notes="Perfect 4-way match."
            )
            payments.append(pay)
            settlements.append(setl)
            bank_txns.append(bank)
            ground_truths.append(gt)

        elif scenario == "GATEWAY_FEE_GST":
            pay = Payment(
                payment_id=payment_id, order_id=order_id, gateway_txn_id=f"gtw_{i}",
                payment_date=txn_date.strftime("%Y-%m-%d %H:%M:%S"),
                gross_amount=gross_amount, fee=pg_fee, tax_on_fee=gst_on_fee, net_amount=net_payout
            )
            setl = Settlement(
                settlement_id=settlement_id, payment_id=payment_id,
                settlement_date=(txn_date + timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
                gross_amount=gross_amount, fee=pg_fee, tax=gst_on_fee, adjustment=0.0,
                net_amount=net_payout, bank_reference=utr
            )
            bank = BankTransaction(
                bank_txn_id=f"BANK-{i:04d}",
                transaction_date=(txn_date + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"),
                reference=utr, credit=net_payout, balance=500000.0 + (i * net_payout),
                description=f"Razorpay Payout {utr}"
            )
            gt = GroundTruth(
                chain_id=chain_id, expected_status=MatchStatus.RECONCILED,
                expected_root_cause=RootCause.GATEWAY_FEE_GST, expected_discrepancy=total_deduction,
                notes=f"Reconciled after applying 2% PG Fee ({pg_fee}) + 18% GST ({gst_on_fee})."
            )
            payments.append(pay)
            settlements.append(setl)
            bank_txns.append(bank)
            ground_truths.append(gt)

        elif scenario == "DATE_DRIFT":
            # Midnight crossing: payment at 23:55, settlement next day at 08:30
            late_date = txn_date.replace(hour=23, minute=55)
            next_day = late_date + timedelta(hours=9)
            pay = Payment(
                payment_id=payment_id, order_id=order_id, gateway_txn_id=f"gtw_{i}",
                payment_date=late_date.strftime("%Y-%m-%d %H:%M:%S"),
                gross_amount=gross_amount, fee=pg_fee, tax_on_fee=gst_on_fee, net_amount=net_payout
            )
            setl = Settlement(
                settlement_id=settlement_id, payment_id=payment_id,
                settlement_date=next_day.strftime("%Y-%m-%d %H:%M:%S"),
                gross_amount=gross_amount, fee=pg_fee, tax=gst_on_fee, adjustment=0.0,
                net_amount=net_payout, bank_reference=utr
            )
            bank = BankTransaction(
                bank_txn_id=f"BANK-{i:04d}",
                transaction_date=(next_day + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                reference=utr, credit=net_payout, balance=500000.0,
                description=f"Razorpay Payout {utr}"
            )
            gt = GroundTruth(
                chain_id=chain_id, expected_status=MatchStatus.PROBABLE_MATCH,
                expected_root_cause=RootCause.DATE_DRIFT, expected_discrepancy=0.0,
                notes="Probable match with 1-day date window drift."
            )
            payments.append(pay)
            settlements.append(setl)
            bank_txns.append(bank)
            ground_truths.append(gt)

        elif scenario == "SETTLEMENT_ADJUSTMENT":
            adj = 500.0
            actual_payout = net_payout - adj
            pay = Payment(
                payment_id=payment_id, order_id=order_id, gateway_txn_id=f"gtw_{i}",
                payment_date=txn_date.strftime("%Y-%m-%d %H:%M:%S"),
                gross_amount=gross_amount, fee=pg_fee, tax_on_fee=gst_on_fee, net_amount=net_payout
            )
            setl = Settlement(
                settlement_id=settlement_id, payment_id=payment_id,
                settlement_date=(txn_date + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
                gross_amount=gross_amount, fee=pg_fee, tax=gst_on_fee, adjustment=adj,
                net_amount=actual_payout, bank_reference=utr
            )
            bank = BankTransaction(
                bank_txn_id=f"BANK-{i:04d}",
                transaction_date=(txn_date + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
                reference=utr, credit=actual_payout, balance=500000.0,
                description=f"Razorpay Payout {utr}"
            )
            gt = GroundTruth(
                chain_id=chain_id, expected_status=MatchStatus.EXCEPTION,
                expected_root_cause=RootCause.SETTLEMENT_ADJUSTMENT, expected_discrepancy=adj,
                notes=f"Settlement short by ₹{adj} due to gateway reserve adjustment."
            )
            payments.append(pay)
            settlements.append(setl)
            bank_txns.append(bank)
            ground_truths.append(gt)

        elif scenario == "DUPLICATE_PAYMENT":
            pay1 = Payment(
                payment_id=payment_id, order_id=order_id, gateway_txn_id=f"gtw_{i}_1",
                payment_date=txn_date.strftime("%Y-%m-%d %H:%M:%S"),
                gross_amount=gross_amount, fee=0.0, tax_on_fee=0.0, net_amount=gross_amount
            )
            pay2 = Payment(
                payment_id=f"{payment_id}_DUP", order_id=order_id, gateway_txn_id=f"gtw_{i}_2",
                payment_date=(txn_date + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S"),
                gross_amount=gross_amount, fee=0.0, tax_on_fee=0.0, net_amount=gross_amount
            )
            setl = Settlement(
                settlement_id=settlement_id, payment_id=payment_id,
                settlement_date=(txn_date + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
                gross_amount=gross_amount, fee=0.0, tax=0.0, adjustment=0.0,
                net_amount=gross_amount, bank_reference=utr
            )
            bank = BankTransaction(
                bank_txn_id=f"BANK-{i:04d}",
                transaction_date=(txn_date + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
                reference=utr, credit=gross_amount, balance=500000.0,
                description=f"Razorpay Payout {utr}"
            )
            gt = GroundTruth(
                chain_id=chain_id, expected_status=MatchStatus.EXCEPTION,
                expected_root_cause=RootCause.DUPLICATE_PAYMENT, expected_discrepancy=gross_amount,
                notes="Two payment records submitted for a single invoice."
            )
            payments.extend([pay1, pay2])
            settlements.append(setl)
            bank_txns.append(bank)
            ground_truths.append(gt)

        elif scenario == "MISSING_SETTLEMENT":
            pay = Payment(
                payment_id=payment_id, order_id=order_id, gateway_txn_id=f"gtw_{i}",
                payment_date=txn_date.strftime("%Y-%m-%d %H:%M:%S"),
                gross_amount=gross_amount, fee=pg_fee, tax_on_fee=gst_on_fee, net_amount=net_payout
            )
            gt = GroundTruth(
                chain_id=chain_id, expected_status=MatchStatus.EXCEPTION,
                expected_root_cause=RootCause.MISSING_SETTLEMENT, expected_discrepancy=net_payout,
                notes="Payment captured but no settlement or bank payout record exists."
            )
            payments.append(pay)
            # No settlement or bank record added
            ground_truths.append(gt)

        elif scenario == "THRESHOLD_ANOMALY":
            pay = Payment(
                payment_id=payment_id, order_id=order_id, gateway_txn_id=f"gtw_{i}",
                payment_date=txn_date.strftime("%Y-%m-%d %H:%M:%S"),
                gross_amount=gross_amount, fee=0.0, tax_on_fee=0.0, net_amount=gross_amount
            )
            setl = Settlement(
                settlement_id=settlement_id, payment_id=payment_id,
                settlement_date=(txn_date + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                gross_amount=gross_amount, fee=0.0, tax=0.0, adjustment=0.0,
                net_amount=gross_amount, bank_reference=utr
            )
            bank = BankTransaction(
                bank_txn_id=f"BANK-{i:04d}",
                transaction_date=(txn_date + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
                reference=utr, credit=gross_amount, balance=500000.0,
                description=f"Razorpay Payout {utr}"
            )
            gt = GroundTruth(
                chain_id=chain_id, expected_status=MatchStatus.HIGH_RISK,
                expected_root_cause=RootCause.THRESHOLD_ANOMALY, expected_discrepancy=0.0,
                notes="Reconciled financially but flagged for suspicious repeated ₹9,999 transactions."
            )
            payments.append(pay)
            settlements.append(setl)
            bank_txns.append(bank)
            ground_truths.append(gt)

    # Save to DATA_DIR
    def _save_json(filename: str, data: list):
        path = os.path.join(DATA_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([item.model_dump() for item in data], f, indent=2)

    _save_json("invoices.json", invoices)
    _save_json("payments.json", payments)
    _save_json("settlements.json", settlements)
    _save_json("bank_statements.json", bank_txns)
    _save_json("ground_truth.json", ground_truths)
    
    print(f"Generated synthetic dataset with {num_chains} transaction chains into {DATA_DIR}")
    return invoices, payments, settlements, bank_txns, ground_truths

if __name__ == "__main__":
    generate_synthetic_dataset(200)
