import json
import logging
from dataclasses import dataclass

from app.core.config import settings
from app.schemas.chat import PipelineStage
from app.services.prompt_loader import load_prompt
from app.services.responses_client import ResponsesClient

logger = logging.getLogger(__name__)

STORY_PLAN_FIELDS = {
    "moods",
    "morals",
    "themes",
    "main_characters",
    "side_characters",
    "user_instructions",
    "age",
    "length",
    "story_outline",
}

STORY_FIELDS = {
    "title",
    "introduction",
    "plot",
    "conclusion",
    "moral",
}

FEEDBACK_FIELDS = {
    "score",
    "to_update",
    "recommendations",
}

MIN_ACCEPTABLE_STORY_SCORE = 8
MAX_STORY_BUILD_ATTEMPTS = 3


@dataclass
class PipelineResult:
    final_text: str
    stages: list[PipelineStage]


class StoryPipeline:
    def __init__(self, responses_client: ResponsesClient) -> None:
        self.responses_client = responses_client

    async def run(self, user_request: list[str]) -> PipelineResult:
        stages: list[PipelineStage] = []
        logger.info("Story pipeline started with request_count=%s.", len(user_request))
        user_request_input = self.create_user_request_input(user_request)

        logger.info("Stage input_guardrail started.")
        guardrail_decision = await self.check_input_guardrails(user_request_input)
        stages.append(PipelineStage(name="input_guardrail", status="completed"))
        logger.info("Stage input_guardrail completed.")

        decision = str(guardrail_decision.get("decision", "")).lower()
        if decision == "reject":
            logger.info("Story pipeline rejected request: %s", guardrail_decision.get("reason"))
            return PipelineResult(
                final_text=self.create_rejection_response(guardrail_decision),
                stages=stages,
            )

        if decision != "allow":
            raise ValueError("Input guardrail returned an unknown decision.")

        logger.info("Stage planner started.")
        plan = await self.create_story_plan(user_request_input)
        stages.append(PipelineStage(name="planner", status="completed"))
        logger.info("Stage planner completed with fields=%s.", sorted(plan.keys()))

        draft: dict | None = None
        feedback = self.empty_feedback()

        for attempt in range(1, MAX_STORY_BUILD_ATTEMPTS + 1):
            logger.info("Stage story_builder attempt %s started.", attempt)
            draft = await self.build_story(plan, feedback, story=draft)
            stages.append(PipelineStage(name=f"story_builder_{attempt}", status="completed"))
            logger.info(
                "Stage story_builder attempt %s completed with title=%r.",
                attempt,
                draft.get("title"),
            )

            logger.info("Stage story_judge attempt %s started.", attempt)
            judge_response = await self.judge_story(plan, draft)
            stages.append(PipelineStage(name=f"story_judge_{attempt}", status="completed"))

            feedback = judge_response["feedback"]
            score = self.get_feedback_score(feedback)
            logger.info("Stage story_judge attempt %s completed with score=%s.", attempt, score)

            if score >= MIN_ACCEPTABLE_STORY_SCORE:
                logger.info("Story accepted with score=%s on attempt %s.", score, attempt)
                break

            if score < MIN_ACCEPTABLE_STORY_SCORE and attempt < MAX_STORY_BUILD_ATTEMPTS:
                logger.info(
                    "Story score %s is below %s; rebuilding with judge feedback.",
                    score,
                    MIN_ACCEPTABLE_STORY_SCORE,
                )
            else:
                logger.info(
                    "Story score %s is below %s, but max attempts reached.",
                    score,
                    MIN_ACCEPTABLE_STORY_SCORE,
                )

        if draft is None:
            raise ValueError("Story builder did not produce a draft.")

        final_story = self.form_final_story(draft)
        logger.info("Story pipeline completed with final_story_chars=%s.", len(final_story))
        return PipelineResult(final_text=final_story, stages=stages)

    def create_user_request_input(self, user_request: list[str]) -> str:
        return json.dumps(
            {
                "user_request": user_request,
            }
        )

    async def check_input_guardrails(self, user_request: str) -> dict:
        guardrail_prompt = load_prompt("input_guardrail")
        stage_config = settings.openai_pipeline_config.guardrail
        guardrail_result = await self.responses_client.create(
            guardrail_prompt,
            user_request,
            max_tokens=stage_config.max_tokens,
            temperature=stage_config.temperature,
        )

        return self.parse_json_response(
            guardrail_result,
            "Input guardrail returned invalid JSON.",
        )

    def create_rejection_response(self, guardrail_decision: dict) -> str:
        reason = guardrail_decision.get("reason", "This request is not allowed.")
        safe_rewrite = guardrail_decision.get("safe_rewrite")

        if not safe_rewrite:
            return reason

        return (
            f"{reason}\n\n"
            f"Recommended request type: {safe_rewrite}"
        )

    async def create_story_plan(self, user_request: str) -> dict:
        plan_prompt = load_prompt("story_planner")
        stage_config = settings.openai_pipeline_config.planner
        plan_result = await self.responses_client.create(
            plan_prompt,
            user_request,
            max_tokens=stage_config.max_tokens,
            temperature=stage_config.temperature,
        )

        plan = self.parse_json_response(
            plan_result,
            "Story planner returned invalid JSON.",
        )

        missing_fields = STORY_PLAN_FIELDS - set(plan)
        if missing_fields:
            logger.warning("Story planner missing fields: %s", sorted(missing_fields))
            raise ValueError("Story planner returned incomplete JSON.")

        return plan

    async def build_story(
        self,
        plan: dict,
        feedback: dict | None = None,
        story: dict | None = None,
    ) -> dict:
        writer_prompt = load_prompt("story_builder")
        stage_config = settings.openai_pipeline_config.story_builder
        builder_input = {
            "user_request": plan,
            "story": story,
            "feedback": feedback or self.empty_feedback(),
        }
        story_result = await self.responses_client.create(
            writer_prompt,
            json.dumps(builder_input),
            max_tokens=stage_config.max_tokens,
            temperature=stage_config.temperature,
        )

        story = self.parse_json_response(
            story_result,
            "Story builder returned invalid JSON.",
        )

        missing_fields = STORY_FIELDS - set(story)
        if missing_fields:
            logger.warning("Story builder missing fields: %s", sorted(missing_fields))
            raise ValueError("Story builder returned incomplete JSON.")

        return story

    def empty_feedback(self) -> dict:
        return {
            "score": None,
            "to_update": [],
            "recommendations": "",
        }

    def form_final_story(self, draft: dict) -> str:
        return (
            f"{draft['title']}\n\n"
            f"{draft['introduction']}\n\n"
            f"{draft['plot']}\n\n"
            f"{draft['conclusion']}\n\n"
            f"Moral: {draft['moral']}"
        )

    async def judge_story(self, plan: dict, draft: dict) -> dict:
        judge_prompt = load_prompt("story_judge")
        stage_config = settings.openai_pipeline_config.story_judge
        judge_input = {
            "user_request": plan,
            "story": draft,
        }
        judge_result = await self.responses_client.create(
            judge_prompt,
            json.dumps(judge_input),
            max_tokens=stage_config.max_tokens,
            temperature=stage_config.temperature,
        )

        judge_response = self.parse_json_response(
            judge_result,
            "Story judge returned invalid JSON.",
        )

        feedback = judge_response.get("feedback")
        if not isinstance(feedback, dict):
            raise ValueError("Story judge returned missing feedback.")

        missing_fields = FEEDBACK_FIELDS - set(feedback)
        if missing_fields:
            logger.warning("Story judge feedback missing fields: %s", sorted(missing_fields))
            raise ValueError("Story judge returned incomplete feedback.")

        return judge_response

    def get_feedback_score(self, feedback: dict) -> float:
        score = feedback.get("score")

        try:
            return float(score)
        except (TypeError, ValueError) as exc:
            raise ValueError("Story judge returned invalid feedback score.") from exc

    def parse_json_response(self, raw_response: str, error_message: str) -> dict:
        cleaned_response = raw_response.strip()
        logger.debug("Parsing JSON response with raw_chars=%s.", len(raw_response))

        if cleaned_response.startswith("```"):
            logger.info("Detected fenced JSON response; stripping markdown fence.")
            lines = cleaned_response.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned_response = "\n".join(lines).strip()

        try:
            parsed_response = json.loads(cleaned_response)
        except json.JSONDecodeError as exc:
            logger.warning("%s raw_preview=%r", error_message, raw_response[:300])
            raise ValueError(error_message) from exc

        if not isinstance(parsed_response, dict):
            logger.warning("%s Parsed response type=%s.", error_message, type(parsed_response).__name__)
            raise ValueError(error_message)

        return parsed_response
