"""
Streamlit frontend for the EASA Propulsion Quiz.

Session-state machine:
    not_started → generating → in_progress → complete
                                    ↑______________|  (new quiz resets to generating)

Run with:
    streamlit run frontend/app.py
"""
import sys
from pathlib import Path

# Allow running from project root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from backend.config import QUESTIONS_PER_QUIZ
from backend.rag.retriever import is_knowledge_base_ready

# ── Page config (must be first Streamlit call) ─────────────────────────────
st.set_page_config(
    page_title="Quiz Propulsão EASA",
    page_icon="✈️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ---- Global ---- */
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }

    /* ---- Header ---- */
    .quiz-header {
        background: linear-gradient(135deg, #0d2137 0%, #1a3a5c 60%, #1e5f8e 100%);
        border-radius: 12px;
        padding: 2rem 2.5rem;
        color: white;
        margin-bottom: 1.5rem;
    }
    .quiz-header h1 { margin: 0; font-size: 2rem; font-weight: 700; }
    .quiz-header p  { margin: 0.4rem 0 0; opacity: 0.85; font-size: 1rem; }

    /* ---- Score badge ---- */
    .score-badge {
        background: #1e5f8e;
        color: white;
        border-radius: 20px;
        padding: 0.25rem 0.9rem;
        font-weight: 600;
        font-size: 0.95rem;
        display: inline-block;
    }

    /* ---- Question card ---- */
    .question-card {
        background: #f8fafc;
        border: 1px solid #dde4ec;
        border-radius: 10px;
        padding: 1.5rem 1.8rem;
        margin-bottom: 1.2rem;
        font-size: 1.05rem;
        font-weight: 500;
        color: #1a2535;
    }

    /* ---- Feedback boxes ---- */
    .feedback-correct {
        background: #eafaf0;
        border-left: 5px solid #28a745;
        border-radius: 6px;
        padding: 1rem 1.2rem;
        margin-top: 1rem;
        color: #1a4d2b;
    }
    .feedback-incorrect {
        background: #fff4f4;
        border-left: 5px solid #dc3545;
        border-radius: 6px;
        padding: 1rem 1.2rem;
        margin-top: 1rem;
        color: #6b1a1a;
    }

    /* ---- Result card ---- */
    .result-card {
        background: linear-gradient(135deg, #0d2137 0%, #1a3a5c 100%);
        border-radius: 12px;
        padding: 2.5rem;
        text-align: center;
        color: white;
        margin: 1rem 0;
    }
    .result-score { font-size: 4rem; font-weight: 700; margin: 0.3rem 0; }
    .result-label { font-size: 1.1rem; opacity: 0.85; }

    /* ---- Warning box ---- */
    .warn-box {
        background: #fff8e1;
        border-left: 5px solid #ffc107;
        border-radius: 6px;
        padding: 1rem 1.2rem;
        color: #5c4000;
        font-size: 0.95rem;
    }

    /* Hide Streamlit chrome elements we don't need */
    #MainMenu, footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── State initialisation ───────────────────────────────────────────────────
_DEFAULTS = {
    "quiz_state": "not_started",  # not_started | generating | in_progress | complete
    "questions": [],
    "current_idx": 0,
    "answers": {},            # {question_id: chosen_option_key}
    "submitted_current": False,
    "score": 0,
    "error_msg": "",
}
for key, val in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ── Helper functions ───────────────────────────────────────────────────────

def _reset_to_generating() -> None:
    st.session_state.quiz_state = "generating"
    st.session_state.questions = []
    st.session_state.current_idx = 0
    st.session_state.answers = {}
    st.session_state.submitted_current = False
    st.session_state.score = 0
    st.session_state.error_msg = ""


def _performance_message(score: int, total: int) -> str:
    ratio = score / total
    if ratio == 1.0:
        return "🏆 Excelente! Domínio completo do conteúdo EASA."
    if ratio >= 0.8:
        return "🎯 Ótimo desempenho! Você está muito bem preparado."
    if ratio >= 0.6:
        return "📚 Bom resultado. Revise os tópicos que errou para consolidar."
    if ratio >= 0.4:
        return "⚙️ Desempenho regular. Foque nos fundamentos de propulsão."
    return "🔧 Precisa revisar o material. Não desanime — continue estudando!"


# ── Page header (always visible) ──────────────────────────────────────────
st.markdown(
    f"""
    <div class="quiz-header">
        <h1>✈️ Quiz Propulsão EASA</h1>
        <p>Questões técnicas baseadas exclusivamente na documentação oficial EASA · {QUESTIONS_PER_QUIZ} questões por sessão</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Guard: check ChromaDB readiness ───────────────────────────────────────
if not is_knowledge_base_ready():
    st.markdown(
        """
        <div class="warn-box">
            <strong>⚠️ Base de conhecimento não encontrada.</strong><br>
            Execute o pipeline de ingestão antes de usar o quiz:<br><br>
            <code>python scripts/ingest.py</code>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# ══════════════════════════════════════════════════════════════════════════
# STATE: not_started
# ══════════════════════════════════════════════════════════════════════════
if st.session_state.quiz_state == "not_started":
    st.markdown("### Bem-vindo ao Quiz de Propulsão EASA")
    st.markdown(
        "Teste seus conhecimentos sobre ciclos termodinâmicos, compressores, turbinas, "
        "câmaras de combustão, desempenho de motores a jato e muito mais. "
        f"Cada sessão gera **{QUESTIONS_PER_QUIZ} questões únicas** baseadas no material oficial EASA."
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Gerar Quiz", use_container_width=True, type="primary"):
            _reset_to_generating()
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# STATE: generating
# ══════════════════════════════════════════════════════════════════════════
elif st.session_state.quiz_state == "generating":
    status_box = st.empty()
    status_box.info("⏳ Consultando a base EASA e gerando questões…")

    def _on_retry(attempt: int, max_retries: int, wait: int) -> None:
        status_box.warning(
            f"⚠️ API sobrecarregada. Aguardando {wait}s antes da "
            f"tentativa {attempt + 1} de {max_retries}…"
        )

    try:
        from backend.agent.quiz_agent import generate_quiz

        data = generate_quiz(on_retry=_on_retry)
        st.session_state.questions = data["questions"]
        st.session_state.quiz_state = "in_progress"
        st.session_state.error_msg = ""
    except TimeoutError:
        st.session_state.error_msg = (
            "Tempo limite excedido ao gerar questões. "
            "Verifique sua conexão e tente novamente."
        )
        st.session_state.quiz_state = "not_started"
    except Exception as exc:
        st.session_state.error_msg = f"Erro ao gerar quiz: {exc}"
        st.session_state.quiz_state = "not_started"

    status_box.empty()
    if st.session_state.error_msg:
        st.error(st.session_state.error_msg)
    else:
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# STATE: in_progress
# ══════════════════════════════════════════════════════════════════════════
elif st.session_state.quiz_state == "in_progress":
    questions = st.session_state.questions
    idx = st.session_state.current_idx
    total = len(questions)
    q = questions[idx]

    # ── Progress & score bar ──────────────────────────────────────────────
    col_prog, col_score = st.columns([3, 1])
    with col_prog:
        st.progress((idx) / total, text=f"Questão {idx + 1} de {total}")
    with col_score:
        st.markdown(
            f'<div class="score-badge">Acertos: {st.session_state.score}/{total}</div>',
            unsafe_allow_html=True,
        )

    # ── Question card ─────────────────────────────────────────────────────
    st.markdown(
        f'<div class="question-card">{idx + 1}. {q["question"]}</div>',
        unsafe_allow_html=True,
    )

    # ── Options ───────────────────────────────────────────────────────────
    options = q["options"]
    option_keys = list(options.keys())
    option_labels = [f"**{k}** — {v}" for k, v in options.items()]

    # Disable radio after answer is submitted
    selected_label = st.radio(
        "Selecione sua resposta:",
        options=option_labels,
        key=f"radio_{idx}",
        disabled=st.session_state.submitted_current,
    )
    selected_key = option_keys[option_labels.index(selected_label)] if selected_label else None

    # ── Submit button ─────────────────────────────────────────────────────
    if not st.session_state.submitted_current:
        if st.button("✅ Confirmar resposta", type="primary", disabled=selected_key is None):
            st.session_state.answers[q["id"]] = selected_key
            st.session_state.submitted_current = True

            if selected_key == q["correct_answer"]:
                st.session_state.score += 1

            st.rerun()

    # ── Feedback (shown after submission) ─────────────────────────────────
    if st.session_state.submitted_current:
        chosen = st.session_state.answers.get(q["id"])
        is_correct = chosen == q["correct_answer"]

        if is_correct:
            st.markdown(
                f'<div class="feedback-correct">'
                f'<strong>✓ Correto!</strong><br><br>{q["explanation"]}'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            correct_text = options[q["correct_answer"]]
            st.markdown(
                f'<div class="feedback-incorrect">'
                f'<strong>✗ Incorreto.</strong> A resposta correta é '
                f'<strong>{q["correct_answer"]}</strong>: {correct_text}<br><br>'
                f'{q["explanation"]}'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("")  # spacing

        # ── Navigation ────────────────────────────────────────────────────
        if idx + 1 < total:
            if st.button("➡️ Próxima questão", type="primary"):
                st.session_state.current_idx += 1
                st.session_state.submitted_current = False
                st.rerun()
        else:
            if st.button("📊 Ver resultado final", type="primary"):
                st.session_state.quiz_state = "complete"
                st.rerun()

    # ── Sidebar: question navigator ───────────────────────────────────────
    with st.sidebar:
        st.markdown("### Navegação")
        for i, _q in enumerate(questions):
            qid = _q["id"]
            if i < idx or (i == idx and st.session_state.submitted_current):
                chosen = st.session_state.answers.get(qid)
                icon = "✅" if chosen == _q["correct_answer"] else "❌"
            elif i == idx:
                icon = "➡️"
            else:
                icon = "⬜"
            st.markdown(f"{icon} Questão {i + 1}")


# ══════════════════════════════════════════════════════════════════════════
# STATE: complete
# ══════════════════════════════════════════════════════════════════════════
elif st.session_state.quiz_state == "complete":
    score = st.session_state.score
    total = len(st.session_state.questions)
    pct = int(score / total * 100)

    st.markdown(
        f"""
        <div class="result-card">
            <div class="result-label">Sua pontuação final</div>
            <div class="result-score">{score}/{total}</div>
            <div class="result-label">{pct}% de aproveitamento</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f"#### {_performance_message(score, total)}")
    st.markdown("---")

    # ── Question review ───────────────────────────────────────────────────
    st.markdown("### Revisão das questões")
    for q in st.session_state.questions:
        chosen = st.session_state.answers.get(q["id"])
        is_correct = chosen == q["correct_answer"]
        icon = "✅" if is_correct else "❌"

        with st.expander(f"{icon} Questão {q['id']}: {q['question'][:80]}…"):
            st.markdown(f"**Sua resposta:** {chosen} — {q['options'].get(chosen, 'N/A')}")
            if not is_correct:
                st.markdown(
                    f"**Resposta correta:** {q['correct_answer']} — "
                    f"{q['options'][q['correct_answer']]}"
                )
            st.markdown(f"**Explicação:** {q['explanation']}")

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Gerar Novas Questões", use_container_width=True, type="primary"):
            _reset_to_generating()
            st.rerun()
