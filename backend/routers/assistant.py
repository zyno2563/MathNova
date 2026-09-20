"""AI Mathematics Assistant endpoints."""

from typing import List, Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.assistant.service import chat, status as assistant_status
from backend.limits import MAX_HISTORY_TURNS

router = APIRouter(prefix="/assistant", tags=["assistant"])


class HistoryEntry(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="The student's question",
        examples=["Find the Laplace transform of t^2 e^(-3t)"]
    )
    history: Optional[List[HistoryEntry]] = Field(
        default=None,
        max_length=MAX_HISTORY_TURNS,
        description="Prior turns, oldest first"
    )
    module: Optional[str] = Field(
        default=None,
        max_length=60,
        description="The MathNova module the student is currently using"
    )


@router.get("/status", summary="Whether the AI assistant is available")
def status():
    # Reports availability only. Which backend answers, which model it
    # uses and how it is configured are deployment details and are not
    # exposed to clients.
    return {"ok": True, "result": assistant_status()}


@router.post("/chat", summary="Ask the AI Mathematics Assistant")
def assistant_chat(request: ChatRequest):
    result = chat(
        message=request.message,
        history=[entry.model_dump() for entry in (request.history or [])],
        module_context=request.module
    )

    return {"ok": True, "result": result}
