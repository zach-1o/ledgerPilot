import json
import os
from typing import List, Optional, Dict
from fastapi import FastAPI, Query, HTTPException, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from backend.schemas import (
    Invoice, Payment, Settlement, BankTransaction, GroundTruth, ReconciliationResult, MatchStatus, RootCause
)
from backend.config import load_settings, save_settings, AppSettings
from backend.engine.deterministic import DeterministicEngine
from backend.engine.investigator import LLMInvestigator
from backend.engine.parser import UniversalParser
from backend.engine.razorpay_client import RazorpayClient
from backend.channels.telegram_bot import TelegramChannel
from backend.evaluate import run_evaluation

app = FastAPI(
    title="LedgerPilot API",
    description="AI Finance Controller for 4-Way Reconciliation & Audit Engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

CACHE = {
    "results": [],
    "summary": {},
    "invoices": [],
    "payments": [],
    "settlements": [],
    "bank_txns": [],
    "activity_log": []
}

def log_activity(action: str, details: str, chain_id: Optional[str] = None):
    import datetime
    CACHE["activity_log"].insert(0, {
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
        "action": action,
        "details": details,
        "chain_id": chain_id
    })
    # Keep last 50 events
    CACHE["activity_log"] = CACHE["activity_log"][:50]

def load_all_datasets():
    invs = [Invoice(**x) for x in json.load(open(os.path.join(DATA_DIR, "invoices.json")))]
    pays = [Payment(**x) for x in json.load(open(os.path.join(DATA_DIR, "payments.json")))]
    sets = [Settlement(**x) for x in json.load(open(os.path.join(DATA_DIR, "settlements.json")))]
    banks = [BankTransaction(**x) for x in json.load(open(os.path.join(DATA_DIR, "bank_statements.json")))]
    return invs, pays, sets, banks

@app.get("/health")
def health_check():
    return {
        "status": "online",
        "system": "LedgerPilot AI Finance Controller",
        "mode": "Hermes-Style Autonomous Ready",
        "version": "1.0.0"
    }

# --- Settings & Control Plane API ---

@app.get("/api/settings")
def get_app_settings():
    return load_settings().model_dump()

@app.post("/api/settings")
def update_app_settings(settings: AppSettings = Body(...)):
    saved = save_settings(settings)
    log_activity("SETTINGS_UPDATED", "Updated Telegram, Email, and Authority limits via Control Plane")
    return {"status": "success", "settings": saved.model_dump()}

@app.post("/api/settings/test-telegram")
def test_telegram_connection(
    token: str = Form(...),
    chat_id: str = Form(...)
):
    try:
        res = TelegramChannel.send_test_message(token, chat_id)
        log_activity("TELEGRAM_TEST", f"Sent test message to chat {chat_id}")
        return {"status": "success", "response": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Telegram test failed: {str(e)}")

@app.get("/api/activity")
def get_activity_feed():
    return {"events": CACHE["activity_log"]}

# --- Reconciliation & Processing API ---

@app.post("/api/reconcile/run")
def trigger_reconciliation():
    invs, pays, sets, banks = load_all_datasets()
    CACHE["invoices"] = invs
    CACHE["payments"] = pays
    CACHE["settlements"] = sets
    CACHE["bank_txns"] = banks

    engine = DeterministicEngine(invs, pays, sets, banks)
    results, unresolved = engine.run_reconciliation()
    
    investigator = LLMInvestigator()
    for case in unresolved:
        res = investigator.investigate(case)
        results.append(res)

    CACHE["results"] = results
    CACHE["summary"] = run_evaluation()

    log_activity("RECONCILIATION_RUN", f"Processed 200 record chains. Closure rate: {CACHE['summary'].get('controller_closure_rate')}")
    
    # Send sample alert to Telegram if configured for the first exception
    exceptions = [r for r in results if r.status in [MatchStatus.EXCEPTION, MatchStatus.HIGH_RISK]]
    if exceptions:
        ex = exceptions[0]
        TelegramChannel.send_exception_alert(
            chain_id=ex.chain_id,
            invoice_id=ex.invoice_id or "N/A",
            discrepancy=ex.discrepancy_amount,
            explanation=ex.explanation,
            severity=ex.severity.value,
            confidence=ex.confidence_score
        )
        log_activity("TELEGRAM_ALERT_SENT", f"Pushed Telegram alert for exception {ex.chain_id}", ex.chain_id)

    return {
        "status": "success",
        "message": f"Successfully processed {len(results)} transaction chains.",
        "summary": CACHE["summary"]
    }

@app.post("/api/reconcile/upload")
async def upload_and_reconcile(
    invoices_file: Optional[UploadFile] = File(None),
    payments_file: Optional[UploadFile] = File(None),
    settlements_file: Optional[UploadFile] = File(None),
    bank_file: Optional[UploadFile] = File(None)
):
    invs, pays, sets, banks = load_all_datasets()

    if invoices_file:
        content = (await invoices_file.read()).decode("utf-8")
        invs = UniversalParser.parse_invoices_csv(content)
    if payments_file:
        content = (await payments_file.read()).decode("utf-8")
        pays = UniversalParser.parse_payments_csv(content)
    if settlements_file:
        content = (await settlements_file.read()).decode("utf-8")
        sets = UniversalParser.parse_settlements_csv(content)
    if bank_file:
        content = (await bank_file.read()).decode("utf-8")
        banks = UniversalParser.parse_bank_csv(content)

    CACHE["invoices"] = invs
    CACHE["payments"] = pays
    CACHE["settlements"] = sets
    CACHE["bank_txns"] = banks

    engine = DeterministicEngine(invs, pays, sets, banks)
    results, unresolved = engine.run_reconciliation()

    investigator = LLMInvestigator()
    for case in unresolved:
        res = investigator.investigate(case)
        results.append(res)

    CACHE["results"] = results
    auto_closed = len([r for r in results if r.status in [MatchStatus.RECONCILED, MatchStatus.PROBABLE_MATCH]])
    exceptions = len([r for r in results if r.status in [MatchStatus.EXCEPTION, MatchStatus.HIGH_RISK]])
    
    CACHE["summary"] = {
        "total_records": len(results),
        "auto_closed_records": auto_closed,
        "controller_closure_rate": f"{round((auto_closed/len(results))*100, 1)}%" if results else "0%",
        "exceptions_flagged": exceptions,
        "mode": "Custom Real-World Upload"
    }

    log_activity("CSV_UPLOAD_RECONCILE", f"Processed {len(results)} custom uploaded records")
    return {
        "status": "success",
        "message": f"Processed {len(results)} uploaded transaction chains.",
        "summary": CACHE["summary"]
    }

@app.post("/api/reconcile/razorpay-sync")
def sync_razorpay_test_mode(key_id: str = Form(...), key_secret: str = Form(...)):
    try:
        client = RazorpayClient(key_id, key_secret)
        pays = client.fetch_payments(50)
        sets = client.fetch_settlements(50)

        invs = [Invoice(
            invoice_id=f"INV-{p.order_id}", order_id=p.order_id, customer_id="CUST-SANDBOX",
            invoice_date=p.payment_date, gross_amount=p.gross_amount, tax_amount=0.0, net_amount=p.gross_amount
        ) for p in pays]

        banks = [BankTransaction(
            bank_txn_id=f"BANK-{s.settlement_id}", transaction_date=s.settlement_date,
            reference=s.bank_reference, credit=s.net_amount, balance=500000.0,
            description=f"Razorpay Payout {s.bank_reference}"
        ) for s in sets]

        CACHE["invoices"] = invs
        CACHE["payments"] = pays
        CACHE["settlements"] = sets
        CACHE["bank_txns"] = banks

        engine = DeterministicEngine(invs, pays, sets, banks)
        results, unresolved = engine.run_reconciliation()

        investigator = LLMInvestigator()
        for case in unresolved:
            res = investigator.investigate(case)
            results.append(res)

        CACHE["results"] = results
        auto_closed = len([r for r in results if r.status in [MatchStatus.RECONCILED, MatchStatus.PROBABLE_MATCH]])
        
        CACHE["summary"] = {
            "total_records": len(results),
            "auto_closed_records": auto_closed,
            "controller_closure_rate": f"{round((auto_closed/len(results))*100, 1)}%" if results else "0%",
            "exceptions_flagged": len(results) - auto_closed,
            "mode": "Razorpay Test-Mode Live Sync"
        }

        log_activity("RAZORPAY_API_SYNC", f"Synced 50 payments and 50 settlements live from Razorpay Sandbox")
        return {
            "status": "success",
            "message": f"Successfully synced {len(results)} live sandbox records from Razorpay API.",
            "summary": CACHE["summary"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Razorpay API Sync failed: {str(e)}")

@app.get("/api/reconcile/summary")
def get_summary():
    if not CACHE["summary"]:
        trigger_reconciliation()
    return CACHE["summary"]

@app.get("/api/reconcile/results")
def get_results(status: Optional[str] = Query(None)):
    if not CACHE["results"]:
        trigger_reconciliation()
    
    results = CACHE["results"]
    if status:
        results = [r for r in results if r.status.value == status.upper()]
        
    return {
        "count": len(results),
        "results": [r.model_dump() for r in results]
    }

@app.get("/api/reconcile/case/{chain_id}")
def get_case_detail(chain_id: str):
    if not CACHE["results"]:
        trigger_reconciliation()
        
    res = next((r for r in CACHE["results"] if r.chain_id == chain_id), None)
    if not res:
        raise HTTPException(status_code=404, detail="Transaction chain case not found.")

    invs = CACHE.get("invoices") or load_all_datasets()[0]
    pays = CACHE.get("payments") or load_all_datasets()[1]
    sets = CACHE.get("settlements") or load_all_datasets()[2]
    banks = CACHE.get("bank_txns") or load_all_datasets()[3]

    invoice = next((i for i in invs if i.invoice_id == res.invoice_id), None)
    payment = next((p for p in pays if p.payment_id == res.payment_id), None)
    settlement = next((s for s in sets if s.settlement_id == res.settlement_id), None)
    bank_entry = next((b for b in banks if b.bank_txn_id == res.bank_txn_id or (settlement and b.reference == settlement.bank_reference)), None)

    return {
        "reconciliation": res.model_dump(),
        "trace": {
            "invoice": invoice.model_dump() if invoice else None,
            "payment": payment.model_dump() if payment else None,
            "settlement": settlement.model_dump() if settlement else None,
            "bank_transaction": bank_entry.model_dump() if bank_entry else None
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
