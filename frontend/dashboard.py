import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import re
import json
import os
import subprocess

# -------------------------------------------------------------------
# Configuration & Custom CSS (Minimalist Light Theme)
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Printer Review Intelligence",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
    }

    .kpi-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 18px 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .kpi-card:hover {
        border-color: #cbd5e1;
        transform: translateY(-2px);
    }
    .kpi-icon-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 34px;
        height: 34px;
        border-radius: 9px;
        font-size: 16px;
        margin-bottom: 8px;
    }
    .kpi-title {
        color: #64748b;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 2.1rem;
        font-weight: 700;
        color: #0f172a;
        margin: 4px 0;
    }
    .kpi-subtext {
        color: #0d9488;
        font-size: 0.8rem;
        font-weight: 500;
    }

    .mini-stat {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px 16px;
        text-align: left;
    }
    .mini-stat-label { color: #64748b; font-size: 0.72rem; font-weight: 600; text-transform: uppercase; }
    .mini-stat-value { color: #0f172a; font-size: 1.3rem; font-weight: 700; margin-top: 2px; }

    .feedback-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        height: 100%;
    }
    .feedback-quote {
        font-style: italic;
        color: #334155;
        font-size: 0.85rem;
        background: #f8fafc;
        border-left: 3px solid #cbd5e1;
        padding: 8px 10px;
        margin: 10px 0;
        border-radius: 4px;
    }
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
    }
    .badge-high { background: #fee2e2; color: #b91c1c; }
    .badge-medium { background: #fef3c7; color: #92400e; }
    .badge-low { background: #d1fae5; color: #065f46; }

    .trend-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 9px 4px;
        border-bottom: 1px solid #eef2f7;
    }
    .trend-count {
        background: #fee2e2;
        color: #b91c1c;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 700;
    }

    div[role="dialog"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #0f172a !important;
    }
    div[role="dialog"] h2, div[role="dialog"] p, div[role="dialog"] span {
        color: #0f172a !important;
    }

    .stSelectbox label, .stTextInput label {
        color: #334155;
        font-weight: 600;
    }

    .source-chip {
        display: block;
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 8px 10px;
        margin: 4px 0;
        font-size: 0.82rem;
        color: #334155;
    }

    .role-badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 700;
    }
    .role-admin { background: #ede9fe; color: #5b21b6; }
    .role-user { background: #e0f2fe; color: #075985; }
    
    .admin-review-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
    }
    .admin-review-card:hover {
        border-color: #cbd5e1;
        background-color: #fafafa;
    }
</style>
""", unsafe_allow_html=True)

API_BASE_URL = "http://localhost:8000"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "phi3"

# -------------------------------------------------------------------
# Auth — simple username/password login for office use.
# -------------------------------------------------------------------
CREDENTIALS = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "user"},
}

MODEL_VISIBILITY_FILE = os.path.join(os.path.dirname(__file__), "model_visibility.json")


def load_hidden_models():
    """Admin-managed list of model names hidden from the User role."""
    if os.path.exists(MODEL_VISIBILITY_FILE):
        try:
            with open(MODEL_VISIBILITY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f).get("hidden_models", []))
        except Exception:
            return set()
    return set()


def save_hidden_models(hidden_set):
    with open(MODEL_VISIBILITY_FILE, "w", encoding="utf-8") as f:
        json.dump({"hidden_models": sorted(hidden_set)}, f, indent=2)


def login_screen():
    st.markdown("## 🖨️ Printer Review Intelligence")
    st.caption("Please sign in to continue.")

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            user_record = CREDENTIALS.get(username.strip().lower())
            if user_record and user_record["password"] == password:
                st.session_state.authenticated = True
                st.session_state.username = username.strip().lower()
                st.session_state.role = user_record["role"]
                st.rerun()
            else:
                st.error("Invalid username or password.")


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    login_screen()
    st.stop()

IS_ADMIN = st.session_state.get("role") == "admin"

SENTIMENT_COLORS = {
    "Positive 😊": "#10b981",
    "Negative 😠": "#f43f5e",
    "Neutral 😐": "#f59e0b"
}

CATEGORY_GROUP_MAP = {
    "Connectivity": "Connectivity",
    "Cost": "Cost & Consumables",
    "Ink & Cost": "Cost & Consumables",
    "Print Quality": "Print Performance",
    "Speed": "Print Performance",
    "Reliability": "Reliability",
    "Setup & Install": "Setup & Functionality",
    "App & Software": "Setup & Functionality"
}

CHAT_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "what", "why", "how",
    "does", "do", "did", "with", "for", "and", "or", "of", "in", "on",
    "to", "about", "printer", "printers", "review", "reviews", "customer",
    "customers", "main", "issues", "issue", "people", "users", "user",
    "this", "that", "these", "those", "have", "has", "can", "could",
    "would", "should", "tell", "me", "you", "please", "there", "any"
}

# -------------------------------------------------------------------
# Data Fetching Helpers & Cleaning
# -------------------------------------------------------------------
@st.cache_data(ttl=30)
def fetch_raw_reviews():
    try:
        res = requests.get(f"{API_BASE_URL}/raw-reviews", timeout=5)
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            if not df.empty and "model_name" in df.columns:
                df["model_name"] = df["model_name"].astype(str).str.strip()
            return df
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=30)
def fetch_highlights():
    try:
        res = requests.get(f"{API_BASE_URL}/highlights", timeout=5)
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            if not df.empty and "model_name" in df.columns:
                df["model_name"] = df["model_name"].astype(str).str.strip()
            return df
    except Exception:
        pass
    return pd.DataFrame()


raw_df = fetch_raw_reviews()
highlights_df = fetch_highlights()


def map_sentiment(val):
    val_str = str(val).upper()
    if "POS" in val_str or val_str in ["4", "5", "4.0", "5.0"]:
        return "Positive 😊"
    elif "NEG" in val_str or val_str in ["1", "2", "1.0", "2.0"]:
        return "Negative 😠"
    return "Neutral 😐"


if not raw_df.empty and "sentiment" not in raw_df.columns:
    if "rating_value" in raw_df.columns:
        raw_df["sentiment"] = raw_df["rating_value"].apply(map_sentiment)
    elif "sentiment_source" in raw_df.columns:
        raw_df["sentiment"] = raw_df["sentiment_source"].apply(map_sentiment)
    else:
        raw_df["sentiment"] = "Neutral 😐"

if not raw_df.empty and "sentiment" in raw_df.columns:
    raw_df["sentiment_raw"] = raw_df["sentiment"]
    raw_df["sentiment"] = raw_df["sentiment"].apply(map_sentiment)

if not raw_df.empty and "rating_value" in raw_df.columns:
    raw_df["rating_value"] = pd.to_numeric(raw_df["rating_value"], errors="coerce")


# -------------------------------------------------------------------
# Extract Robust Printer Model List (role-aware)
# -------------------------------------------------------------------
def get_all_models(df_raw, df_hl, role="user", hidden_models=None):
    hidden_models = hidden_models or set()

    all_models = set()
    for df in [df_raw, df_hl]:
        if not df.empty and "model_name" in df.columns:
            valid_models = df["model_name"].dropna().astype(str).str.strip()
            all_models.update([m for m in valid_models if m and m.lower() not in ["nan", "none", "null"]])

    if role == "admin":
        visible = all_models
    else:
        models_with_reviews = set()
        if not df_raw.empty and "model_name" in df_raw.columns:
            counts = df_raw["model_name"].dropna().astype(str).str.strip().value_counts()
            models_with_reviews = set(counts[counts > 0].index)
        visible = (all_models & models_with_reviews) - hidden_models

    return ["All Models"] + sorted(visible)


# -------------------------------------------------------------------
# AI-Powered QA Insight Generation (Ollama)
# -------------------------------------------------------------------
def ollama_generate(prompt, timeout=180):
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 350},
            },
            timeout=timeout,
        )
        if response.status_code == 200:
            text = response.json().get("response", "").strip()
            if text:
                st.session_state["last_ollama_error"] = None
                return text
            st.session_state["last_ollama_error"] = "Ollama responded with HTTP 200 but an empty body."
            return None

        st.session_state["last_ollama_error"] = (
            f"Ollama responded with HTTP {response.status_code}. This often means the "
            f"model '{OLLAMA_MODEL}' isn't pulled yet - try `ollama pull {OLLAMA_MODEL}`."
        )
        return None

    except requests.exceptions.ConnectionError:
        st.session_state["last_ollama_error"] = (
            f"Couldn't connect to Ollama at {OLLAMA_BASE_URL}. Make sure it's running - "
            "`ollama run phi3` in a terminal (or `ollama serve` if it's already pulled)."
        )
        return None
    except requests.exceptions.Timeout:
        st.session_state["last_ollama_error"] = (
            f"Ollama connected fine but didn't finish responding within {timeout}s. "
            "This usually means it's genuinely still generating (phi3 on CPU-only "
            "hardware can take a while for longer answers) rather than not running - "
            "try again, and consider closing other heavy apps to free up CPU."
        )
        return None
    except Exception as e:
        st.session_state["last_ollama_error"] = f"Unexpected error calling Ollama: {e}"
        return None


def ollama_failure_message(action_hint="Start it locally with `ollama run phi3`, then click **🔄 Regenerate AI Insights** below (this result may be cached from before Ollama was ready)."):
    err = st.session_state.get("last_ollama_error")
    base = "Ollama isn't running or didn't respond, so a live result couldn't be generated."
    if err:
        return f"{base}\n\n**Reason:** {err}\n\n{action_hint}"
    return f"{base}\n\n{action_hint}"


def select_representative_samples(review_series, max_samples=6, min_length=40, max_chars=400):
    texts = review_series.dropna().astype(str)
    texts = texts[texts.str.len() >= min_length]
    texts = texts.sort_values(key=lambda s: s.str.len(), ascending=False)
    selected = texts.head(max_samples).tolist()
    return [t[:max_chars] + ("…" if len(t) > max_chars else "") for t in selected]


def build_qa_prompt(category, sample_reviews, insight_type):
    reviews_block = "\n".join(f"- {r}" for r in sample_reviews)

    grounding_rule = (
        'GROUNDING RULE: Do not state any specific number, statistic, timing, capacity, '
        'or product specification (e.g. "25 seconds per page", "12,000 page yield") unless '
        'that exact figure is written verbatim in the text above. If no specific figures are '
        'present, describe the issue or strength in qualitative terms only - do not estimate '
        'or invent numbers to sound precise.'
    )

    if insight_type == "negative":
        return f"""You are a QA analyst reviewing real customer complaints for a printer's "{category}" category.

Customer complaints:
{reviews_block}

Write a structured analysis using EXACTLY these three headers, in this exact order, with nothing before the first header and nothing after the last one.

WHAT'S HAPPENING: 2-3 sentences describing the specific, concrete failure pattern you see across these complaints. Be specific to what customers actually described, not a generic statement.

LIKELY ROOT CAUSE: Your best technical hypothesis for why this happens, reasoning about how a printer's {category} functionality typically works internally (firmware, WiFi radio/driver stack, mechanical print-head or ink-tank hardware, sensor calibration, packaging/logistics damage, or documentation/UX gap). Pick the explanation that best fits what these specific complaints describe.

RECOMMENDATION: One concrete, engineer-actionable recommendation - specific enough that an engineer or support lead could act on it directly, not generic advice like "improve quality."

Reminder: {grounding_rule}"""
    else:
        return f"""You are a product analyst reviewing real customer praise for a printer's "{category}" category.

Customer comments:
{reviews_block}

Write a structured analysis using EXACTLY these three headers, in this exact order, with nothing before the first header and nothing after the last one.

WHAT CUSTOMERS LOVE: 2-3 sentences on the specific, concrete thing customers appreciate. Be specific to what they actually said, not a generic statement.

WHY IT WORKS: Your best hypothesis on the underlying design or engineering choice that makes this work well for users.

MARKETING ANGLE: One concrete suggestion for how to highlight this specific strength, referencing the actual theme in what customers said.

Reminder: {grounding_rule}"""


@st.cache_data(ttl=3600, show_spinner=False)
def generate_qa_insight_cached(category, review_texts_tuple, insight_type):
    prompt = build_qa_prompt(category, list(review_texts_tuple), insight_type)
    return ollama_generate(prompt)


# -------------------------------------------------------------------
# AI Review Assistant — retrieval + Ollama synthesis
# -------------------------------------------------------------------
def extract_query_terms(query):
    tokens = re.findall(r"[a-zA-Z]{3,}", query.lower())
    terms = [t for t in tokens if t not in CHAT_STOPWORDS]
    return terms if terms else tokens


def search_relevant_reviews(query, df, max_results=8):
    if df.empty or "review_body" not in df.columns:
        return pd.DataFrame(), []

    terms = extract_query_terms(query)
    if not terms:
        return pd.DataFrame(), []

    body_lower = df["review_body"].astype(str).str.lower()
    scores = pd.Series(0, index=df.index)
    for term in terms:
        scores += body_lower.str.contains(re.escape(term), na=False).astype(int)

    matched_mask = scores > 0
    if not matched_mask.any():
        return pd.DataFrame(), terms

    matched = df[matched_mask].copy()
    matched["_match_score"] = scores[matched_mask]
    matched = matched.sort_values("_match_score", ascending=False)
    return matched.head(max_results), terms


def summarize_aggregate_context(df):
    if df.empty:
        return "No review data is currently loaded."

    parts = [f"Total reviews in scope: {len(df)}."]

    if "sentiment" in df.columns:
        counts = df["sentiment"].value_counts()
        sentiment_line = ", ".join(f"{k}: {v}" for k, v in counts.items())
        parts.append(f"Sentiment breakdown: {sentiment_line}.")

    if "category" in df.columns:
        top_cats = df["category"].value_counts().head(5)
        cat_line = ", ".join(f"{k} ({v})" for k, v in top_cats.items())
        parts.append(f"Most-mentioned categories: {cat_line}.")

    return " ".join(parts)


def build_chat_prompt(query, matched_df, aggregate_context, model_scope):
    if not matched_df.empty:
        excerpt_lines = []
        for _, row in matched_df.iterrows():
            model = row.get("model_name", "Unknown model")
            sentiment = row.get("sentiment", "Unknown")
            body = str(row.get("review_body", ""))[:280]
            excerpt_lines.append(f"- [{sentiment} | {model}] {body}")
        excerpts_block = "\n".join(excerpt_lines)
    else:
        excerpts_block = "(No individual reviews matched this question directly.)"

    return f"""You are a helpful analyst answering questions about real printer customer reviews for the model scope: {model_scope}.

User question: {query}

Relevant review excerpts:
{excerpts_block}

Aggregate context for this scope: {aggregate_context}

Answer the question directly in 3-5 sentences, grounded ONLY in the excerpts and aggregate context above. If the excerpts don't clearly address the question, say so honestly and offer the closest relevant insight from the aggregate context instead. Do not invent specifics, numbers, or quotes that aren't present above."""


def answer_review_question(query, reviews_df, model_scope):
    matched, terms = search_relevant_reviews(query, reviews_df)
    aggregate_context = summarize_aggregate_context(reviews_df)
    prompt = build_chat_prompt(query, matched, aggregate_context, model_scope)
    answer = ollama_generate(prompt, timeout=45)

    if answer is None:
        err = st.session_state.get(
            "last_ollama_error",
            "Ollama isn't running or didn't respond."
        )
        answer = (
            f"⚠️ **{err}**\n\n"
            f"Once it's running, ask again. In the meantime, here's what the raw data shows: "
            f"{aggregate_context}"
        )

    return answer, matched


@st.dialog("Review Details Drill-Down", width="large")
def show_review_modal(sentiment_filter, model_name, reviews_subset):
    st.subheader(f"Raw Reviews — {sentiment_filter} ({model_name})")

    df_sub = reviews_subset.copy()
    if sentiment_filter != "Total":
        df_sub = df_sub[df_sub["sentiment"].str.contains(sentiment_filter, case=False, na=False)]

    # ---------------- Filter row ----------------
    f1, f2, f3, f4, f5 = st.columns(5)

    with f1:
        opts = ["All"] + sorted(df_sub["model_name"].dropna().unique().tolist()) if "model_name" in df_sub.columns else ["All"]
        model_choice = st.selectbox("Model", opts, key="modal_filter_model")

    with f2:
        opts = ["All"] + sorted(df_sub["category"].dropna().unique().tolist()) if "category" in df_sub.columns else ["All"]
        category_choice = st.selectbox("Category", opts, key="modal_filter_category")

    with f3:
        opts = ["All"] + sorted(df_sub["sentiment"].dropna().unique().tolist()) if "sentiment" in df_sub.columns else ["All"]
        sentiment_choice = st.selectbox("Sentiment", opts, key="modal_filter_sentiment")

    with f4:
        star_vals = sorted({int(v) for v in df_sub["rating_value"].dropna().unique()}, reverse=True) if "rating_value" in df_sub.columns else []
        opts = ["All"] + [str(v) for v in star_vals]
        star_choice = st.selectbox("Stars", opts, key="modal_filter_stars")

    with f5:
        opts = ["All"] + sorted(df_sub["source"].dropna().unique().tolist()) if "source" in df_sub.columns else ["All"]
        platform_choice = st.selectbox("Platform", opts, key="modal_filter_platform")

    search_query = st.text_input("🔍 Search within these reviews...", "", key="modal_filter_search")

    # ---------------- Apply filters ----------------
    if model_choice != "All":
        df_sub = df_sub[df_sub["model_name"] == model_choice]
    if category_choice != "All":
        df_sub = df_sub[df_sub["category"] == category_choice]
    if sentiment_choice != "All":
        df_sub = df_sub[df_sub["sentiment"] == sentiment_choice]
    if star_choice != "All":
        df_sub = df_sub[df_sub["rating_value"] == int(star_choice)]
    if platform_choice != "All":
        df_sub = df_sub[df_sub["source"] == platform_choice]
    if search_query:
        df_sub = df_sub[df_sub["review_body"].str.contains(search_query, case=False, na=False)]

    st.write(f"Showing **{len(df_sub)}** records")

    display_cols = [c for c in ["model_name", "sentiment", "category", "rating_value", "review_body", "source"] if c in df_sub.columns]

    st.dataframe(
        df_sub[display_cols],
        column_config={
            "model_name": "Model",
            "sentiment": "Sentiment",
            "category": "Category",
            "rating_value": "Stars",
            "review_body": "Review Body",
            "source": "Platform"
        },
        hide_index=True,
        use_container_width=True,
        height=380
    )

    if st.button("✖ Close", use_container_width=True, key="modal_close_btn"):
        st.rerun()


# -------------------------------------------------------------------
# Admin Helper Functions
# -------------------------------------------------------------------
def admin_fetch_reviews(search_term=""):
    """Fetch reviews with optional search filter - uses cached data."""
    df = fetch_raw_reviews()
    if df.empty:
        return []
    
    reviews = df.to_dict('records')
    if search_term:
        search_lower = search_term.lower()
        reviews = [
            r for r in reviews 
            if search_lower in str(r.get('model_name', '')).lower() 
            or search_lower in str(r.get('review_body', '')).lower()
        ]
    return reviews


def admin_get_models():
    """Get list of models with reviews."""
    df = fetch_raw_reviews()
    if df.empty:
        return []
    return sorted(df['model_name'].dropna().unique().tolist())


def admin_update_review(review_id, category, sentiment):
    """Update a review's category and sentiment."""
    try:
        response = requests.patch(
            f"{API_BASE_URL}/raw-reviews/{review_id}",
            json={
                "category": category,
                "sentiment_source": sentiment,
                "actor": st.session_state.username
            },
            timeout=5
        )
        if response.status_code == 200:
            return True, "Review updated successfully!"
        else:
            return False, f"Failed: {response.text}"
    except Exception as e:
        return False, f"Error: {e}"


def admin_delete_review(review_id):
    """Delete a review."""
    try:
        response = requests.delete(
            f"{API_BASE_URL}/raw-reviews/{review_id}",
            params={"actor": st.session_state.username},
            timeout=5
        )
        if response.status_code == 200:
            return True, "Review deleted successfully!"
        else:
            return False, f"Failed: {response.text}"
    except Exception as e:
        return False, f"Error: {e}"


def admin_bulk_reclassify(review_ids):
    """Bulk reclassify reviews."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/raw-reviews/bulk-reclassify",
            json={
                "review_ids": review_ids,
                "actor": st.session_state.username
            },
            timeout=600  # embedding-based reclassify is slower than the old heuristic
        )
        if response.status_code == 200:
            result = response.json()
            return True, f"Reclassified {result['updated']} out of {result['processed']} reviews!"
        else:
            return False, f"Failed: {response.text}"
    except Exception as e:
        return False, f"Error: {e}"


def admin_fetch_audit_log(limit=50):
    """Fetch recent audit log entries."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/audit-log",
            params={"limit": limit},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []


PRODUCTS_FILE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scraper", "products.json")
)


def load_scraper_products():
    """Reads the shared products.json that both scrapers and this dashboard use."""
    try:
        with open(PRODUCTS_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"amazon": [], "hp": []}


def save_scraper_products(products_dict):
    with open(PRODUCTS_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(products_dict, f, indent=2, ensure_ascii=False)


def launch_scraper_script(script_name, model_name=None):
    """Launches a scraper script in a new terminal window (Windows).
    If model_name is given, passes it as a CLI arg so the scraper only
    scrapes that one product instead of every product in products.json."""
    try:
        frontend_dir = os.path.dirname(os.path.abspath(__file__))
        scraper_dir = os.path.normpath(os.path.join(frontend_dir, "..", "scraper"))

        if not os.path.isdir(scraper_dir):
            return False, f"Scraper folder not found at: {scraper_dir}"

        arg_part = f' "{model_name}"' if model_name else ""
        inner_cmd = (
            f'cd /d "{scraper_dir}" && '
            f'call venv\\Scripts\\activate && '
            f'python {script_name}{arg_part}'
        )
        full_command = f'cmd /k "{inner_cmd}"'
        subprocess.Popen(full_command, creationflags=subprocess.CREATE_NEW_CONSOLE)
        label = f"{script_name} for '{model_name}'" if model_name else script_name
        return True, f"Launched {label} in a new terminal window."
    except Exception as e:
        return False, f"Couldn't launch: {e}"


# -------------------------------------------------------------------
# Sidebar — platform meta info + role-gated admin controls
# -------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🖨️ PRIP")
    st.caption("Printer Review Intelligence Platform")

    role_class = "role-admin" if IS_ADMIN else "role-user"
    st.markdown(
        f"Signed in as **{st.session_state.username}** "
        f"<span class='role-badge {role_class}'>{st.session_state.role.upper()}</span>",
        unsafe_allow_html=True
    )
    if st.button("Log out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

    st.markdown("---")
    st.markdown("**Data Sources**")
    if not raw_df.empty and "source" in raw_df.columns:
        for s in sorted(raw_df["source"].dropna().unique()):
            st.markdown(f"- {s}")
    else:
        st.caption("No data loaded yet")
    st.markdown("---")

    # Live Ollama status check.
    st.markdown("**AI Engine (Ollama)**")
    try:
        tags_res = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        if tags_res.status_code == 200:
            model_names = [m.get("name", "") for m in tags_res.json().get("models", [])]
            if any(OLLAMA_MODEL in m for m in model_names):
                st.success(f"🟢 Connected — {OLLAMA_MODEL} ready")
            else:
                st.warning(f"🟡 Connected, but '{OLLAMA_MODEL}' not pulled yet")
        else:
            st.error(f"🔴 Ollama responded with HTTP {tags_res.status_code}")
    except Exception:
        st.error("🔴 Not reachable — run `ollama run phi3`")

    st.markdown("---")
    st.caption(f"Last refreshed: {pd.Timestamp.now().strftime('%b %d, %Y %I:%M %p')}")

    # ---------------- Admin-only controls ----------------
    if IS_ADMIN:
        st.markdown("### 🛠️ Admin Tools")

        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        with st.expander("👁️ Manage model visibility (Users)"):
            st.caption("Models unchecked here are hidden from the User role, even if they have review data.")
            all_known = sorted(get_all_models(raw_df, highlights_df, role="admin")[1:])
            hidden_now = load_hidden_models()
            newly_hidden = st.multiselect(
                "Hide these models from Users",
                options=all_known,
                default=sorted(hidden_now & set(all_known))
            )
            if st.button("Save visibility settings", use_container_width=True):
                save_hidden_models(set(newly_hidden))
                st.success("Saved.")
                st.rerun()

        

        # --- NEW: Manage / Edit Reviews ---
        with st.expander("🗑️ Manage / Edit Reviews"):
            st.caption("Search, edit, or delete individual reviews.")
            
            search_term = st.text_input("🔍 Search by model name or review text", "", key="admin_review_search")
            
            reviews = admin_fetch_reviews(search_term)
            
            if reviews:
                st.write(f"Showing {min(len(reviews), 20)} of {len(reviews)} reviews")
                
                for review in reviews[:20]:
                    with st.container():
                        st.markdown(f"""
                        <div class="admin-review-card">
                            <b>{review.get('model_name', 'Unknown')}</b> 
                            <span style="color:#64748b;font-size:0.8rem;">| ID: {review.get('id')} | Rating: {review.get('rating_value', 'N/A')}⭐</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2, col3 = st.columns([3, 2, 1])
                        
                        with col1:
                            st.caption(f"\"{str(review.get('review_body', ''))[:150]}...\"")
                        
                        with col2:
                            categories = ["Connectivity", "Print Quality", "Reliability", "Setup & Install", 
                                        "App & Software", "Ink & Cost", "Speed", "Support", "General"]
                            current_cat = review.get('category', 'General')
                            cat_index = categories.index(current_cat) if current_cat in categories else 0
                            
                            new_category = st.selectbox(
                                "Category",
                                categories,
                                index=cat_index,
                                key=f"admin_cat_{review['id']}"
                            )
                            
                            sentiments = ["POSITIVE", "NEGATIVE", "NEUTRAL"]
                            current_sent = str(review.get('sentiment_raw', 'NEUTRAL')).upper()
                            sent_index = sentiments.index(current_sent) if current_sent in sentiments else 2

                            new_sentiment = st.selectbox(
                                "Sentiment",
                                sentiments,
                                index=sent_index,
                                key=f"admin_sent_{review['id']}"
                            )
                        
                        with col3:
                            if st.button("💾 Update", key=f"admin_update_{review['id']}"):
                                success, message = admin_update_review(review['id'], new_category, new_sentiment)
                                if success:
                                    st.success(f"✅ {message}")
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error(f"❌ {message}")
                            
                            confirm_del = st.checkbox("Confirm delete", key=f"admin_confirm_{review['id']}")
                            if st.button("🗑️ Delete", key=f"admin_delete_{review['id']}", disabled=not confirm_del):
                                success, message = admin_delete_review(review['id'])
                                if success:
                                    st.success(f"✅ {message}")
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error(f"❌ {message}")
                        
                        st.divider()
            else:
                st.info("No reviews found matching your search.")

        # --- NEW: Bulk Re-classify ---
        with st.expander("🔄 Bulk Re-classify"):
            st.caption("Re-run AI classification on reviews for a specific model.")
            
            df = fetch_raw_reviews()
            if not df.empty:
                models = admin_get_models()
                model_filter = st.selectbox("Select model to reclassify", ["All Models"] + models)
                
                if st.button("🚀 Run Bulk Re-classification", use_container_width=True):
                    with st.spinner("Reclassifying reviews... This may take a moment."):
                        if model_filter == "All Models":
                            review_ids = df['id'].tolist()
                        else:
                            review_ids = df[df['model_name'] == model_filter]['id'].tolist()
                        
                        if not review_ids:
                            st.warning("No reviews found for this model.")
                        else:
                            success, message = admin_bulk_reclassify(review_ids)
                            if success:
                                st.success(f"✅ {message}")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
            else:
                st.info("No reviews found in the database.")

        # --- NEW: Audit Log ---
        with st.expander("📜 Audit Log"):
            st.caption("Recent admin actions (edits, deletes, bulk reclassifications).")
            
            entries = admin_fetch_audit_log(limit=50)
            if entries:
                for entry in entries:
                    st.markdown(f"""
                    **{entry.get('actor', 'Unknown')}** - `{entry.get('action', 'unknown')}`  
                    {entry.get('details', 'No details')}  
                    *{entry.get('timestamp', '')}*
                    ---
                    """)
            else:
                st.info("No audit log entries found.")

# -------------------------------------------------------------------
# Main Dashboard Layout
# -------------------------------------------------------------------
if IS_ADMIN:
    tab_dashboard, tab_qa, tab_assistant, tab_admin = st.tabs(
        ["📊 Executive Dashboard", "💡 QA & Topic Insights", "🤖 AI Review Assistant", "🛠️ Admin Console"]
    )
else:
    tab_dashboard, tab_qa, tab_assistant = st.tabs(
        ["📊 Executive Dashboard", "💡 QA & Topic Insights", "🤖 AI Review Assistant"]
    )
    tab_admin = None

with tab_dashboard:
    f_col1, f_col2 = st.columns([7, 3])
    with f_col1:
        st.markdown("## 🖨️ Printer Review Intelligence")
        st.caption("Here's what's happening with printer reviews today.")
    with f_col2:
        hidden_models = load_hidden_models()
        available_models = get_all_models(raw_df, highlights_df, role=st.session_state.role, hidden_models=hidden_models)
        selected_model = st.selectbox("Filter by Printer Model", available_models, index=0)

    # Robust Filter Logic (Strip spaces & normalize comparison)
    filtered_reviews = raw_df.copy()
    filtered_highlights = highlights_df.copy()

    if selected_model != "All Models":
        target = selected_model.strip().lower()
        if not filtered_reviews.empty and "model_name" in filtered_reviews.columns:
            filtered_reviews = filtered_reviews[
                filtered_reviews["model_name"].astype(str).str.strip().str.lower() == target
            ]
        if not filtered_highlights.empty and "model_name" in filtered_highlights.columns:
            filtered_highlights = filtered_highlights[
                filtered_highlights["model_name"].astype(str).str.strip().str.lower() == target
            ]

    st.markdown("---")

    # ---------------- Primary KPI Row (Total / Positive / Negative / Neutral) ----------------
    st.markdown("### Key Performance Indicators")

    total_cnt = len(filtered_reviews)
    pos_cnt = len(filtered_reviews[filtered_reviews["sentiment"].str.contains("Positive", na=False)]) if not filtered_reviews.empty else 0
    neg_cnt = len(filtered_reviews[filtered_reviews["sentiment"].str.contains("Negative", na=False)]) if not filtered_reviews.empty else 0
    neu_cnt = len(filtered_reviews[filtered_reviews["sentiment"].str.contains("Neutral", na=False)]) if not filtered_reviews.empty else 0

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    with kpi_col1:
        st.markdown(f"""
        <div class="kpi-card" style="border-top: 4px solid #6366f1;">
            <div class="kpi-icon-badge" style="background:#eef2ff;">📊</div>
            <div class="kpi-title">Total Reviews</div>
            <div class="kpi-value">{total_cnt}</div>
            <div class="kpi-subtext">Scope: {selected_model}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View All →", key="btn_total", use_container_width=True):
            show_review_modal("Total", selected_model, filtered_reviews)

    with kpi_col2:
        st.markdown(f"""
        <div class="kpi-card" style="border-top: 4px solid #10b981;">
            <div class="kpi-icon-badge" style="background:#d1fae5;">😊</div>
            <div class="kpi-title">Positive</div>
            <div class="kpi-value">{pos_cnt}</div>
            <div class="kpi-subtext">{(pos_cnt/total_cnt*100 if total_cnt > 0 else 0):.1f}% of total</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View Positive →", key="btn_pos", use_container_width=True):
            show_review_modal("Positive", selected_model, filtered_reviews)

    with kpi_col3:
        st.markdown(f"""
        <div class="kpi-card" style="border-top: 4px solid #f43f5e;">
            <div class="kpi-icon-badge" style="background:#fee2e2;">😠</div>
            <div class="kpi-title">Negative</div>
            <div class="kpi-value">{neg_cnt}</div>
            <div class="kpi-subtext">{(neg_cnt/total_cnt*100 if total_cnt > 0 else 0):.1f}% of total</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View Negative →", key="btn_neg", use_container_width=True):
            show_review_modal("Negative", selected_model, filtered_reviews)

    with kpi_col4:
        st.markdown(f"""
        <div class="kpi-card" style="border-top: 4px solid #f59e0b;">
            <div class="kpi-icon-badge" style="background:#fef3c7;">😐</div>
            <div class="kpi-title">Neutral</div>
            <div class="kpi-value">{neu_cnt}</div>
            <div class="kpi-subtext">{(neu_cnt/total_cnt*100 if total_cnt > 0 else 0):.1f}% of total</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View Neutral →", key="btn_neu", use_container_width=True):
            show_review_modal("Neutral", selected_model, filtered_reviews)

    # ---------------- Secondary stat chips ----------------
    st.markdown("")
    products_tracked = raw_df["model_name"].nunique() if not raw_df.empty and "model_name" in raw_df.columns else 0
    avg_rating = filtered_reviews["rating_value"].mean() if not filtered_reviews.empty and "rating_value" in filtered_reviews.columns else None
    sources_tracked = raw_df["source"].nunique() if not raw_df.empty and "source" in raw_df.columns else 0

    mini1, mini2, mini3 = st.columns(3)
    with mini1:
        st.markdown(f"""
        <div class="mini-stat"><div class="mini-stat-label">Products Tracked</div>
        <div class="mini-stat-value">{products_tracked}</div></div>
        """, unsafe_allow_html=True)
    with mini2:
        rating_display = f"{avg_rating:.1f} / 5 ⭐" if avg_rating is not None and not pd.isna(avg_rating) else "N/A"
        st.markdown(f"""
        <div class="mini-stat"><div class="mini-stat-label">Average Rating</div>
        <div class="mini-stat-value">{rating_display}</div></div>
        """, unsafe_allow_html=True)
    with mini3:
        st.markdown(f"""
        <div class="mini-stat"><div class="mini-stat-label">Data Sources</div>
        <div class="mini-stat-value">{sources_tracked}</div></div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ---------------- Charts: issue heatmap + sentiment donut ----------------
    c_left, c_right = st.columns([6, 4])

    with c_left:
        st.subheader("🔥 Issue Heatmap — % Negative by Product & Category")
        if not filtered_reviews.empty and "category" in filtered_reviews.columns:
            df_heat = filtered_reviews.copy()
            df_heat["category_group"] = df_heat["category"].map(CATEGORY_GROUP_MAP).fillna("Other")

            pivot_total = (
                df_heat.groupby(["model_name", "category_group"]).size()
                .unstack(fill_value=0)
            )

            neg_df = df_heat[df_heat["sentiment"].str.contains("Negative", na=False)]
            pivot_neg = (
                neg_df.groupby(["model_name", "category_group"]).size()
                .unstack(fill_value=0)
                .reindex(index=pivot_total.index, columns=pivot_total.columns, fill_value=0)
            )

            if not pivot_total.empty and pivot_total.values.sum() > 0:
                pct_negative = (pivot_neg / pivot_total.replace(0, pd.NA) * 100).round(1)

                text_labels = pct_negative.copy().astype(object)
                for r in pivot_total.index:
                    for c in pivot_total.columns:
                        total_n = pivot_total.loc[r, c]
                        if total_n == 0:
                            text_labels.loc[r, c] = ""
                        else:
                            pct_val = pct_negative.loc[r, c]
                            text_labels.loc[r, c] = f"{pct_val:.0f}%<br>({total_n})"

                fig_heat = go.Figure(data=go.Heatmap(
                    z=pct_negative.values,
                    x=pct_negative.columns.tolist(),
                    y=pct_negative.index.tolist(),
                    colorscale=[[0, "#0d9488"], [0.5, "#facc15"], [1, "#f43f5e"]],
                    zmin=0, zmax=100,
                    text=text_labels.values,
                    texttemplate="%{text}",
                    textfont={"size": 12, "color": "#0f172a"},
                    hovertemplate="<b>%{y}</b><br>%{x}<br>Negative: %{z:.1f}%<extra></extra>",
                    colorbar=dict(title="% Negative", ticksuffix="%"),
                    xgap=3, ygap=3
                ))
                fig_heat.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#334155"),
                    margin=dict(t=10, l=10, r=10, b=10),
                    xaxis=dict(side="top", tickangle=0),
                    yaxis=dict(autorange="reversed")
                )
                st.plotly_chart(fig_heat, use_container_width=True)
                st.caption("Cell shows % of reviews that were negative, with total review count in parentheses. Blank cells mean no reviews yet for that product/category combination.")
            else:
                st.info("No category data available for this selection.")
        else:
            st.info("No category data available for this selection.")

    with c_right:
        st.subheader("Sentiment Distribution")
        if not filtered_reviews.empty and "sentiment" in filtered_reviews.columns:
            sent_counts = filtered_reviews["sentiment"].value_counts().reset_index()
            sent_counts.columns = ["Sentiment", "Count"]
            total_all = sent_counts["Count"].sum()

            fig_pie = go.Figure(data=[go.Pie(
                labels=sent_counts["Sentiment"],
                values=sent_counts["Count"],
                hole=0.62,
                marker=dict(colors=[SENTIMENT_COLORS.get(s, "#94a3b8") for s in sent_counts["Sentiment"]]),
                textinfo="none",
                showlegend=False
            )])
            fig_pie.update_layout(
                annotations=[dict(
                    text=f"<b>{total_all}</b><br><span style='font-size:11px;color:#64748b'>Total</span>",
                    x=0.5, y=0.5, font_size=22, showarrow=False
                )],
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_pie, use_container_width=True)

            legend_cols = st.columns(len(sent_counts)) if len(sent_counts) else []
            for col, (_, row) in zip(legend_cols, sent_counts.iterrows()):
                pct = (row["Count"] / total_all * 100) if total_all else 0
                dot_color = SENTIMENT_COLORS.get(row["Sentiment"], "#94a3b8")
                col.markdown(
                    f"<div style='text-align:center;font-size:13px;'>"
                    f"<span style='color:{dot_color};font-size:16px;'>●</span> {row['Sentiment']}<br>"
                    f"<b>{pct:.0f}%</b> ({row['Count']})</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("No sentiment data available for this selection.")

    st.markdown("---")

    # ---------------- Top Product Feedback + Trending Issues ----------------
    feed_col, trend_col = st.columns([7, 3])

    with feed_col:
        st.subheader("🗂️ Top Product Feedback")
        if not filtered_reviews.empty:
            model_volume = (
                filtered_reviews.groupby("model_name").size()
                .sort_values(ascending=False)
            )
            top_models = model_volume.head(3).index.tolist() if selected_model == "All Models" else [selected_model]

            fb_cols = st.columns(len(top_models)) if top_models else []
            for col, model in zip(fb_cols, top_models):
                model_df = filtered_reviews[filtered_reviews["model_name"] == model]
                m_total = len(model_df)
                m_neg = model_df[model_df["sentiment"].str.contains("Negative", na=False)]
                m_avg_rating = model_df["rating_value"].mean() if "rating_value" in model_df.columns else None

                neg_pct = (len(m_neg) / m_total * 100) if m_total else 0
                if neg_pct > 30:
                    badge_class, badge_text = "badge-high", "High Issues"
                elif neg_pct > 15:
                    badge_class, badge_text = "badge-medium", "Medium Issues"
                else:
                    badge_class, badge_text = "badge-low", "Low Issues"

                top_issue = m_neg["category"].value_counts().idxmax() if not m_neg.empty and "category" in m_neg.columns else "N/A"
                quote_source = m_neg if not m_neg.empty else model_df
                quote = ""
                if not quote_source.empty and "review_body" in quote_source.columns:
                    non_null = quote_source["review_body"].dropna()
                    raw_quote = str(non_null.iloc[0]) if not non_null.empty else ""
                    quote = (raw_quote[:110] + "…") if len(raw_quote) > 110 else raw_quote

                rating_str = f"{m_avg_rating:.1f} ⭐" if m_avg_rating is not None and not pd.isna(m_avg_rating) else "N/A"

                with col:
                    st.markdown(f"""
                    <div class="feedback-card">
                        <div style="display:flex;justify-content:space-between;align-items:start;">
                            <b>🖨️ {model}</b>
                            <span class="badge {badge_class}">{badge_text}</span>
                        </div>
                        <div style="color:#64748b;font-size:12px;margin-top:6px;">Top Issue: {top_issue}</div>
                        <div class="feedback-quote">“{quote}”</div>
                        <div style="display:flex;justify-content:space-between;font-size:12px;color:#334155;">
                            <span>Total Reviews<br><b>{m_total}</b></span>
                            <span>Avg. Rating<br><b>{rating_str}</b></span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No product feedback available for this selection.")

    with trend_col:
        st.subheader("🔥 Trending Issues")
        if not filtered_reviews.empty and "category" in filtered_reviews.columns:
            trend_counts = filtered_reviews["category"].value_counts().head(5).reset_index()
            trend_counts.columns = ["Category", "Count"]
            for i, row in trend_counts.iterrows():
                st.markdown(f"""
                <div class="trend-row">
                    <span><b>{i+1}.</b> {row['Category']}</span>
                    <span class="trend-count">{row['Count']}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No category data available.")

# -------------------------------------------------------------------
# Tab 2: QA & Actionable Insights
# -------------------------------------------------------------------
with tab_qa:
    st.subheader("💡 Key Quality & Product Action Insights")
    st.markdown("Click **Generate** on any category below to run AI analysis on demand. Nothing runs automatically, so the page loads instantly.")

    reviews_to_analyze = filtered_reviews if 'filtered_reviews' in locals() else raw_df

    MIN_REVIEWS_FOR_INSIGHT = 3  # skip categories with too few reviews to say anything meaningful

    if "qa_insights_cache" not in st.session_state:
        st.session_state.qa_insights_cache = {}  # {(category, insight_type): insight_text}

    def render_category_block(category, count, samples, insight_type, icon):
        cache_key = (category, insight_type)

        with st.expander(f"{icon} {category} — {count} {'negative' if insight_type == 'negative' else 'positive'} reviews"):
            if not samples:
                st.info("Not enough detailed review text in this category yet to generate an insight.")
                return

            cached_insight = st.session_state.qa_insights_cache.get(cache_key)

            if cached_insight is None:
                if st.button(f"⚡ Generate AI insight for {category}", key=f"gen_{insight_type}_{category}"):
                    with st.spinner(f"Analyzing {len(samples)} {category} {insight_type} reviews with AI..."):
                        result = generate_qa_insight_cached(category, tuple(samples), insight_type)
                    if result:
                        st.session_state.qa_insights_cache[cache_key] = result
                        st.rerun()
                    else:
                        st.warning(ollama_failure_message())
            else:
                st.markdown(cached_insight)
                st.caption(f"Based on {len(samples)} representative reviews out of {count} total in this category.")
                st.markdown("**📄 Source reviews used:**")
                for s in samples:
                    st.markdown(f"<div class='source-chip'>{s}</div>", unsafe_allow_html=True)
                if st.button("🔄 Regenerate this one", key=f"regen_{insight_type}_{category}"):
                    del st.session_state.qa_insights_cache[cache_key]
                    st.rerun()

    if not reviews_to_analyze.empty and "category" in reviews_to_analyze.columns:
        neg_reviews = reviews_to_analyze[reviews_to_analyze["sentiment"].str.contains("Negative", na=False)]
        pos_reviews = reviews_to_analyze[reviews_to_analyze["sentiment"].str.contains("Positive", na=False)]

        neg_category_counts = neg_reviews["category"].value_counts()
        pos_category_counts = pos_reviews["category"].value_counts()

        neg_categories = neg_category_counts[neg_category_counts >= MIN_REVIEWS_FOR_INSIGHT]
        pos_categories = pos_category_counts[pos_category_counts >= MIN_REVIEWS_FOR_INSIGHT]

        st.caption(
            f"{len(neg_categories)} complaint categories and {len(pos_categories)} strength "
            f"categories have at least {MIN_REVIEWS_FOR_INSIGHT} reviews each. Each insight you "
            f"generate is cached for an hour, so you only pay the wait once per category."
        )

        st.markdown("---")

        st.markdown("### 🚨 Complaint Areas")
        if neg_categories.empty:
            st.success("No category has enough negative reviews yet for a reliable AI diagnosis.")
        else:
            for category, count in neg_categories.items():
                cat_reviews = neg_reviews[neg_reviews["category"] == category]
                samples = select_representative_samples(cat_reviews["review_body"])
                render_category_block(category, count, samples, "negative", "🔍")

        st.markdown("---")

        st.markdown("### 🌟 Core Strengths")
        if pos_categories.empty:
            st.info("No category has enough positive reviews yet for a reliable AI synthesis.")
        else:
            for category, count in pos_categories.items():
                cat_reviews = pos_reviews[pos_reviews["category"] == category]
                samples_pos = select_representative_samples(cat_reviews["review_body"])
                render_category_block(category, count, samples_pos, "positive", "✨")

        st.markdown("---")
        if st.button("🗑️ Clear all generated insights", help="Clears everything you've generated in this session, plus the underlying 1-hour cache"):
            st.session_state.qa_insights_cache = {}
            generate_qa_insight_cached.clear()
            st.rerun()
    else:
        st.info("Load review data to view actionable QA insights.")

# -------------------------------------------------------------------
# Tab 3: AI Review Assistant
# -------------------------------------------------------------------
with tab_assistant:
    st.subheader("🤖 AI Customer Sentiment Assistant")
    st.markdown("Ask natural language questions about customer complaints, setup friction, print quality, or specific printer models.")
    st.caption(f"Answering within scope: **{selected_model if 'selected_model' in locals() else 'All Models'}** (matches the Executive Dashboard filter above)")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Hello! I am your Review Intelligence Assistant. Ask me anything like: *'What are the main issues with printer setup?'*"}
        ]

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            sources = msg.get("sources")
            if sources:
                with st.expander(f"📄 {len(sources)} source review(s) used"):
                    for src in sources:
                        st.markdown(
                            f"<div class='source-chip'><b>{src['model']}</b> "
                            f"— {src['sentiment']}<br>{src['excerpt']}</div>",
                            unsafe_allow_html=True
                        )

    user_query = st.chat_input("Ask a question about printer feedback...")

    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing review dataset with AI..."):
                reviews_context = filtered_reviews if 'filtered_reviews' in locals() else raw_df
                scope_label = selected_model if 'selected_model' in locals() else "All Models"

                answer, matched = answer_review_question(user_query, reviews_context, scope_label)

                sources = []
                if not matched.empty:
                    for _, row in matched.head(5).iterrows():
                        body = str(row.get("review_body", ""))
                        sources.append({
                            "model": row.get("model_name", "Unknown"),
                            "sentiment": row.get("sentiment", "Unknown"),
                            "excerpt": (body[:180] + "…") if len(body) > 180 else body
                        })

                st.markdown(answer)
                if sources:
                    with st.expander(f"📄 {len(sources)} source review(s) used"):
                        for src in sources:
                            st.markdown(
                                f"<div class='source-chip'><b>{src['model']}</b> "
                                f"— {src['sentiment']}<br>{src['excerpt']}</div>",
                                unsafe_allow_html=True
                            )

                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources
                })

# -------------------------------------------------------------------
# Tab 4: Admin Console (admin only)
# -------------------------------------------------------------------
if IS_ADMIN and tab_admin is not None:
    with tab_admin:
        st.subheader("🛠️ Scraper Pipelines")
        st.caption(
            "Each source has two steps that must run in order: scrape the raw reviews first, "
            "then classify + post them to the backend. Both launch in a separate terminal window "
            "— you'll still complete any manual login/captcha steps the scraper asks for there."
        )

        products = load_scraper_products()

        pipe_col1, pipe_col2 = st.columns(2)

        with pipe_col1:
            with st.container(border=True):
                st.markdown("#### 🛒 Amazon Pipeline")

                amz_models = [p["model_name"] for p in products.get("amazon", [])]
                amz_choice = st.selectbox(
                    "Model to scrape", ["All Amazon models"] + amz_models, key="amz_model_choice"
                )
                amz_target = None if amz_choice == "All Amazon models" else amz_choice

                st.markdown("**Step 1 — Scrape**")
                st.caption("`amazon_reviews_scraper.py`" + (f" — {amz_target}" if amz_target else ""))
                if st.button("▶️ Launch Amazon Scrape", use_container_width=True, key="launch_amz_scrape"):
                    ok, msg = launch_scraper_script("amazon_reviews_scraper.py", amz_target)
                    st.success(msg) if ok else st.error(msg)

                st.markdown("**Step 2 — Classify & Post**")
                st.caption("`amazon_reviews_to_highlights.py` (always processes the full scraped JSON)")
                if st.button("▶️ Launch Amazon Classify & Post", use_container_width=True, key="launch_amz_post"):
                    ok, msg = launch_scraper_script("amazon_reviews_to_highlights.py")
                    st.success(msg) if ok else st.error(msg)

        with pipe_col2:
            with st.container(border=True):
                st.markdown("#### 🖨️ HP.com Pipeline")

                hp_models = [p["model_name"] for p in products.get("hp", [])]
                hp_choice = st.selectbox(
                    "Model to scrape", ["All HP.com models"] + hp_models, key="hp_model_choice"
                )
                hp_target = None if hp_choice == "All HP.com models" else hp_choice

                st.markdown("**Step 1 — Scrape**")
                st.caption("`hp_reviews_scraper.py`" + (f" — {hp_target}" if hp_target else ""))
                if st.button("▶️ Launch HP Scrape", use_container_width=True, key="launch_hp_scrape"):
                    ok, msg = launch_scraper_script("hp_reviews_scraper.py", hp_target)
                    st.success(msg) if ok else st.error(msg)

                st.markdown("**Step 2 — Classify & Post**")
                st.caption("`hp_reviews_to_highlights.py` (always processes the full scraped JSON)")
                if st.button("▶️ Launch HP Classify & Post", use_container_width=True, key="launch_hp_post"):
                    ok, msg = launch_scraper_script("hp_reviews_to_highlights.py")
                    st.success(msg) if ok else st.error(msg)

        st.markdown("---")
        st.markdown("#### ➕ Add a New Product")
        st.caption("Adds to products.json. Doesn't scrape anything by itself — pick the new model in the dropdown above afterward and launch its scrape.")

        with st.form("add_product_form", clear_on_submit=True):
            new_source = st.selectbox("Source", ["amazon", "hp"])
            new_model_name = st.text_input("Model name (exact, used for grouping everywhere)")
            new_url = st.text_input(
                "Product page URL",
                help="Amazon: the /product-reviews/... URL. HP.com: the product page URL ending in #review-section."
            )
            add_submitted = st.form_submit_button("Add Product")

            if add_submitted:
                if not new_model_name.strip() or not new_url.strip():
                    st.error("Both model name and URL are required.")
                else:
                    products.setdefault(new_source, [])
                    if any(p["model_name"] == new_model_name.strip() for p in products[new_source]):
                        st.error(f"A {new_source} product named '{new_model_name}' already exists.")
                    else:
                        products[new_source].append({
                            "model_name": new_model_name.strip(),
                            "url": new_url.strip()
                        })
                        save_scraper_products(products)
                        st.success(f"Added '{new_model_name}' to {new_source}. Select it above to scrape it.")
                        st.rerun()

        with st.expander("📋 Current products"):
            for source_key, label in [("amazon", "Amazon"), ("hp", "HP.com")]:
                st.markdown(f"**{label}**")
                for p in products.get(source_key, []):
                    st.markdown(f"- {p['model_name']}")
                    st.caption(p['url'])

        st.markdown("---")
        with st.expander("Other / manual scripts"):
            st.caption("Older or standalone scripts not part of the two main pipelines above.")
            if st.button("▶️ Launch highlights_scraper.py", key="launch_legacy_highlights"):
                ok, msg = launch_scraper_script("highlights_scraper.py")
                st.success(msg) if ok else st.error(msg)