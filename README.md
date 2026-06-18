# Sleepy Heads

## Problem Statement

Parents and caregivers often need quick, gentle, age-appropriate bedtime stories that can be revised through natural conversation. Sleepy Heads turns a user's request into a structured children's bedtime story, remembers follow-up instructions in the same session, and uses a judge feedback loop to improve the story before returning the final version.

## Solution

- The user can describe the kind of bedtime story they want in a chat-style experience.
- The app remembers follow-up messages, so the user can ask for changes without restating the whole story idea.
- Each request is checked to make sure it is appropriate for a children's bedtime story.
- The story idea is converted into a clear plan with mood, characters, theme, age, length, and lesson/moral.
- A story draft is created from the plan.
- The draft is reviewed for quality, age fit, structure, and alignment with the user's request.
- If the draft is not strong enough, it is revised using the feedback from a story judge.
- The final response is returned as a polished, readable bedtime story.
- Personas used: Input Validator, Story Planner, Story Builder, Story Judge

## Architecture Diagram

System highlights:

- Chat UI (React)
- Session management to accomodate request changes and feedback
- In-memory request store
- Story Pipeline: Orchestration as shown in diagram (Prompts/Personas for Input Validator, Story Planner, Story Builder, Story Judge)
- OpenAI Chat Completions API
- Per-stage OpenAI configuration for user input, instructions, max_tokens, temperature
- Final story formatter

## Future Enhancements

- Multi-agent orchestration: create individual agents for each task so they can be called independently, for example calling `story_judge` only to judge a given story input.
- Persistent sessions using Redis or a database instead of in-memory storage.
- Dedicated endpoint for judging or revising an externally provided story.
- Conversation reset and session management in the frontend.
- Stage-level observability dashboard for scores, retries, and token usage.

## Run Locally

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Start the backend:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
```

Start the frontend:

```bash
npm start
```

Access the running app at `http://localhost:3000`.

The frontend dev server proxies `/api` requests to the backend at `http://127.0.0.1:8000`.
