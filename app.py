import re
import streamlit as st

from openrouter_client import (
    chat_completion,
    estimate_cost,
    get_api_key,
    get_model_pricing,
    DEFAULT_MODEL,
)
from prompts import PROMPT_STRATEGIES, QUESTION_INSTRUCTION, EVALUATION_INSTRUCTION, CRITIQUE_INSTRUCTION
from security import validate_user_input, enforce_rate_limit

st.set_page_config(
    page_title="AI Solutions Architect Interview Coach",
    page_icon="🎯",
    layout="wide",
)

CUSTOM_CSS = """
<style>
html, body, [class*="css"] {
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}

/* Hide the top-right Deploy button / "..." menu toolbar */
[data-testid="stToolbar"] {
    display: none !important;
}

/* Pull the main content (and the header banner) up now that the
   toolbar's reserved space is gone */
[data-testid="stMainBlockContainer"] {
    padding-top: 1.5rem !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #171b3d 0%, #10132b 100%);
}
[data-testid="stSidebar"] * {
    color: #e6e8f5 !important;
}
[data-testid="stSidebarUserContent"] {
    padding-top: 1.25rem;
}

/* Sidebar select fields: darker field so the light text stays visible.
   This Streamlit version renders selects as react-aria components (no
   data-baseweb attribute) — the closed field is the [role="group"] wrapper
   around the input + open button inside [data-testid="stSelectbox"]. */
[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"] {
    background-color: #232849 !important;
    border: 1px solid #3a3f6b !important;
    border-radius: 12px !important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] input {
    color: #e6e8f5 !important;
    background-color: transparent !important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] svg {
    fill: #e6e8f5 !important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"]:focus-within {
    border-color: #7c80f5 !important;
    box-shadow: 0 0 0 3px rgba(124, 128, 245, 0.25);
}

/* Header banner */
.app-banner {
    background: linear-gradient(90deg, #0f2f66 0%, #0e8f8a 100%);
    border-radius: 14px;
    overflow: hidden;
    padding: 26px 32px;
    color: white;
    margin-bottom: 1.4rem;
    box-shadow: 0 8px 24px rgba(15, 47, 102, 0.25);
}
.app-banner h1 {
    margin: 0;
    font-size: 1.7rem;
    color: white;
    display: flex;
    align-items: center;
    gap: 12px;
    line-height: 1;
}
.app-banner h1 .icon {
    font-size: 1.5em;
    line-height: 1;
}
.app-banner p {
    margin: 6px 0 0 0;
    color: #d6f5f2;
    font-size: 0.95rem;
}

/* Cards */
.app-card {
    background: white;
    border-radius: 12px;
    padding: 18px 22px;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
    border: 1px solid rgba(15,23,42,0.06);
    color: #1c2333;
}
.app-card h4 {
    margin: 0 0 10px 0;
    color: #1c2333;
}
.app-card ul.checklist {
    margin: 0;
    padding-left: 20px;
}
.app-card ul.checklist li {
    margin-bottom: 8px;
    line-height: 1.4;
}

/* Buttons */
.stButton>button {
    border-radius: 10px;
    font-weight: 600;
}
.stButton>button[kind="primary"] {
    background: linear-gradient(90deg, #5b5fef, #4145c9);
    border: none;
}

/* Tabs styled as a nav-link menu */
.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    border-bottom: none;
}
.stTabs [data-baseweb="tab-highlight"] {
    display: none;
}
.stTabs [data-baseweb="tab"] {
    background-color: #eceefb;
    border-radius: 10px;
    padding: 10px 22px;
    border: 1px solid #d7dafa;
    transition: background-color 0.15s ease, color 0.15s ease, box-shadow 0.15s ease, transform 0.1s ease;
}
.stTabs [data-baseweb="tab"] p {
    color: #33359e !important;
    font-weight: 600;
    font-size: 1rem;
}
.stTabs [data-baseweb="tab"]:hover {
    background-color: #d7dafa;
    border-color: #5b5fef;
    cursor: pointer;
    transform: translateY(-1px);
}
.stTabs [data-baseweb="tab"]:hover p {
    color: #262a8c !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, #5b5fef, #4145c9) !important;
    border-color: transparent !important;
    box-shadow: 0 4px 14px rgba(91, 95, 239, 0.35);
}
.stTabs [aria-selected="true"] p {
    color: #ffffff !important;
}
.stTabs [aria-selected="true"]:hover {
    background: linear-gradient(90deg, #4a4ee0, #363ab8) !important;
    transform: translateY(-1px);
}
.stTabs [aria-selected="true"]:hover p {
    color: #ffffff !important;
}

/* Score badges */
.score-badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 14px;
}
.score-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.95rem;
    color: white;
    white-space: nowrap;
}
.score-good { background: linear-gradient(90deg,#16a34a,#15803d); }
.score-fair { background: linear-gradient(90deg,#f59e0b,#d97706); }
.score-poor { background: linear-gradient(90deg,#ef4444,#dc2626); }
.score-unknown { background: #64748b; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

MODELS = [
    "openai/gpt-5-mini",
    "openai/gpt-5-nano",
    "openai/gpt-5",
]

FOCUS_AREAS = [
    "End-to-end AI solution architecture",
    "RAG and enterprise knowledge systems",
    "AI agents and tool use",
    "LLMOps, evaluation, and observability",
    "Cloud architecture and integration",
    "Security, privacy, and responsible AI",
    "Performance, reliability, and cost",
    "Stakeholder discovery and solution consulting",
]

DIFFICULTIES = ["Beginner", "Intermediate", "Senior", "Principal"]

MAX_FOLLOWUPS = 4

CHECKLIST_ITEMS = [
    "Clarify goals, users, constraints, and success metrics",
    "State key assumptions",
    "Describe the architecture end to end",
    "Explain model/provider choice",
    "Cover data flow and RAG where relevant",
    "Include evaluation and observability",
    "Address security, privacy, and governance",
    "Discuss scale, latency, reliability, and cost",
    "Name important trade-offs and alternatives",
    "Tie the design back to business outcomes",
]

if "question" not in st.session_state:
    st.session_state.question = ""
if "last_feedback" not in st.session_state:
    st.session_state.last_feedback = ""
if "last_scores" not in st.session_state:
    st.session_state.last_scores = {}
if "question_cost" not in st.session_state:
    st.session_state.question_cost = None
if "last_cost" not in st.session_state:
    st.session_state.last_cost = None
if "followup_question" not in st.session_state:
    st.session_state.followup_question = None
if "followup_history" not in st.session_state:
    st.session_state.followup_history = []


def api_key_or_stop():
    key = get_api_key(st)
    if not key:
        st.error(
            "No OpenRouter API key found. Add OPENROUTER_API_KEY to "
            ".streamlit/secrets.toml or your environment, then restart the app."
        )
        st.stop()
    return key


@st.cache_data(ttl=3600, show_spinner=False)
def cached_model_pricing(model):
    try:
        return get_model_pricing(model)
    except Exception:
        return None


def safe_model_call(system_prompt, user_prompt, model, max_tokens=1200, temperature=0.4, reasoning_effort="low"):
    allowed, message = enforce_rate_limit(st.session_state)
    if not allowed:
        st.error(message)
        return None
    try:
        result = chat_completion(
            api_key=api_key_or_stop(),
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            reasoning_effort=reasoning_effort,
        )
        pricing = cached_model_pricing(model)
        if pricing:
            cost = estimate_cost(result.get("usage", {}), pricing)
            result["cost"] = cost
            st.session_state.session_cost = st.session_state.get("session_cost", 0.0) + cost
        else:
            result["cost"] = None
        return result
    except Exception as exc:
        st.error(f"Model call failed: {exc}")
        return None


def extract_score(text):
    match = re.search(r"OVERALL_SCORE:\s*(10|[1-9])", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def extract_all_scores(text):
    matches = re.findall(r"([A-Z_]+_SCORE):\s*(10|[1-9])", text, flags=re.IGNORECASE)
    return {label.upper(): int(value) for label, value in matches}


def extract_follow_up(text):
    """Pull the FOLLOW_UP section from an evaluation. Returns None if the
    model signaled no further probing is needed (a missing or "NONE" section)."""
    match = re.search(r"FOLLOW_UP:\s*(.*)", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    follow_up = match.group(1).strip()
    if not follow_up or follow_up.upper().startswith("NONE"):
        return None
    return follow_up


def score_label(key):
    return key.replace("_SCORE", "").replace("_", " ").title()


def score_tier(score):
    if score is None:
        return "score-unknown", "❔", "Not parsed"
    if score >= 8:
        return "score-good", "✅", "Strong"
    if score >= 5:
        return "score-fair", "⚠️", "Fair"
    return "score-poor", "❌", "Needs work"


def score_badge_html(label, score):
    css_class, icon, tier = score_tier(score)
    score_text = f"{score}/10" if score is not None else "N/A"
    return f'<div class="score-badge {css_class}">{icon} {label}: {score_text} — {tier}</div>'


def score_dot(score):
    _, icon, _ = score_tier(score)
    return icon


def warn_empty_response(action: str):
    st.error(
        f"Received empty response from the model when {action}. Reasoning models "
        "can spend their whole token budget on hidden reasoning and leave nothing "
        "for the actual answer. Try lowering 'Reasoning effort' to Low in the "
        "sidebar, or click the button again."
    )


def render_score_badges(scores):
    if not scores:
        return
    badges_html = "".join(score_badge_html(score_label(k), v) for k, v in scores.items())
    st.markdown(f'<div class="score-badge-row">{badges_html}</div>', unsafe_allow_html=True)


def cost_caption_text(result):
    if not result:
        return None
    usage = result.get("usage") or {}
    prompt_tokens = usage.get("prompt_tokens") or 0
    completion_tokens = usage.get("completion_tokens") or 0
    cost = result.get("cost")
    if cost is not None:
        return f"💲 Estimated cost: ${cost:.6f} ({prompt_tokens} prompt + {completion_tokens} completion tokens)"
    if prompt_tokens or completion_tokens:
        return f"Tokens used: {prompt_tokens} prompt + {completion_tokens} completion (pricing unavailable)"
    return None


st.markdown(
    '<div class="app-banner">'
    '<h1><span class="icon">🎯</span> AI Solutions Architect Interview Coach</h1>'
    '<p>Practice architecture interviews, receive structured feedback, and compare prompt-engineering strategies.</p>'
    '</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Interview setup")
    selected_model = st.selectbox("OpenRouter model", MODELS, index=0)
    focus = st.selectbox("Focus area", FOCUS_AREAS)
    difficulty = st.selectbox("Difficulty", DIFFICULTIES, index=2)
    strategy_name = st.selectbox(
        "Prompt strategy",
        list(PROMPT_STRATEGIES.keys()),
        index=2,
    )
    temperature = st.slider(
        "Response temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.4,
        step=0.05,
        help=(
            "Controls randomness in the model's output. Lower values (near 0) give "
            "consistent, deterministic questions and feedback. Higher values (near 1) "
            "give more varied, exploratory phrasing — useful for generating a wider "
            "range of interview questions, but less repeatable scoring."
        ),
    )
    reasoning_effort = st.selectbox(
        "Reasoning effort",
        ["low", "medium", "high"],
        index=0,
        help=(
            "How much internal 'thinking' reasoning-capable models (like the gpt-5 "
            "family) do before answering. Higher effort can improve answer quality "
            "but uses more of the token budget on hidden reasoning — if it's set too "
            "high relative to max tokens, the model can run out of room and return "
            "an empty response. 'low' leaves the most room for actual output."
        ),
    )
    st.divider()
    session_cost_slot = st.empty()
    st.caption(
        "Security: input-length limits, prompt-injection/secret detection, "
        "and a per-session API rate limit are enabled."
    )

practice_tab, lab_tab, temp_tab, prompts_tab = st.tabs(
    ["🎤 Practice", "🧪 Prompt Lab", "🌡️ Temperature Lab", "📚 Prompt Techniques"]
)

with practice_tab:
    left, right = st.columns([2, 1])

    with left:
        if st.button("Generate interview question", type="primary", use_container_width=True):
            prompt = QUESTION_INSTRUCTION.format(
                focus=focus,
                difficulty=difficulty,
            )
            result = safe_model_call(
                PROMPT_STRATEGIES[strategy_name],
                prompt,
                selected_model,
                max_tokens=800,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
            )
            if result:
                content = result.get("content")
                if content:
                    st.session_state.question = content.strip()
                    st.session_state.question_cost = result.get("cost")
                    st.session_state.last_feedback = ""
                    st.session_state.last_scores = {}
                    st.session_state.last_cost = None
                    st.session_state.followup_history = []
                    st.session_state.followup_question = None
                else:
                    warn_empty_response("generating a question")

        if st.session_state.question:
            st.subheader("Interview question")
            st.info(st.session_state.question)
            if st.session_state.question_cost is not None:
                st.caption(f"💲 Estimated cost to generate this question: ${st.session_state.question_cost:.6f}")

            answer = st.text_area(
                "Your answer",
                height=260,
                placeholder=(
                    "Answer as if you were speaking to the interviewer. "
                    "State assumptions, architecture, trade-offs, security, "
                    "evaluation, reliability, and cost where relevant."
                ),
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Evaluate my answer", use_container_width=True):
                    valid, message = validate_user_input(answer)
                    if not valid:
                        st.warning(message)
                    else:
                        evaluation_prompt = EVALUATION_INSTRUCTION.format(
                            question=st.session_state.question,
                            answer=answer,
                        )
                        result = safe_model_call(
                            PROMPT_STRATEGIES[strategy_name],
                            evaluation_prompt,
                            selected_model,
                            max_tokens=1500,
                            temperature=temperature,
                            reasoning_effort=reasoning_effort,
                        )
                        if result:
                            feedback = result.get("content")
                            if feedback:
                                st.session_state.last_feedback = feedback
                                st.session_state.last_scores = extract_all_scores(feedback)
                                st.session_state.last_cost = result.get("cost")
                                st.session_state.followup_history = []
                                st.session_state.followup_question = extract_follow_up(feedback)
                            else:
                                warn_empty_response("evaluating your answer")

            with col2:
                if st.button("Get AI Critique", use_container_width=True):
                    valid, message = validate_user_input(answer)
                    if not valid:
                        st.warning(message)
                    else:
                        critique_prompt = CRITIQUE_INSTRUCTION.format(
                            question=st.session_state.question,
                            answer=answer,
                        )
                        result = safe_model_call(
                            PROMPT_STRATEGIES[strategy_name],
                            critique_prompt,
                            selected_model,
                            max_tokens=2000,
                            temperature=temperature,
                            reasoning_effort=reasoning_effort,
                        )
                        if result:
                            critique = result.get("content")
                            if critique:
                                st.session_state.last_feedback = critique
                                st.session_state.last_scores = extract_all_scores(critique)
                                st.session_state.last_cost = result.get("cost")
                                st.session_state.followup_history = []
                                st.session_state.followup_question = None
                            else:
                                warn_empty_response("generating critique")

            if st.session_state.last_feedback:
                st.subheader("Feedback")
                render_score_badges(st.session_state.last_scores)
                if st.session_state.last_cost is not None:
                    st.caption(f"💲 Estimated cost of this response: ${st.session_state.last_cost:.6f}")
                st.markdown(st.session_state.last_feedback)

                for idx, round_data in enumerate(st.session_state.followup_history, start=1):
                    st.divider()
                    st.subheader(f"Follow-up {idx}")
                    st.info(round_data["question"])
                    st.markdown(f"**Your answer:** {round_data['answer']}")
                    render_score_badges(round_data["scores"])
                    if round_data.get("cost") is not None:
                        st.caption(f"💲 Estimated cost: ${round_data['cost']:.6f}")
                    st.markdown(round_data["feedback"])

                if st.session_state.followup_question:
                    st.divider()
                    round_num = len(st.session_state.followup_history) + 1
                    st.subheader(f"Follow-up {round_num}")
                    st.info(st.session_state.followup_question)
                    followup_answer = st.text_area(
                        "Your follow-up answer",
                        height=180,
                        key=f"followup_answer_{round_num}",
                        placeholder="Answer the interviewer's follow-up question.",
                    )
                    if st.button("Submit follow-up answer", key=f"followup_submit_{round_num}"):
                        valid, message = validate_user_input(followup_answer)
                        if not valid:
                            st.warning(message)
                        else:
                            followup_prompt = EVALUATION_INSTRUCTION.format(
                                question=st.session_state.followup_question,
                                answer=followup_answer,
                            )
                            result = safe_model_call(
                                PROMPT_STRATEGIES[strategy_name],
                                followup_prompt,
                                selected_model,
                                max_tokens=1500,
                                temperature=temperature,
                                reasoning_effort=reasoning_effort,
                            )
                            if result:
                                followup_feedback = result.get("content")
                                if followup_feedback:
                                    st.session_state.followup_history.append(
                                        {
                                            "question": st.session_state.followup_question,
                                            "answer": followup_answer,
                                            "feedback": followup_feedback,
                                            "scores": extract_all_scores(followup_feedback),
                                            "cost": result.get("cost"),
                                        }
                                    )
                                    if len(st.session_state.followup_history) >= MAX_FOLLOWUPS:
                                        st.session_state.followup_question = None
                                    else:
                                        st.session_state.followup_question = extract_follow_up(followup_feedback)
                                    st.rerun()
                                else:
                                    warn_empty_response("evaluating your follow-up answer")
                elif st.session_state.followup_history:
                    st.divider()
                    st.success("No more follow-up questions — this line of questioning is complete.")
        else:
            st.info("Choose your settings and generate your first question.")

    with right:
        checklist_items = "".join(f"<li>{item}</li>" for item in CHECKLIST_ITEMS)
        st.markdown(
            f'<div class="app-card"><h4>Strong-answer checklist</h4>'
            f'<ul class="checklist">{checklist_items}</ul></div>',
            unsafe_allow_html=True,
        )

with lab_tab:
    st.subheader("Compare all 5 prompt strategies")
    st.write(
        "Run the same candidate answer through every system-prompt technique and "
        "compare the resulting scores and feedback."
    )

    lab_question = st.text_area(
        "Question to test",
        value=(
            "Design an enterprise RAG assistant for 20,000 employees using confidential "
            "internal documents. Explain the architecture and how you would evaluate it."
        ),
        height=100,
        key="lab_question",
    )
    lab_answer = st.text_area(
        "Candidate answer to test",
        height=220,
        key="lab_answer",
        placeholder="Paste one answer here so each prompt strategy evaluates the same input.",
    )

    if st.button("Run prompt comparison", type="primary"):
        valid_q, msg_q = validate_user_input(lab_question)
        valid_a, msg_a = validate_user_input(lab_answer)

        if not valid_q:
            st.warning(msg_q)
        elif not valid_a:
            st.warning(msg_a)
        else:
            results = []
            eval_prompt = EVALUATION_INSTRUCTION.format(
                question=lab_question,
                answer=lab_answer,
            )

            progress = st.progress(0, text="Comparing prompt strategies...")
            for idx, (name, system_prompt) in enumerate(PROMPT_STRATEGIES.items(), start=1):
                result = safe_model_call(
                    system_prompt,
                    eval_prompt,
                    selected_model,
                    max_tokens=1200,
                    temperature=0.2,
                    reasoning_effort=reasoning_effort,
                )
                if result:
                    feedback = result.get("content")
                    if feedback:
                        score = extract_score(feedback)
                        results.append(
                            {
                                "strategy": name,
                                "score": score,
                                "feedback": feedback,
                                "cost": result.get("cost"),
                            }
                        )
                    else:
                        results.append(
                            {
                                "strategy": name,
                                "score": None,
                                "feedback": "(empty response from model)",
                                "cost": result.get("cost"),
                            }
                        )
                progress.progress(
                    idx / len(PROMPT_STRATEGIES),
                    text=f"Completed {idx}/{len(PROMPT_STRATEGIES)} strategies",
                )

            progress.empty()

            scored = [r for r in results if r["score"] is not None]
            if scored:
                best = max(scored, key=lambda r: r["score"])
                st.markdown(
                    score_badge_html(f"Best: {best['strategy']}", best["score"]),
                    unsafe_allow_html=True,
                )
                st.caption(
                    "This is a practical comparison, not a scientific benchmark. "
                    "Repeat with several questions before choosing a final prompt."
                )

            total_lab_cost = sum(r["cost"] for r in results if r.get("cost") is not None)
            if total_lab_cost:
                st.caption(f"💲 Total estimated cost for this comparison: ${total_lab_cost:.6f}")

            for row in results:
                score_text = f"{row['score']}/10" if row["score"] else "Not parsed"
                with st.expander(f"{score_dot(row['score'])} {row['strategy']} — {score_text}"):
                    st.markdown(
                        score_badge_html("Score", row["score"]),
                        unsafe_allow_html=True,
                    )
                    if row.get("cost") is not None:
                        st.caption(f"💲 Estimated cost: ${row['cost']:.6f}")
                    st.markdown(row["feedback"])

with temp_tab:
    st.subheader("Compare temperature settings")
    st.write(
        "Run the identical evaluation prompt at several temperature values, using the "
        "model and prompt strategy selected in the sidebar, to see how this setting "
        "changes the feedback and score."
    )
    st.caption(
        "Temperature controls randomness: lower values push the model toward the same, "
        "most-likely answer every time; higher values let it sample more freely, so "
        "wording — and sometimes the score — varies run to run."
    )

    temp_question = st.text_area(
        "Question to test",
        value=(
            "Design an enterprise RAG assistant for 20,000 employees using confidential "
            "internal documents. Explain the architecture and how you would evaluate it."
        ),
        height=100,
        key="temp_question",
    )
    temp_answer = st.text_area(
        "Candidate answer to test",
        height=220,
        key="temp_answer",
        placeholder="Paste one answer here so each temperature evaluates the same input.",
    )
    temp_values = st.multiselect(
        "Temperatures to compare",
        [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        default=[0.0, 0.4, 1.0],
    )

    if st.button("Run temperature comparison", type="primary"):
        valid_q, msg_q = validate_user_input(temp_question)
        valid_a, msg_a = validate_user_input(temp_answer)

        if not valid_q:
            st.warning(msg_q)
        elif not valid_a:
            st.warning(msg_a)
        elif not temp_values:
            st.warning("Select at least one temperature to compare.")
        else:
            temp_eval_prompt = EVALUATION_INSTRUCTION.format(
                question=temp_question,
                answer=temp_answer,
            )
            temp_results = []
            sorted_temps = sorted(temp_values)

            progress = st.progress(0, text="Comparing temperatures...")
            for idx, temp_value in enumerate(sorted_temps, start=1):
                result = safe_model_call(
                    PROMPT_STRATEGIES[strategy_name],
                    temp_eval_prompt,
                    selected_model,
                    max_tokens=1200,
                    temperature=temp_value,
                    reasoning_effort=reasoning_effort,
                )
                if result:
                    feedback = result.get("content")
                    if feedback:
                        temp_results.append(
                            {
                                "temperature": temp_value,
                                "score": extract_score(feedback),
                                "feedback": feedback,
                                "cost": result.get("cost"),
                            }
                        )
                    else:
                        temp_results.append(
                            {
                                "temperature": temp_value,
                                "score": None,
                                "feedback": "(empty response from model)",
                                "cost": result.get("cost"),
                            }
                        )
                progress.progress(
                    idx / len(sorted_temps),
                    text=f"Completed {idx}/{len(sorted_temps)} temperatures",
                )

            progress.empty()

            if temp_results:
                quick_badges = "".join(
                    score_badge_html(f"T={row['temperature']}", row["score"])
                    for row in temp_results
                )
                st.markdown(f'<div class="score-badge-row">{quick_badges}</div>', unsafe_allow_html=True)

            total_temp_cost = sum(r["cost"] for r in temp_results if r.get("cost") is not None)
            if total_temp_cost:
                st.caption(f"💲 Total estimated cost for this comparison: ${total_temp_cost:.6f}")

            for row in temp_results:
                score_text = f"{row['score']}/10" if row["score"] else "Not parsed"
                with st.expander(f"{score_dot(row['score'])} Temperature {row['temperature']} — {score_text}"):
                    if row.get("cost") is not None:
                        st.caption(f"💲 Estimated cost: ${row['cost']:.6f}")
                    st.markdown(row["feedback"])

with prompts_tab:
    st.subheader("Five system-prompt techniques")
    st.write(
        "These satisfy the prompt-engineering requirement and let you test which "
        "approach works best for your interview style."
    )

    descriptions = {
        "1. Zero-Shot Expert Interviewer": "Zero-shot role + explicit evaluation criteria.",
        "2. Few-Shot Interviewer": "Few-shot examples demonstrate what strong answers and feedback should look like.",
        "3. Structured Reasoning Coach": "Chain-of-thought-inspired decomposition; internal reasoning only, concise final rationale.",
        "4. Socratic Adaptive Interviewer": "Socratic questioning that probes weak assumptions and adapts difficulty.",
        "5. Rubric + Self-Critique Interviewer": "Explicit scoring rubric plus a silent consistency/self-critique pass.",
    }

    for name, prompt in PROMPT_STRATEGIES.items():
        with st.expander(name):
            st.write(descriptions[name])
            st.code(prompt.strip(), language="text")

session_cost = st.session_state.get("session_cost", 0.0)
if session_cost:
    session_cost_slot.metric("Session cost so far", f"${session_cost:.6f}")

st.divider()
st.caption("Copyright Samuel Mugisha D.C. Design for Samuel Mugisha D.C.")
