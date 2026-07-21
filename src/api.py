import csv
import io
import json
import logging
import os
import shutil
import time
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, Response as FastAPIResponse, StreamingResponse

from src.config import DATA_DIR, PRELOAD_WHISPER
from src.auth import bearer, create_session, current_user, delete_session, hash_password, normalize_email, verify_password
from src.database import add_event, connection, get_call, get_events, init_db, now_iso, row_to_dict
from src.schemas import AnalyzeCallRequest, AuthResponse, CallAnalysisUpdate, CallEvent, CallRecord, LoginRequest, RegisterRequest, StatusUpdateRequest, UserResponse
from src.speech import get_speech_provider, normalize_audio
from src.pdf_report import build_call_pdf

logger = logging.getLogger("contender.api")
UPLOAD_DIR = Path(DATA_DIR) / "uploads"
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@asynccontextmanager
async def lifespan(_: FastAPI):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    if PRELOAD_WHISPER and "PYTEST_CURRENT_TEST" not in os.environ:
        def warm_whisper():
            try:
                get_speech_provider()._get_model()
                logger.info("Whisper model preloaded and ready")
            except Exception:
                logger.exception("Whisper preload failed; it will retry on the first audio call")
        threading.Thread(target=warm_whisper, name="whisper-warmup", daemon=True).start()
    yield


app = FastAPI(title="Contender Voice Intelligence API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/auth/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterRequest, response: Response):
    email = normalize_email(payload.email)
    with connection() as db:
        if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            raise HTTPException(409, "An account with this email already exists.")
        cursor = db.execute(
            "INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",
            (payload.name.strip(), email, hash_password(payload.password), now_iso()),
        )
        user_id = cursor.lastrowid
    user = {"id": user_id, "name": payload.name.strip(), "email": email}
    token = create_session(user_id)
    response.set_cookie("contender_session", token, httponly=True, samesite="lax", max_age=604800)
    return {"access_token": token, "user": user}


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response):
    email = normalize_email(payload.email)
    with connection() as db:
        row = db.execute("SELECT id,name,email,password_hash FROM users WHERE email = ?", (email,)).fetchone()
    if not row or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(401, "Incorrect email or password.")
    user = {"id": row["id"], "name": row["name"], "email": row["email"]}
    token = create_session(row["id"])
    response.set_cookie("contender_session", token, httponly=True, samesite="lax", max_age=604800)
    return {"access_token": token, "user": user}


@app.post("/auth/logout", status_code=204)
def logout(response: Response, user: dict = Depends(current_user)):
    delete_session(user["token"])
    response.delete_cookie("contender_session")


@app.get("/auth/me", response_model=UserResponse)
def me(user: dict = Depends(current_user)):
    return user


def owned_call(call_id: str, user_id: int) -> dict:
    call = get_call(call_id)
    if not call or call.get("created_by") != user_id:
        raise HTTPException(404, "Call not found.")
    return call


@app.post("/calls/upload", response_model=CallRecord, status_code=201)
def upload_call(file: UploadFile = File(...), user: dict = Depends(current_user)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Supported audio formats are MP3, WAV, and M4A.")
    call_id = f"CALL-{uuid.uuid4().hex[:8].upper()}"
    target = UPLOAD_DIR / f"{call_id}{suffix}"
    with target.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    if target.stat().st_size > MAX_UPLOAD_BYTES:
        target.unlink(missing_ok=True)
        raise HTTPException(413, "Audio file exceeds the 25 MB prototype limit.")
    created_at = now_iso()
    with connection() as db:
        db.execute("INSERT INTO calls(id,filename,created_at,created_by) VALUES(?,?,?,?)", (call_id, file.filename, created_at, user["id"]))
    add_event(call_id, "upload", None, file.filename)
    logger.info("Upload succeeded for %s", call_id)
    return get_call(call_id)


def update_processing(call_id: str, status: str, error: str | None = None) -> None:
    with connection() as db:
        db.execute("UPDATE calls SET processing_status = ?, processing_error = ? WHERE id = ?", (status, error, call_id))


def audio_path_for(call: dict) -> Path:
    return UPLOAD_DIR / f"{call['id']}{Path(call['filename']).suffix.lower()}"


def process_call(call_id: str, supplied_transcript: str | None = None) -> None:
    call = get_call(call_id)
    if not call:
        return
    transcript = supplied_transcript or call["transcript"]
    segments = call["transcript_segments"]
    try:
        if not transcript:
            update_processing(call_id, "Normalizing")
            normalized_path = normalize_audio(str(audio_path_for(call)))
            update_processing(call_id, "Transcribing")
            started = time.perf_counter()
            result = get_speech_provider().transcribe(normalized_path)
            transcript = result["text"]
            segments = result.get("segments", [])
            logger.info("Transcription completed for %s in %.2fs", call_id, time.perf_counter() - started)
        update_processing(call_id, "Analyzing")
        from src.llm_analyzer import analyze_transcript

        started = time.perf_counter()
        analysis = analyze_transcript(call_id, transcript)
        logger.info("AI analysis completed for %s in %.2fs", call_id, time.perf_counter() - started)
        fields = [
            "caller_name", "caller_phone", "company_name", "category", "priority", "priority_reason",
            "summary", "important_information", "recommended_next_action", "missing_information", "confidence_notes"
        ]
        values = [json.dumps(analysis[name]) if name in {"important_information", "missing_information", "confidence_notes"} else analysis[name] for name in fields]
        assignments = ", ".join(f"{name} = ?" for name in fields)
        with connection() as db:
            db.execute(
                f"UPDATE calls SET transcript = ?, transcript_segments = ?, processing_status = 'Complete', processing_error = NULL, {assignments} WHERE id = ?",
                [transcript, json.dumps(segments), *values, call_id],
            )
        add_event(call_id, "analysis", call["processing_status"], "Complete")
    except Exception as exc:
        logger.exception("Call processing failed for %s", call_id)
        update_processing(call_id, "Failed", str(exc)[:500])
        add_event(call_id, "processing_error", call["processing_status"], str(exc)[:500])


@app.post("/calls/{call_id}/analyze", response_model=CallRecord, status_code=202)
def analyze_call(call_id: str, background_tasks: BackgroundTasks, payload: AnalyzeCallRequest | None = None, user: dict = Depends(current_user)):
    call = owned_call(call_id, user["id"])
    if call["processing_status"] in {"Queued", "Normalizing", "Transcribing", "Analyzing"}:
        raise HTTPException(409, "This call is already being processed.")
    transcript = (payload.transcript if payload else None) or call["transcript"] or None
    update_processing(call_id, "Queued")
    add_event(call_id, "processing", call["processing_status"], "Queued")
    background_tasks.add_task(process_call, call_id, transcript)
    return get_call(call_id)


@app.post("/calls/analyze", response_model=CallRecord, status_code=202)
def analyze_compat(background_tasks: BackgroundTasks, call_id: str = Query(...), payload: AnalyzeCallRequest | None = None, user: dict = Depends(current_user)):
    return analyze_call(call_id, background_tasks, payload, user)


@app.patch("/calls/{call_id}/analysis", response_model=CallRecord)
def update_analysis(call_id: str, payload: CallAnalysisUpdate, user: dict = Depends(current_user)):
    call = owned_call(call_id, user["id"])
    data = payload.model_dump()
    changed = {key: {"previous": call.get(key), "new": value} for key, value in data.items() if call.get(key) != value}
    if changed:
        json_fields = {"important_information", "missing_information", "confidence_notes"}
        values = [json.dumps(value) if name in json_fields else value for name, value in data.items()]
        with connection() as db:
            db.execute(f"UPDATE calls SET {', '.join(f'{name} = ?' for name in data)} WHERE id = ?", [*values, call_id])
        add_event(call_id, "human_edit", json.dumps({k: v["previous"] for k, v in changed.items()}), json.dumps({k: v["new"] for k, v in changed.items()}))
    return get_call(call_id)


@app.get("/calls/{call_id}/events", response_model=list[CallEvent])
def call_events(call_id: str, user: dict = Depends(current_user)):
    owned_call(call_id, user["id"])
    return get_events(call_id)


@app.get("/calls/{call_id}/audio")
def call_audio(call_id: str, user: dict = Depends(current_user)):
    call = owned_call(call_id, user["id"])
    path = audio_path_for(call)
    if not path.exists():
        raise HTTPException(404, "Audio file not found.")
    return FileResponse(path, filename=call["filename"])


@app.get("/calls", response_model=list[CallRecord])
def list_calls(category: str | None = None, priority: str | None = None, status: str | None = None, search: str | None = None, user: dict = Depends(current_user)):
    clauses, params = ["created_by = ?"], [user["id"]]
    for field, value in (("category", category), ("priority", priority), ("status", status)):
        if value:
            clauses.append(f"{field} = ?")
            params.append(value)
    if search:
        clauses.append("(caller_name LIKE ? OR company_name LIKE ? OR filename LIKE ? OR summary LIKE ?)")
        params.extend([f"%{search}%"] * 4)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with connection() as db:
        rows = db.execute(f"SELECT * FROM calls{where} ORDER BY created_at DESC", params).fetchall()
    return [row_to_dict(row) for row in rows]


@app.get("/calls/export.csv")
def export_calls(user: dict = Depends(current_user)):
    calls = list_calls(user=user)
    output = io.StringIO()
    columns = ["id", "created_at", "filename", "caller_name", "company_name", "category", "priority", "status", "summary", "recommended_next_action"]
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(calls)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=calls.csv"})


@app.get("/calls/{call_id}", response_model=CallRecord)
def call_detail(call_id: str, user: dict = Depends(current_user)):
    return owned_call(call_id, user["id"])


@app.patch("/calls/{call_id}/status", response_model=CallRecord)
def update_status(call_id: str, payload: StatusUpdateRequest, user: dict = Depends(current_user)):
    call = owned_call(call_id, user["id"])
    with connection() as db:
        db.execute("UPDATE calls SET status = ? WHERE id = ?", (payload.status.value, call_id))
    add_event(call_id, "status_change", call["status"], payload.status.value)
    return get_call(call_id)


@app.get("/calls/{call_id}/export.txt", response_class=PlainTextResponse)
def export_call(call_id: str, user: dict = Depends(current_user)):
    call = owned_call(call_id, user["id"])
    return FastAPIResponse(
        content=build_call_pdf(call, get_events(call_id)),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{call_id}-report.pdf"'},
    )


@app.get("/calls/{call_id}/export.pdf")
def export_call_pdf(call_id: str, user: dict = Depends(current_user)):
    call = owned_call(call_id, user["id"])
    return FastAPIResponse(
        content=build_call_pdf(call, get_events(call_id)),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{call_id}-report.pdf"'},
    )
