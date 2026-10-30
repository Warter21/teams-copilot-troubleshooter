from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from teams_copilot_troubleshooter.config import (  # noqa: E402
    EMBEDDING_MODEL,
    LLM_BACKEND as DEFAULT_LLM_BACKEND,
    MODEL_NAME as DEFAULT_MODEL_NAME,
)
from teams_copilot_troubleshooter.graph import get_assistant  # noqa: E402
from teams_copilot_troubleshooter.llm import (  # noqa: E402
    ollama_model_status,
    pull_ollama_model,
)


st.set_page_config(
    page_title="Teams Copilot Troubleshooter",
    page_icon="🧭",
    layout="wide",
)

st.title("Teams Copilot Troubleshooter")
st.caption(
    "A source-grounded prototype for meeting Copilot/Recap, Facilitator, and Interpreter."
)
st.info(
    "This assistant uses public Microsoft documentation and user-provided details. "
    "It cannot inspect your tenant, license, meeting policy, or device."
)

MODEL_OPTIONS = {
    "Dummy — deterministic, no LLM": {
        "backend": "mock",
        "model_name": "dummy",
        "embedding_backend": "hash",
        "description": "Runs without Ollama or model downloads. Useful for checking the workflow, not answer-model quality.",
    },
    "Small — Qwen3 0.6B": {
        "backend": "ollama",
        "model_name": "qwen3:0.6b",
        "embedding_backend": "fastembed",
        "description": "Recommended for the 8 GB CPU-only setup. Usually slower than dummy mode.",
    },
    "Large — Qwen3 1.7B": {
        "backend": "ollama",
        "model_name": "qwen3:1.7b",
        "embedding_backend": "fastembed",
        "description": "Experimental on CPU. A previous run on this setup exceeded the 300-second timeout.",
    },
}


def _default_model_choice() -> str:
    if DEFAULT_LLM_BACKEND == "mock":
        return "Dummy — deterministic, no LLM"
    if DEFAULT_MODEL_NAME == "qwen3:1.7b":
        return "Large — Qwen3 1.7B"
    return "Small — Qwen3 0.6B"

with st.sidebar:
    st.subheader("Runtime")
    selected_model = st.selectbox(
        "Answer model",
        options=list(MODEL_OPTIONS),
        index=list(MODEL_OPTIONS).index(_default_model_choice()),
        key="answer_model_choice",
    )
    model_config = MODEL_OPTIONS[selected_model]
    llm_backend = model_config["backend"]
    model_name = model_config["model_name"]
    embedding_backend = model_config["embedding_backend"]
    st.caption(model_config["description"])
    if embedding_backend == "fastembed":
        st.write(f"Embeddings: FastEmbed · `{EMBEDDING_MODEL}`")
    else:
        st.write("Embeddings: deterministic hash vectors")
    if llm_backend == "ollama":
        ready, reachable, message = ollama_model_status(model_name)
        if ready:
            st.success(message)
        elif reachable:
            st.warning(message)

            def update_download_progress(event: dict) -> None:
                status_text = event.get("status", "Downloading")
                total = event.get("total")
                completed = event.get("completed", 0)
                if isinstance(total, (int, float)) and total > 0:
                    fraction = min(max(completed / total, 0.0), 1.0)
                    percent = int(fraction * 100)
                    download_progress.progress(
                        fraction,
                        text=f"{status_text}: {percent}%",
                    )
                else:
                    download_status.caption(status_text)

            if st.button(
                f"Download {model_name}",
                key=f"download_{model_name}",
                use_container_width=True,
            ):
                download_progress = st.progress(0.0, text="Starting download…")
                download_status = st.empty()
                try:
                    pull_ollama_model(model_name, update_download_progress)
                except Exception as exc:
                    st.error(f"Model download failed: {exc}")
                else:
                    st.success(f"{model_name} downloaded successfully.")
                    st.rerun()

            with st.expander("Manual download command"):
                st.code(f"ollama pull {model_name}", language="bash")
                st.caption(
                    "For Docker Compose: "
                    f"docker compose exec ollama ollama pull {model_name}"
                )
        else:
            st.error(message)
            st.caption("Start the Ollama service before downloading or using this model.")
    st.divider()
    st.subheader("Try a question")
    examples = [
        "Can Facilitator be added to a channel meeting?",
        "Why can't I ask Copilot about a meeting after it ended?",
        "Does Interpreter work in a Teams webinar?",
        "Can a Hungarian question find the English Microsoft guidance for Interpreter?",
    ]
    for example in examples:
        if st.button(example, use_container_width=True):
            st.session_state["pending_question"] = example
    if st.button("Clear conversation", use_container_width=True):
        st.session_state["history"] = []
        st.session_state.pop("pending_question", None)
        st.rerun()

if "history" not in st.session_state:
    st.session_state.history = []


def render_entry(entry: dict) -> None:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])
        if entry["role"] != "assistant":
            return
        if entry.get("model_label"):
            st.caption(f"Selected model: {entry['model_label']}")
        if entry.get("answer_method"):
            method_label = entry["answer_method"].replace("_", " ").title()
            st.caption(f"Response method: {method_label}")
        if entry.get("generation_truncated") and entry.get("answer_fallback_used"):
            st.info(
                "The local model reached its output limit. A complete answer based on "
                "the retrieved evidence is shown instead."
            )
        elif entry.get("answer_truncated"):
            st.warning(
                "The final answer may be incomplete. Please check the cited Microsoft sources."
            )
        evidence = entry.get("evidence", [])
        diagnostics = entry.get("diagnostics", [])
        trace = entry.get("trace", [])
        if diagnostics:
            with st.expander("Diagnostic checks"):
                for item in diagnostics:
                    st.markdown(f"- **{item['status'].replace('_', ' ').title()}:** {item['message']}")
        if evidence:
            with st.expander(f"Microsoft sources ({len(evidence)})"):
                for item in evidence:
                    citation = item.get("citation_id", "")
                    title = item.get("title", "Microsoft documentation")
                    url = item.get("source_url", "")
                    section = item.get("section", "")
                    st.markdown(f"**[{citation}] [{title}]({url})**  \n{section}")
        if trace:
            with st.expander("Workflow trace"):
                for item in sorted(trace, key=lambda value: value.get("node", "")):
                    st.markdown(
                        f"- **{item.get('node', 'Step')}** — "
                        f"{item.get('status', 'complete')}: {item.get('detail', '')} "
                        f"({item.get('elapsed_ms', 0)} ms)"
                    )


for previous in st.session_state.history:
    render_entry(previous)

prompt = st.chat_input("Describe the Teams meeting Copilot issue")
if not prompt:
    prompt = st.session_state.pop("pending_question", None)

if prompt:
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    try:
        with st.status("Checking the issue against the local Microsoft documentation index…", expanded=True) as status:
            assistant = get_assistant(
                embedding_backend=embedding_backend,
                llm_backend=llm_backend,
                model_name=model_name,
            )
            result = assistant.invoke(
                {
                    "query": prompt,
                    "retry_count": 0,
                    "force_broad": False,
                    "trace": [],
                    "timings_ms": {},
                }
            )
            status.update(label="Troubleshooting complete", state="complete", expanded=False)
        entry = {
            "role": "assistant",
            "content": result.get("answer", "No answer was produced."),
            "evidence": result.get("evidence", []),
            "diagnostics": result.get("diagnostics", []),
            "trace": result.get("trace", []),
            "answer_truncated": result.get("answer_truncated", False),
            "generation_truncated": result.get("generation_truncated", False),
            "answer_fallback_used": result.get("answer_fallback_used", False),
            "answer_method": result.get("answer_method", ""),
            "generation_done_reason": result.get("generation_done_reason", "unknown"),
            "model_label": selected_model,
        }
    except Exception as exc:
        entry = {
            "role": "assistant",
            "content": (
                "The local assistant could not complete this request. "
                f"Check the model and embedding setup, then try again. Details: {exc}"
            ),
            "evidence": [],
            "diagnostics": [],
            "trace": [],
            "model_label": selected_model,
        }
    st.session_state.history.append(entry)
    render_entry(entry)
