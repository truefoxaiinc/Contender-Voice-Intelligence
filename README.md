Contender Voice Call Intelligence Pipeline 🎙️⚡

An AI-driven voice call intelligence system for freight logistics. This prototype converts unstructured voice call transcripts into structured, actionable operational insights using OpenAI LLMs, Pydantic schema validation, and RAG (Retrieval-Augmented Generation) with FAISS.


📌 Project Overview & Scope

The Contender Voice Call Intelligence Prototype is designed as an AI Co-Pilot for Freight Dispatchers and Logistics Staff. It processes pre-recorded audio call transcripts, categorizes operational issues, assigns standardized priority levels, detects missing information, and provides human-in-the-loop recommended actions based on company Standard Operating Procedures (SOPs).

🚨 Operational Guardrails & Limitations (Human-in-the-Loop)

To maintain complete operational safety, this prototype does NOT :

* ❌ Integrate with live telephone systems or answer live incoming calls.
* ❌ Make direct customer commitments or promise freight delivery windows.
* ❌ Perform automated customer callbacks or generate freight price quotes.
* ❌ Act independently without human review.

Instead, it analyzes recordings and formats insights strictly for internal staff review.



📊 Benchmark Results

The pipeline includes a automated evaluation suite (`src/evaluator.py`) tested against 15 diverse logistics call scenarios.

| Metric | Pass Rate | Status |
| :--- | :---: | :---: |
| **Category Classification Accuracy** | **100.0%** (15/15) | ✅ PASS |
| **Priority Assignment Accuracy** | **100.0%** (15/15) | ✅ PASS |
| **Missing Information Extraction** | **100.0%** | ✅ PASS |
| **Output JSON Schema Validation** | **100.0%** | ✅ PASS |



🗂️ Supported Call Categories

1. Shipment Tracking Inquiry : Routine tracking checks or delayed load updates.
2. Quote Request  : Freight rate requests (identifies missing weights or dimensions).
3. Delivery Issue : Freight damage at dock, delivery refusals, or late arrivals.
4. Pickup Issue : Driver missed pickup windows, wrong addresses, or closed docks.
5. Customer Complaint : Billing fee disputes (e.g., unauthorized detention charges) or service escalations.
6. Carrier Communication : Driver location updates, traffic delays, or ETA logs.
7. Invoice Inquiry  : Routine invoice copy requests or payment status checks.
8. Document Request : Signed Proof of Delivery (POD) or Bill of Lading (BOL) requests.
9. New Business Inquiry : Sales leads and distribution expansion inquiries.



🛠️ Architecture & Tech Stack

* Language   : Python 3.10+
* LLM Engine : OpenAI GPT-4o (Structured Outputs via Pydantic)
* Retrieval-Augmented Generation (RAG) : LangChain + FAISS Vector Store
* Data Validation : Pydantic `BaseModel`
* Testing & Analytics : Pytest & Pandas



📁 Repository Structure


Contender_Voice_Intelligence/
├── data/
│   ├── sops/                      # Company Standard Operating Procedures (RAG Knowledge Base)
│   └── test_calls/                # Synthetic call transcripts for benchmark testing
├── src/
│   ├── __init__.py
│   ├── evaluator.py               # Benchmark evaluation engine
│   ├── llm_analyzer.py            # Core transcript processing module
│   ├── prompts.py                 # System prompts & category disambiguation rules
│   ├── rag_engine.py              # FAISS vector store & retriever setup
│   └── schemas.py                 # Pydantic data schemas
├── evaluation_results.csv         # Full 15-call benchmark evaluation results
├── requirements.txt               # Python package dependencies
├── .gitignore
└── README.md

🏎️ Getting Started

1. Prerequisites
   
   Ensure you have Python 3.10+ installed and an active OpenAI API key.

2. Installation
   
   Clone the repository and set up a virtual environment :

   git clone ( https://github.com/truefoxaiinc/Contender-Voice-Intelligence.git )
   
   cd Contender_Voice_Intelligence

  # Create & activate virtual environment

   python -m venv .venv
  
  # On Windows PowerShell :

   .venv\Scripts\Activate.ps1
  
  # On macOS/Linux :

    source .venv/bin/activate

  # Install dependencies

    pip install -r requirements.txt
    
3. Environment Setup
   
   Create a .env file in the root directory and add your OpenAI API key :

   OPENAI_API_KEY=your_openai_api_key_here

4. Run the Benchmark Evaluator
   
   Execute the evaluation suite across all 15 call transcripts :

   python -m src.evaluator

   This will run the analyzer, print the detailed pass/fail report to the terminal, and generate/update evaluation_results.csv.


   In your PyCharm terminal, run :

   git add README.md
   
   git commit -m "docs: add comprehensive README with architecture, benchmark metrics, and project guardrails"
   
   git push -u origin main

## FastAPI + React admin panel

The prototype now includes a FastAPI service and responsive React operations dashboard.

```powershell
# API (from the repository root)
pip install -r requirements.txt
uvicorn src.api:app --reload

# Admin panel (in a second terminal)
cd frontend
npm install
npm run dev
```

On Windows, the safest backend command is the included script, which always
uses the project virtual environment instead of a globally installed Uvicorn:

```powershell
.\run-backend.ps1
```

Open `http://localhost:5173`. The API documentation is available at
`http://localhost:8000/docs`.

Register an account on the first screen, then log in to access the dashboard.
Call uploads, call records, audio playback, exports, status changes, and edits
are protected and scoped to the logged-in user. Sessions expire after seven
days and can be invalidated immediately with Log out.

The upload limit is 25 MB and accepted formats are MP3, WAV, and M4A. For a
lightweight demo, paste a transcript after upload. Audio transcription uses the
optional `faster-whisper` provider; install it separately when required. AI
analysis requires `OPENAI_API_KEY` in `.env`.

### Low-latency settings

The backend caches the FAISS index and LLM client and preloads Whisper in a
background thread. Defaults favor faster CPU processing. They can be adjusted
in `.env`:

```env
WHISPER_MODEL_NAME=base.en
WHISPER_CPU_THREADS=4
PRELOAD_WHISPER=true
LLM_MODEL_NAME=gpt-4o-mini
```

Use `tiny.en` for the fastest English transcription on weaker computers, or
`small.en` for higher accuracy at the cost of additional processing time. A
submitted text transcript skips speech-to-text completely and is the fastest
way to generate a report.

### Docker startup

Create `.env` with `OPENAI_API_KEY`, then run:

```powershell
docker compose up --build
```

Open the admin panel at `http://localhost:8080` and API documentation at
`http://localhost:8000/docs`. FFmpeg and faster-whisper are included in the API
container. The first automatic transcription downloads the configured Whisper
model and can therefore take longer than later calls.
