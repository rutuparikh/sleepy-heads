import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.story_pipeline import StoryPipeline
from app.services.responses_client import ResponsesClient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])
session_user_requests: dict[str, list[str]] = {}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or str(uuid4())
    user_request = session_user_requests.setdefault(session_id, [])
    user_request.append(request.message)

    logger.info(
        "Received chat request session_id=%s message_chars=%s request_count=%s.",
        session_id,
        len(request.message),
        len(user_request),
    )
    pipeline = StoryPipeline(ResponsesClient())

    try:
        result = await pipeline.run(user_request)
    except ValueError as exc:
        logger.warning("Chat request failed validation: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "Chat request completed with stages=%s and response_chars=%s.",
        [stage.name for stage in result.stages],
        len(result.final_text),
    )
    return ChatResponse(
        session_id=session_id,
        message=result.final_text,
        stages=result.stages,
    )
