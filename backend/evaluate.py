import json
import os
from typing import List, Dict
from backend.schemas import Invoice, Payment, Settlement, BankTransaction, GroundTruth, ReconciliationResult, MatchStatus
from backend.engine.deterministic import DeterministicEngine
from backend.engine.investigator import LLMInvestigator

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

def run_evaluation() -> Dict:
    # 1. Load Data
    invoices = [Invoice(**x) for x in json.load(open(os.path.join(DATA_DIR, "invoices.json")))]
    payments = [Payment(**x) for x in json.load(open(os.path.join(DATA_DIR, "payments.json")))]
    settlements = [Settlement(**x) for x in json.load(open(os.path.join(DATA_DIR, "settlements.json")))]
    bank_txns = [BankTransaction(**x) for x in json.load(open(os.path.join(DATA_DIR, "bank_statements.json")))]
    ground_truths = [GroundTruth(**x) for x in json.load(open(os.path.join(DATA_DIR, "ground_truth.json")))]

    gt_dict = {gt.chain_id: gt for gt in ground_truths}

    # 2. Run Engine Pipeline
    deterministic_engine = DeterministicEngine(invoices, payments, settlements, bank_txns)
    results, unresolved = deterministic_engine.run_reconciliation()

    investigator = LLMInvestigator()
    for case in unresolved:
        res = investigator.investigate(case)
        results.append(res)

    pred_dict: Dict[str, ReconciliationResult] = {r.chain_id: r for r in results}

    # 3. Calculate Metrics
    total = len(ground_truths)
    tp_exception = 0
    fp_exception = 0
    fn_exception = 0
    correct_root_cause = 0
    auto_closed = 0

    for chain_id, gt in gt_dict.items():
        pred = pred_dict.get(chain_id)
        if not pred:
            continue

        # Closure rate (RECONCILED or PROBABLE_MATCH)
        if pred.status in [MatchStatus.RECONCILED, MatchStatus.PROBABLE_MATCH]:
            auto_closed += 1

        # Root Cause Accuracy
        if pred.root_cause == gt.expected_root_cause:
            correct_root_cause += 1

        # Exception Detection Precision & Recall
        is_gt_exception = gt.expected_status in [MatchStatus.EXCEPTION, MatchStatus.HIGH_RISK]
        is_pred_exception = pred.status in [MatchStatus.EXCEPTION, MatchStatus.HIGH_RISK]

        if is_pred_exception and is_gt_exception:
            tp_exception += 1
        elif is_pred_exception and not is_gt_exception:
            fp_exception += 1
        elif not is_pred_exception and is_gt_exception:
            fn_exception += 1

    precision = round((tp_exception / (tp_exception + fp_exception)) * 100, 2) if (tp_exception + fp_exception) > 0 else 100.0
    recall = round((tp_exception / (tp_exception + fn_exception)) * 100, 2) if (tp_exception + fn_exception) > 0 else 100.0
    root_cause_acc = round((correct_root_cause / total) * 100, 2)
    closure_rate = round((auto_closed / total) * 100, 2)

    metrics = {
        "total_records": total,
        "auto_closed_records": auto_closed,
        "controller_closure_rate": f"{closure_rate}%",
        "exception_precision": f"{precision}%",
        "exception_recall": f"{recall}%",
        "root_cause_accuracy": f"{root_cause_acc}%",
        "exceptions_flagged": len(total_exceptions := [r for r in results if r.status in [MatchStatus.EXCEPTION, MatchStatus.HIGH_RISK]]),
    }

    print("\n" + "="*50)
    print("      LEDGERPILOT RECONCILIATION EVALUATION      ")
    print("="*50)
    for k, v in metrics.items():
        print(f"  {k.replace('_', ' ').title():<28}: {v}")
    print("="*50 + "\n")

    return metrics

if __name__ == "__main__":
    run_evaluation()
