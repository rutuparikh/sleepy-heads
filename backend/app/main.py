import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.core.config import settings

'''
    what you would have built next if you spent 2 more hours on this project?
    - Implement multi-agent orchestration by creating individual agents for each task so they can be called independently, for example calling `story_judge` only to judge a given story input.
    - Implement stage-level observability dashboard for scores, retries, and token usage.

'''

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logging.getLogger("app").setLevel(logging.INFO)

app = FastAPI(title="Code-Managed Prompt Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
