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
            # 2. Dynamic Tool-Calling Agent Loop on Unresolved Cases
            res = investigator.run_react_loop(case, self)
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
