import datetime
from typing import List, Dict, Any, Tuple
from backend.schemas import ReconciliationResult, MatchStatus
from backend.engine.deterministic import DeterministicEngine
from backend.engine.investigator import RealLLMInvestigator
from backend.agent.tools import FinanceToolRegistry
from backend.channels.telegram_bot import TelegramChannel

class AgentController:
    """Autonomous AI Finance Controller Orchestrator."""

    def __init__(self, data_store: Dict[str, Any]):
        self.data_store = data_store
        self.trace: List[Dict[str, Any]] = []

    def log_trace(self, step_type: str, details: str, chain_id: str = None, metadata: Dict = None):
        entry = {
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            "step_type": step_type,
            "details": details,
            "chain_id": chain_id,
            "metadata": metadata or {}
        }
        self.trace.insert(0, entry)

    def run_autonomous_loop(self) -> Tuple[List[ReconciliationResult], Dict[str, Any]]:
        self.log_trace("EVENT_RECEIVED", "Triggered 4-way batch financial reconciliation")

        invs = self.data_store.get("invoices", [])
        pays = self.data_store.get("payments", [])
        sets = self.data_store.get("settlements", [])
        banks = self.data_store.get("bank_txns", [])

        # 1. Tool Call: Deterministic 4-Way Match
        self.log_trace("TOOL_CALL", "Executing DeterministicEngine 4-way symbolic matcher")
        engine = DeterministicEngine(invs, pays, sets, banks)
        results, unresolved = engine.run_reconciliation()
        self.log_trace("DETERMINISTIC", f"Resolved {len(results)} clean chains straight-through. {len(unresolved)} flagged for AI investigation.")

        # 2. Tool Call: LLM Exception Investigator on Unresolved Cases
        investigator = RealLLMInvestigator()
        for case in unresolved:
            chain_id = case["chain_id"]
            self.log_trace("TOOL_CALL", f"Invoking RealLLMInvestigator for {chain_id}", chain_id)
            res = investigator.investigate(case)
            
            # 3. Tool Call: Policy Authority Evaluation
            auth_res = FinanceToolRegistry.evaluate_authority_policy(res.discrepancy_amount)
            policy_status = auth_res["data"]["policy_status"]
            self.log_trace("POLICY_CHECK", auth_res["message"], chain_id, {"policy_status": policy_status})

            if policy_status == "AUTO_APPROVED":
                # Execute adjustment tool & verify
                adj_res = FinanceToolRegistry.execute_financial_adjustment(chain_id, res.discrepancy_amount, res.explanation)
                audit_id = adj_res["data"]["audit_id"]
                self.log_trace("ACTION_EXECUTED", adj_res["message"], chain_id, {"audit_id": audit_id})

                ver_res = FinanceToolRegistry.verify_outcome_consistency(chain_id, audit_id)
                self.log_trace("VERIFICATION", ver_res["message"], chain_id)

                res.status = MatchStatus.RECONCILED
                res.explanation += f" (Auto-Resolved under {audit_id})"
            elif policy_status == "REQUIRES_OWNER_APPROVAL":
                self.log_trace("NOTIFICATION", f"Pushed Telegram alert to owner for {chain_id} (Approval Required)", chain_id)
                TelegramChannel.send_exception_alert(
                    chain_id=chain_id,
                    invoice_id=res.invoice_id or "N/A",
                    discrepancy=res.discrepancy_amount,
                    explanation=res.explanation,
                    severity=res.severity.value,
                    confidence=res.confidence_score
                )

            results.append(res)

        auto_closed = len([r for r in results if r.status in [MatchStatus.RECONCILED, MatchStatus.PROBABLE_MATCH]])
        summary = {
            "total_records": len(results),
            "auto_closed_records": auto_closed,
            "controller_closure_rate": f"{round((auto_closed / len(results)) * 100, 1)}%",
            "exceptions_flagged": len(results) - auto_closed,
            "mode": "Autonomous AI Controller Engine"
        }

        self.log_trace("CONTROLLER_FINISHED", f"Controller completed execution loop. Closure rate: {summary['controller_closure_rate']}")
        return results, summary
