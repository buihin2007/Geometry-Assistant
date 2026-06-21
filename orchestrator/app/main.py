import json
import time
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import get_settings
from .pipeline import Pipeline, LLMBudgetExceeded
from .supabase_client import SupabaseClient
from .gating import Gating, client_ip as gating_client_ip
from .ggb_client import GgbClient

settings = get_settings()
app = FastAPI(title="Hình học orchestrator", version="1.0.0")

# Frontend là SPA tĩnh khác origin → mở CORS (siết domain ở production nếu cần).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase = SupabaseClient(settings)
gating = Gating(settings, supabase)
pipeline = Pipeline(settings)
ggb = GgbClient(settings.ggb_service_url)


# ---------- Schemas ----------
class GenerateRequest(BaseModel):
    problem: str
    formats: list[str] | None = None


class SaveFigureRequest(BaseModel):
    title: str | None = None
    problem_text: str
    commands: list[str]
    thumbnail_url: str | None = None


class ReportRequest(BaseModel):
    problem_text: str
    commands: list[str] = []        # lưu plan/commands (text) → tái hiện tất định
    category: str = "khac"          # khong_ve_duoc | ve_sai | bo_cuc | khac
    note: str | None = None
    review_passed: bool | None = None
    warnings: list[str] = []


# ---------- Helpers ----------
async def _auth_user(authorization: str | None) -> tuple[str | None, str | None]:
    """Trả (jwt, user_id) nếu hợp lệ, ngược lại (None, None)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None, None
    jwt = authorization.split(" ", 1)[1].strip()
    user = await supabase.get_user(jwt)
    if not user:
        return None, None
    return jwt, user.get("id")


# ---------- Routes ----------
@app.get("/health")
async def health():
    out = {"ok": True, "provider": settings.llm_provider, "review": settings.enable_review}
    try:
        out["ggb"] = await ggb.health()
    except Exception as e:
        out["ggb"] = {"ok": False, "error": str(e)}
    return out


@app.post("/generate")
async def generate(
    body: GenerateRequest,
    request: Request,
    authorization: str | None = Header(default=None),
):
    jwt, user_id = await _auth_user(authorization)
    authenticated = user_id is not None

    decision = await gating.check(request, authenticated)
    if not decision.allowed:
        raise HTTPException(status_code=429, detail=decision.reason)

    if not body.problem or not body.problem.strip():
        raise HTTPException(status_code=400, detail="Thiếu đề bài.")

    try:
        result = await pipeline.run(body.problem.strip(), formats=body.formats)
    except LLMBudgetExceeded as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi pipeline: {e}")

    # Chỉ tính lượt khi chạy xong (không trừ lượt nếu lỗi server).
    await gating.consume(request, authenticated)

    return {
        "commands": result.commands,
        "pngBase64": result.png_base64,
        "svg": result.svg,
        "ggbBase64": result.ggb_base64,
        "rounds": result.rounds,
        "llmCalls": result.llm_calls,
        "reviewPassed": result.review_passed,
        "partial": result.partial,
        "warnings": result.warnings,
        "log": result.log,
        "remaining": decision.remaining,
    }


@app.post("/report")
async def report(body: ReportRequest, request: Request):
    """Người dùng báo hình SAI / góp ý — bắt lỗi im lặng mà auto-log không thấy.
    Lưu plan text (tái hiện tất định) + ghi chú. KHÔNG lưu ảnh (xem DEPLOY.md về
    lưu trữ bền cho prod). Chống spam nhẹ bằng IP + giới hạn độ dài note."""
    note = (body.note or "")[:1000]
    entry = {
        "ip": gating_client_ip(request),
        "category": body.category[:40],
        "note": note,
        "problem_text": body.problem_text[:2000],
        "commands": body.commands[:200],
        "review_passed": body.review_passed,
        "warnings": body.warnings[:50],
    }
    # Prod: lưu DB Supabase (bền qua scale-to-zero). Dev/không cấu hình: file fallback.
    if supabase.service_enabled:
        try:
            await supabase.insert_report(entry)
            return {"ok": True, "store": "supabase"}
        except Exception as e:
            # DB lỗi → vẫn cố ghi file để không mất report.
            entry["_supabase_error"] = str(e)
    try:
        path = Path(settings.report_log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **entry}, ensure_ascii=False) + "\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không lưu được report: {e}")
    return {"ok": True, "store": "file"}


@app.get("/figures")
async def list_figures(authorization: str | None = Header(default=None)):
    jwt, user_id = await _auth_user(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Cần đăng nhập.")
    return await supabase.list_figures(jwt)


@app.post("/figures")
async def save_figure(
    body: SaveFigureRequest, authorization: str | None = Header(default=None)
):
    jwt, user_id = await _auth_user(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Cần đăng nhập.")
    return await supabase.create_figure(jwt, user_id, body.model_dump())


@app.delete("/figures/{figure_id}")
async def delete_figure(
    figure_id: str, authorization: str | None = Header(default=None)
):
    jwt, user_id = await _auth_user(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Cần đăng nhập.")
    await supabase.delete_figure(jwt, figure_id)
    return {"ok": True}
