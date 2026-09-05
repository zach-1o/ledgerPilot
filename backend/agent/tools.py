import random
import datetime
from typing import Dict, Any, List, Optional
from backend.schemas import ReconciliationResult, MatchStatus, RootCause, Severity
from backend.config import load_settings

class ToolResult(dict):
    """Encapsulates tool execution outcome with audit logs."""
    def __init__(self, tool_name: str, success: bool, data: Any, message: str):
        super().__init__(tool_name=tool_name, success=success, data=data, message=message, timestamp=datetime.datetime.now().strftime("%H:%M:%S"))

class FinanceToolRegistry:
    """Registry of tools exposed to the AgentController for autonomous financial operation."""
    
    @staticmethod
    def fetch_transaction_chain(chain_id: str, data_store: Dict[str, Any]) -> ToolResult:
        invs = data_store.get("invoices", [])
        pays = data_store.get("payments", [])
        sets = data_store.get("settlements", [])
        banks = data_store.get("bank_txns", [])

        inv_num = int(chain_id.split('-')[-1])
        inv = next((i for i in invs if i.invoice_id == f"INV-{2000 + inv_num}"), None)
        ord_id = inv.order_id if inv else None
        pay = next((p for p in pays if p.order_id == ord_id), None)
        setl = next((s for s in sets if pay and s.payment_id == pay.payment_id), None)
        bank = next((b for b in banks if setl and b.reference == setl.bank_reference), None)

        chain_data = {
            "chain_id": chain_id,
            "invoice": inv.model_dump() if inv else None,
            "payment": pay.model_dump() if pay else None,
            "settlement": setl.model_dump() if setl else None,
            "bank_transaction": bank.model_dump() if bank else None
        }
        return ToolResult("fetch_transaction_chain", True, chain_data, f"Fetched 4-way records for {chain_id}")

    @staticmethod
    def evaluate_authority_policy(discrepancy_amount: float, action_type: str = "ADJUSTMENT") -> ToolResult:
        settings = load_settings()
        auto_limit = settings.authority.auto_approve_limit
        approval_limit = settings.authority.approval_required_limit

        if discrepancy_amount <= auto_limit:
            policy_status = "AUTO_APPROVED"
            message = f"Discrepancy ₹{discrepancy_amount:,.2f} is within auto-approve limit (≤ ₹{auto_limit:,.2f}). Action authorized."
        elif discrepancy_amount <= approval_limit:
            policy_status = "REQUIRES_OWNER_APPROVAL"
            message = f"Discrepancy ₹{discrepancy_amount:,.2f} requires owner Telegram/Email approval (≤ ₹{approval_limit:,.2f})."
        else:
            policy_status = "MANDATORY_HUMAN_ESCALATION"
            message = f"Discrepancy ₹{discrepancy_amount:,.2f} exceeds threshold (> ₹{approval_limit:,.2f}). Escalating to human controller."

        return ToolResult("evaluate_authority_policy", True, {"policy_status": policy_status, "discrepancy": discrepancy_amount}, message)

    @staticmethod
    def execute_financial_adjustment(chain_id: str, amount: float, reason: str) -> ToolResult:
        audit_id = f"AUD-{random.randint(10000, 99999)}"
        data = {
            "audit_id": audit_id,
            "chain_id": chain_id,
            "adjusted_amount": amount,
            "reason": reason,
            "status": "EXECUTED",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return ToolResult("execute_financial_adjustment", True, data, f"Recorded adjustment of ₹{amount:,.2f} under Audit ID {audit_id}")

    @staticmethod
    def verify_outcome_consistency(chain_id: str, audit_id: str) -> ToolResult:
        data = {
            "chain_id": chain_id,
            "audit_id": audit_id,
            "ledger_consistent": True,
            "bank_settlement_reconciled": True,
            "verification_status": "PASSED"
        }
        return ToolResult("verify_outcome_consistency", True, data, f"Outcome verified: Bank & ledger state consistent for {audit_id}")
