"""Asynchronous Studio-facing API; Python manager calls stay synchronous by default."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from app.engineering_loop import engineering_manager, EngineeringState as S

router = APIRouter(prefix="/engineering")


@router.get("/capabilities")
def capabilities():
    import os
    from app.config import config
    from app.engineering_loop import setting
    return {"model_name": os.environ.get("LITECODER_MODEL_NAME") or config.get("MODEL_NAME", "Qwen/Qwen2.5-Coder-1.5B"),
            "lora_enabled": bool(config.get("LORA_ENABLED", False)),
            "memory_enabled": setting(None, "LITECODER_MEMORY_ENABLED", "MEMORY_ENABLED"),
            "strategy_enabled": setting(None, "LITECODER_STRATEGY_ENABLED", "STRATEGY_LEARNING_ENABLED"),
            "max_attempts": 3, "approval_required": True}


class EngineeringRequest(BaseModel):
    task_prompt: str = Field(min_length=1, max_length=20000)
    repo_root: str = Field(min_length=1)
    test_command: str = Field(min_length=1, max_length=2000)
    fallback_enabled: Optional[bool] = None
    repo_index_enabled: Optional[bool] = None
    prompt_example_enabled: Optional[bool] = None
    memory_enabled: Optional[bool] = None
    strategy_enabled: Optional[bool] = None
    storage_dir: Optional[str] = None
    max_attempts: int = Field(default=3, ge=1, le=10)
    test_timeout: float = Field(default=30, gt=0, le=600)


def find_session(session_id):
    session = engineering_manager.get_session(session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    return session


@router.post("/start", status_code=202)
def start_engineering(req: EngineeringRequest):
    session_id = engineering_manager.start_session(**req.model_dump(), eager_policy_check=True, background=True)
    return find_session(session_id).get_status()


@router.post("/approve/{session_id}", status_code=202)
def approve_engineering(session_id: str, expected_patch_hash: str = Query(min_length=64, max_length=64)):
    session = find_session(session_id)
    status = session.get_status()
    if status["state"] != S.AWAITING_APPROVAL or status["current_patch_hash"] != expected_patch_hash:
        raise HTTPException(409, "Proposal state/hash changed; refresh before approving")
    if not engineering_manager.dispatch(session_id, approve_hash=expected_patch_hash):
        raise HTTPException(409, "Session worker already running")
    return {"session_id": session_id, "accepted": True}


@router.post("/reject/{session_id}")
def reject_engineering(session_id: str):
    session = find_session(session_id)
    if not session.reject():
        raise HTTPException(409, "Session is not awaiting approval")
    return session.get_status()


@router.post("/cancel/{session_id}")
def cancel_engineering(session_id: str):
    session = find_session(session_id)
    session.cancel()
    return session.get_status()


@router.get("/status/{session_id}")
def get_engineering_status(session_id: str):
    return find_session(session_id).get_status()
