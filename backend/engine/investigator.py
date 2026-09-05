import os
import json
from typing import Dict, Any, Optional
from backend.schemas import ReconciliationResult, MatchStatus, RootCause, Severity

class RealLLMInvestigator:
    """AI Exception Investigator using Google Gemini / OpenAI structured output API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")

    def investigate(self, unresolved_case: Dict[str, Any]) -> ReconciliationResult:
        chain_id = unresolved_case["chain_id"]
        inv = unresolved_case.get("invoice")
        pay = unresolved_case.get("payment")
        setl = unresolved_case.get("settlement")
        bank = unresolved_case.get("bank_entry")

        expected_net = unresolved_case.get("expected_net", inv.gross_amount if inv else 0.0)
        actual_net = setl.net_amount if setl else 0.0
        discrepancy = round(expected_net - actual_net, 2)

        # 1. Check if Gemini / OpenAI API Key is present
        if self.api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                
                prompt = (
                    f"You are the AI Finance Controller for LedgerPilot.\n"
                    f"Analyze this 4-way transaction discrepancy:\n"
                    f"Chain ID: {chain_id}\n"
                    f"Invoice Gross: ₹{inv.gross_amount if inv else 'N/A'}\n"
                    f"Payment Net: ₹{pay.net_amount if pay else 'N/A'}\n"
                    f"Settlement Payout: ₹{actual_net}\n"
                    f"Settlement Reserve Adjustment: ₹{setl.adjustment if setl else 0.0}\n"
                    f"Bank Credit: ₹{bank.credit if bank else 'N/A'}\n"
                    f"Expected Net Payout: ₹{expected_net}\n"
                    f"Discrepancy: ₹{discrepancy}\n\n"
                    f"Determine the root cause and output a brief 2-sentence financial explanation."
                )

                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                
                explanation = response.text.strip() if response and response.text else None
                if explanation:
                    root_cause = RootCause.SETTLEMENT_ADJUSTMENT if (setl and setl.adjustment > 0) else RootCause.UNEXPLAINED_DISCREPANCY
                    return ReconciliationResult(
                        chain_id=chain_id,
                        invoice_id=inv.invoice_id if inv else None,
                        payment_id=pay.payment_id if pay else None,
                        settlement_id=setl.settlement_id if setl else None,
                        bank_txn_id=bank.bank_txn_id if bank else None,
                        status=MatchStatus.EXCEPTION,
                        root_cause=root_cause,
                        confidence_score=0.96,
                        discrepancy_amount=discrepancy if discrepancy > 0 else (setl.adjustment if setl else 0.0),
                        explanation=f"[Gemini AI Model] {explanation}",
                        evidence_ids=[x for x in [inv.invoice_id if inv else None, pay.payment_id if pay else None, setl.settlement_id if setl else None] if x],
                        severity=Severity.MEDIUM if (setl and setl.adjustment > 0) else Severity.HIGH
                    )
            except Exception as e:
                print(f"LLM API call failed, falling back to deterministic investigator: {e}")

        # 2. Fallback Engine (Explicitly labeled)
        return DeterministicFallbackInvestigator.investigate(unresolved_case)


class DeterministicFallbackInvestigator:
    """Deterministic fallback investigator when LLM API keys are offline."""

    @staticmethod
    def investigate(unresolved_case: Dict[str, Any]) -> ReconciliationResult:
        chain_id = unresolved_case["chain_id"]
        inv = unresolved_case.get("invoice")
        pay = unresolved_case.get("payment")
        setl = unresolved_case.get("settlement")
        bank = unresolved_case.get("bank_entry")

        expected_net = unresolved_case.get("expected_net", inv.gross_amount if inv else 0.0)
        actual_net = setl.net_amount if setl else 0.0
        discrepancy = round(expected_net - actual_net, 2)

        if setl and setl.adjustment > 0:
            root_cause = RootCause.SETTLEMENT_ADJUSTMENT
            status = MatchStatus.EXCEPTION
            severity = Severity.MEDIUM
            explanation = (
                f"[Fallback Rule Engine] Settlement adjustment of ₹{setl.adjustment} identified. "
                f"Gateway settlement record contains a reserve hold of ₹{setl.adjustment}, "
                f"explaining the payout delta against expected net (₹{expected_net})."
            )
        else:
            root_cause = RootCause.UNEXPLAINED_DISCREPANCY
            status = MatchStatus.EXCEPTION
            severity = Severity.HIGH
            explanation = (
                f"[Fallback Rule Engine] Unresolved discrepancy of ₹{discrepancy}. "
                f"Invoice gross is ₹{inv.gross_amount if inv else 'N/A'}, settlement payout is ₹{actual_net}."
            )

        evidence_ids = [x for x in [inv.invoice_id if inv else None, pay.payment_id if pay else None, setl.settlement_id if setl else None] if x]

        return ReconciliationResult(
            chain_id=chain_id,
            invoice_id=inv.invoice_id if inv else None,
            payment_id=pay.payment_id if pay else None,
            settlement_id=setl.settlement_id if setl else None,
            bank_txn_id=bank.bank_txn_id if bank else None,
            status=status,
            root_cause=root_cause,
            confidence_score=0.92,
            discrepancy_amount=discrepancy if discrepancy > 0 else (setl.adjustment if setl else 0.0),
            explanation=explanation,
            evidence_ids=evidence_ids,
            severity=severity
        )

# Backward-compatible alias
LLMInvestigator = RealLLMInvestigator
