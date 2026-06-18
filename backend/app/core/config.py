from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAIStageConfig(BaseModel):
    max_tokens: int
    temperature: float


class OpenAIPipelineConfig(BaseModel):
    guardrail: OpenAIStageConfig = OpenAIStageConfig(max_tokens=500, temperature=0.1)
    planner: OpenAIStageConfig = OpenAIStageConfig(max_tokens=1200, temperature=0.3)
    story_builder: OpenAIStageConfig = OpenAIStageConfig(max_tokens=3000, temperature=0.8)
    story_judge: OpenAIStageConfig = OpenAIStageConfig(max_tokens=1200, temperature=0.1)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    openai_api_key: str | None = None
    openai_model: str = "gpt-3.5-turbo"
    openai_pipeline_config: OpenAIPipelineConfig = Field(
        default_factory=OpenAIPipelineConfig
    )
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


settings = Settings()
