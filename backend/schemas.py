from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime

class MatchStatus(str, Enum):
    RECONCILED = "RECONCILED"
    PROBABLE_MATCH = "PROBABLE_MATCH"
    EXCEPTION = "EXCEPTION"
    HIGH_RISK = "HIGH_RISK"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class RootCause(str, Enum):
    CLEAN_MATCH = "CLEAN_MATCH"
    GATEWAY_FEE_GST = "GATEWAY_FEE_GST"
    DATE_DRIFT = "DATE_DRIFT"
    SETTLEMENT_ADJUSTMENT = "SETTLEMENT_ADJUSTMENT"
    DUPLICATE_PAYMENT = "DUPLICATE_PAYMENT"
    MISSING_SETTLEMENT = "MISSING_SETTLEMENT"
    THRESHOLD_ANOMALY = "THRESHOLD_ANOMALY"
    MISSING_INVOICE = "MISSING_INVOICE"
    UNEXPLAINED_DISCREPANCY = "UNEXPLAINED_DISCREPANCY"

class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class Invoice(BaseModel):
    invoice_id: str
    order_id: str
    customer_id: str
    invoice_date: str
    gross_amount: float
    tax_amount: float
    net_amount: float
    currency: str = "INR"
    status: str = "ISSUED"

class Payment(BaseModel):
    payment_id: str
    order_id: str
    gateway_txn_id: str
    payment_date: str
    gross_amount: float
    fee: float
    tax_on_fee: float
    net_amount: float
    currency: str = "INR"
    status: str = "CAPTURED"

class Settlement(BaseModel):
    settlement_id: str
    payment_id: str
    settlement_date: str
    gross_amount: float
    fee: float
    tax: float
    adjustment: float = 0.0
    net_amount: float
    bank_reference: str  # UTR
    status: str = "SETTLED"

class BankTransaction(BaseModel):
    bank_txn_id: str
    transaction_date: str
    reference: str  # UTR
    credit: float
    debit: float = 0.0
    balance: float
    description: str

class GroundTruth(BaseModel):
    chain_id: str
    expected_status: MatchStatus
    expected_root_cause: RootCause
    expected_discrepancy: float = 0.0
    notes: Optional[str] = None

class ReconciliationResult(BaseModel):
    chain_id: str
    invoice_id: Optional[str] = None
    payment_id: Optional[str] = None
    settlement_id: Optional[str] = None
    bank_txn_id: Optional[str] = None
    status: MatchStatus
    root_cause: RootCause
    confidence_score: float
    discrepancy_amount: float = 0.0
    explanation: str
    evidence_ids: List[str] = []
    severity: Severity = Severity.LOW
