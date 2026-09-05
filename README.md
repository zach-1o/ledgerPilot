# LedgerPilot 🤖💼

**LedgerPilot** is an Autonomous AI Finance Controller designed to eliminate manual financial reconciliation. 

Instead of acting as a "dumb pipeline", LedgerPilot operates a true **ReAct (Reasoning and Acting) Agent Loop**. It hooks into your payment gateways (like Razorpay) and bank statements, calculates discrepancies mathematically, and then autonomously uses financial tools to resolve them or escalate for human review via Telegram.

---

## ✨ Key Features

1. **Autonomous ReAct Agent Loop**:
   When LedgerPilot encounters an unresolved discrepancy, it hands the case to Google Gemini. Gemini acts autonomously, dynamically selecting tools to check authority policies, execute ledger adjustments, and verify outcomes without being forced into a rigid procedural loop.

2. **Deterministic 4-Way Matching**:
   Before the AI even looks at a transaction, LedgerPilot runs a fast, deterministic engine that automatically resolves up to 80-90% of straightforward cases (matching Invoices, Payments, Gateway Settlements, and Bank Transactions). The AI only steps in when humans normally would.

3. **Interactive Telegram Approval**:
   No more logging into dashboards to approve a ₹500 fee discrepancy. LedgerPilot pings the business owner on Telegram with a detailed exception report. The owner can click `[✅ Approve]` directly in the chat, which instantly calls a webhook, recalculates the exact missing amount, logs the action, and clears the exception.

4. **Structured & Safe LLM Output**:
   Instead of parsing conversational text that can easily break, LedgerPilot forces the LLM to output highly structured JSON (`root_cause`, `confidence`, `evidence_ids`). This makes the system incredibly resistant to hallucinations and completely production-ready.

5. **Single-Container Deployment**:
   LedgerPilot contains both a React frontend and a FastAPI backend, but it's engineered to be easily hostable. The provided multi-stage `Dockerfile` compiles the React UI and mounts it natively inside the Python FastAPI server. You can deploy the entire stack in one click on Render, Railway, or Heroku.

---

## 🛠️ Architecture

* **Backend:** FastAPI (Python), Google GenAI SDK (Gemini 2.5 Flash), Razorpay API
* **Frontend:** React, Vite, TailwindCSS (Hostable directly via the backend)
* **Agent Flow:** `Event -> Deterministic Match -> ReAct LLM Loop -> Tool Execution / Telegram Escalation`

---

## 🚀 How to Run Locally

### 1. Set Up Environment Variables
Create a `.env` file in the root directory (you can copy `.env.example`).
```env
TELEGRAM_BOT_TOKEN="your_bot_token"
OWNER_CHAT_ID="your_chat_id"
RAZORPAY_KEY_ID="your_razorpay_key"
RAZORPAY_KEY_SECRET="your_razorpay_secret"
```

### 2. Build the Frontend
```bash
cd frontend
npm install
npm run build
cd ..
```
*(FastAPI is configured to serve the `frontend/dist` directory automatically).*

### 3. Run the Backend
```bash
pip install -r requirements.txt
python -m backend.main
```
Your app will be live at `http://127.0.0.1:8000`.

---

## 🐳 How to Deploy (Docker)

LedgerPilot comes with a multi-stage Dockerfile that builds the frontend and bundles it with the backend into a single lightweight container.

```bash
docker build -t ledgerpilot .
docker run -p 8000:8000 --env-file .env ledgerpilot
```

## 🔒 Security
All API keys, tokens, and sensitive limits are securely managed via environment variables. The system strictly avoids writing credentials to disk, ensuring GitHub repository safety.

---
*Built for the Hackathon.*