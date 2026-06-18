from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str | None = None


class PipelineStage(BaseModel):
    name: str
    status: str


class ChatResponse(BaseModel):
    session_id: str
    message: str
    stages: list[PipelineStage]
