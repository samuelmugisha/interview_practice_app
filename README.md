# AI Solutions Architect Interview Coach

A Streamlit app for practicing AI Solutions Architect interviews using OpenRouter.

## What the app includes

- Streamlit front end with chat/interview-style workflow.
- OpenRouter integration.
- Default model: `openai/gpt-5-mini`.
- Optional model selector for:
  - `openai/gpt-5-mini`
  - `openai/gpt-5-nano`
  - `openai/gpt-5`
- Five prompt-engineering strategies:
  1. Zero-shot expert interviewer
  2. Few-shot interviewer
  3. Structured reasoning / Chain-of-Thought-inspired coach
  4. Socratic adaptive interviewer
  5. Rubric + self-critique interviewer
- Prompt Lab that runs the same answer through all five strategies and identifies
  the highest parsed score for that test.
- Security guards:
  - prompt-injection detection
  - API-key/private-key leakage detection
  - maximum input length
  - per-session request rate limiting
- API key is read server-side and is never entered into a normal chat field.

## 1. Create your OpenRouter API key

Sign in to OpenRouter and create an API key in your OpenRouter account/dashboard.

Do **not** commit the key to Git.

### Recommended: Streamlit secrets

Create this file:

`.streamlit/secrets.toml`

Add:

```toml
OPENROUTER_API_KEY = "your_key_here"
```

Or set an environment variable:

```bash
export OPENROUTER_API_KEY="your_key_here"
```

## 2. Install

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Run

```bash
streamlit run app.py
```

Then open the local URL Streamlit prints, normally `http://localhost:8501`.

## 4. How to evaluate the five prompts

Use the **Prompt Lab** tab.

1. Enter one interview question.
2. Enter the same candidate answer.
3. Click **Run prompt comparison**.
4. The app sends the identical evaluation task to all five system prompts.
5. Compare the scores and qualitative feedback.
6. Repeat across several interview questions before deciding which prompt is best.

A useful evaluation set should include:
- RAG architecture
- agent/tool-calling design
- security/privacy
- LLM evaluation
- cloud integration
- scaling/cost
- stakeholder discovery

The "best" prompt should be selected based on consistency, usefulness, realism, and
how much the feedback improves your answers—not only the numeric score.

## Security design

The app intentionally includes an application-layer security module. It blocks common
attempts to reveal system prompts or credentials, detects likely pasted API/private
keys, limits input size, and rate-limits calls within a Streamlit session.

These are basic guards for an assignment/demo. A production deployment should also use
authentication, server-side quotas, provider spend limits, logging/monitoring, secure
secret storage, dependency scanning, and stronger content-abuse controls.

## Notes on Chain-of-Thought

The structured-reasoning strategy asks the model to reason internally and return only
a concise final rationale. This demonstrates a reasoning-oriented prompt technique
without requesting or exposing private hidden reasoning traces.
