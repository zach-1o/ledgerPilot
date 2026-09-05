import json
import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Query, HTTPException, UploadFile, File, Form, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.schemas import (
    Invoice, Payment, Settlement, BankTransaction, GroundTruth, ReconciliationResult, MatchStatus, RootCause
)
from backend.config import load_settings, save_settings, AppSettings
from backend.agent.controller import AgentController
from backend.agent.tools import FinanceToolRegistry
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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        os.getenv("FRONTEND_URL", "http://localhost")
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
    "controller": None
}

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
        "mode": "Agentic Tool Loop Active",
        "version": "1.0.0"
    }

# --- Settings & Control Plane API ---

@app.get("/api/settings")
def get_app_settings():
    return load_settings().model_dump()

@app.post("/api/settings")
def update_app_settings(settings: AppSettings = Body(...)):
    saved = save_settings(settings)
    return {"status": "success", "settings": saved.model_dump()}

@app.post("/api/settings/test-telegram")
def test_telegram_connection(token: str = Form(...), chat_id: str = Form(...)):
    try:
        res = TelegramChannel.send_test_message(token, chat_id)
        return {"status": "success", "response": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Telegram test failed: {str(e)}")

@app.get("/api/activity")
def get_agent_trace():
    if CACHE["controller"]:
        return {"events": CACHE["controller"].trace}
    return {"events": []}

# --- Reconciliation & Agent Controller API ---

@app.post("/api/reconcile/run")
def trigger_reconciliation():
    invs, pays, sets, banks = load_all_datasets()
    data_store = {
        "invoices": invs,
        "payments": pays,
        "settlements": sets,
        "bank_txns": banks
    }
    CACHE["invoices"] = invs
    CACHE["payments"] = pays
    CACHE["settlements"] = sets
    CACHE["bank_txns"] = banks

    controller = AgentController(data_store)
    results, summary = controller.run_autonomous_loop()

    CACHE["controller"] = controller
    CACHE["results"] = results
    CACHE["summary"] = summary
    
    return {
        "status": "success",
        "message": f"Successfully executed agent controller loop across {len(results)} record chains.",
        "summary": summary
    }

@app.post("/api/telegram/webhook")
async def handle_telegram_callback(request: Request):
    """Processes interactive Telegram button callbacks (approve, reject, inspect)."""
    try:
        payload = await request.json()
        callback_query = payload.get("callback_query")
        if not callback_query:
            return {"status": "ignored"}

        data = callback_query.get("data", "")
        action, chain_id = data.split(":") if ":" in data else (data, "")
        controller = CACHE.get("controller")

        if action == "approve" and chain_id:
            # Retrieve the proposed case
            case_res = next((r for r in CACHE.get("results", []) if r.chain_id == chain_id), None)
            if not case_res:
                return {"status": "error", "message": "Transaction chain not found in cache"}
                
            discrepancy = case_res.discrepancy_amount
            
            # Re-check authority (sanity check)
            policy_res = FinanceToolRegistry.evaluate_authority_policy(discrepancy)
            
            # Execute adjustment tool using the actual calculated discrepancy
            adj_res = FinanceToolRegistry.execute_financial_adjustment(chain_id, discrepancy, "Approved by Owner via Telegram")
            audit_id = adj_res["data"]["audit_id"]
            
            if controller:
                controller.log_trace("OWNER_APPROVED_TELEGRAM", f"Owner approved adjustment of ₹{discrepancy:,.2f} for {chain_id} via Telegram", chain_id, {"audit_id": audit_id, "policy_check": policy_res["message"]})
                controller.log_trace("ACTION_EXECUTED", adj_res["message"], chain_id)
                ver_res = FinanceToolRegistry.verify_outcome_consistency(chain_id, audit_id)
                controller.log_trace("VERIFICATION", ver_res["message"], chain_id)

            # Update cache result
            for r in CACHE["results"]:
                if r.chain_id == chain_id:
                    r.status = MatchStatus.RECONCILED
                    r.explanation += f" (Approved via Telegram, Audit ID: {audit_id})"

            return {"status": "success", "message": f"Approved {chain_id} under {audit_id}"}

        elif action == "reject" and chain_id:
            if controller:
                controller.log_trace("OWNER_REJECTED_TELEGRAM", f"Owner rejected auto-resolution for {chain_id}. Escalated to manual human review.", chain_id)

            for r in CACHE["results"]:
                if r.chain_id == chain_id:
                    r.status = MatchStatus.EXCEPTION
                    r.explanation += " (Escalated by Owner via Telegram)"

            return {"status": "success", "message": f"Escalated {chain_id}"}

    except Exception as e:
        print(f"Error handling Telegram callback: {e}")
    return {"status": "error"}

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

    data_store = {"invoices": invs, "payments": pays, "settlements": sets, "bank_txns": banks}
    controller = AgentController(data_store)
    results, summary = controller.run_autonomous_loop()

    CACHE["controller"] = controller
    CACHE["results"] = results
    CACHE["summary"] = summary
    summary["mode"] = "Custom Real-World Upload"

    return {
        "status": "success",
        "message": f"Processed {len(results)} uploaded transaction chains.",
        "summary": summary
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

        data_store = {"invoices": invs, "payments": pays, "settlements": sets, "bank_txns": banks}
        controller = AgentController(data_store)
        results, summary = controller.run_autonomous_loop()

        CACHE["controller"] = controller
        CACHE["results"] = results
        CACHE["summary"] = summary
        summary["mode"] = "Razorpay Test-Mode Live Sync"

        return {
            "status": "success",
            "message": f"Successfully synced {len(results)} live sandbox records from Razorpay API.",
            "summary": summary
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

# --- Frontend Static Serving ---
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        requested_file = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(requested_file):
            return FileResponse(requested_file)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
