import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Printer Review Intelligence Platform",
    layout="wide"
)

# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown("""
<style>
.main {
    background-color: #F5F7FA;
}

.main-title {
    background-color: #0F172A;
    padding: 20px;
    border-radius: 15px;
    text-align: center;
    color: white;
    font-size: 40px;
    font-weight: bold;
    margin-bottom: 10px;
}

.sub-title {
    text-align: center;
    color: #475569;
    font-size: 20px;
    margin-bottom: 25px;
}

[data-testid="stMetric"] {
    background: #f2f6fc;
    border: 1px solid #1F2937;
    padding: 10px;
    border-radius: 18px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# HEADER
# =====================================================

st.markdown(
    '<div class="main-title">🖨️ Printer Review Intelligence Platform</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">QA Analytics Dashboard</div>',
    unsafe_allow_html=True
)

# =====================================================
# FETCH DATA
# =====================================================

try:
    response = requests.get(
        "http://127.0.0.1:8000/analytics/reviews",
        timeout=10
    )

    data = response.json()
    df = pd.DataFrame(data)

except Exception as e:
    st.error(f"Unable to connect to FastAPI.\n\n{e}")
    st.stop()

# =====================================================
# INITIAL DATA
# =====================================================

filtered_df = df.copy()

# =====================================================
# KPI SECTION
# =====================================================

total_reviews = len(filtered_df)

positive_reviews = len(
    filtered_df[
        filtered_df["sentiment"] == "POSITIVE"
    ]
)

negative_reviews = len(
    filtered_df[
        filtered_df["sentiment"] == "NEGATIVE"
    ]
)

neutral_reviews = len(
    filtered_df[
        filtered_df["sentiment"] == "NEUTRAL"
    ]
)

issue_df = filtered_df.explode("issues")

issue_df = issue_df[
    issue_df["issues"].notna()
]

if len(issue_df) > 0:
    top_issue = issue_df["issues"].mode()[0]
else:
    top_issue = "No Issues Found"

col1, col2, col3, col4 = st.columns(4)

col1.metric("📊 Total Reviews", total_reviews)
col2.metric("🟢 Positive", positive_reviews)
col3.metric("🔴 Negative", negative_reviews)
col4.metric("🟡 Neutral", neutral_reviews)

st.markdown(
    f"### 🔥 Top Reported Issue: `{top_issue}`"
)

st.divider()

# =====================================================
# FILTERS
# =====================================================

st.subheader("🎛️ Filters")

f1, f2, f3 = st.columns(3)

with f1:
    selected_model = st.selectbox(
        "Printer Model",
        ["All"] + sorted(
            df["model_name"].dropna().unique().tolist()
        )
    )

with f2:
    selected_sentiment = st.selectbox(
        "Sentiment",
        ["All", "POSITIVE", "NEGATIVE", "NEUTRAL"]
    )

issue_df = df.explode("issues")

unique_issues = sorted(
    issue_df["issues"]
    .dropna()
    .unique()
    .tolist()
)

with f3:
    selected_category = st.selectbox(
        "Issue Category",
        ["All"] + unique_issues
    )

# =====================================================
# APPLY FILTERS
# =====================================================

if selected_model != "All":
    filtered_df = filtered_df[
        filtered_df["model_name"] == selected_model
    ]

if selected_sentiment != "All":
    filtered_df = filtered_df[
        filtered_df["sentiment"] == selected_sentiment
    ]

if selected_category != "All":
    filtered_df = filtered_df[
        filtered_df["issues"].apply(
            lambda x: (
                selected_category in x
                if isinstance(x, list)
                else False
            )
        )
    ]

# =====================================================
# ISSUE DISTRIBUTION
# =====================================================

issue_chart_df = filtered_df.explode("issues")

issue_chart_df = issue_chart_df[
    issue_chart_df["issues"].notna()
]

issue_chart = (
    issue_chart_df
    .groupby("issues")
    .size()
    .reset_index(name="count")
)

if not issue_chart.empty:

    issue_fig = px.bar(
        issue_chart,
        x="issues",
        y="count",
        title="📊 Issue Distribution",
        text_auto=True
    )

    issue_fig.update_layout(height=400)

else:
    issue_fig = None

# =====================================================
# SENTIMENT DISTRIBUTION
# =====================================================

sentiment_chart = (
    filtered_df
    .groupby("sentiment")
    .size()
    .reset_index(name="count")
)

pie_fig = px.pie(
    sentiment_chart,
    names="sentiment",
    values="count",
    title="😊 Sentiment Distribution",
    color="sentiment",
    color_discrete_map={
        "POSITIVE": "#34D399",
        "NEGATIVE": "#F87171",
        "NEUTRAL": "#FBBF24"
    }
)

pie_fig.update_layout(height=400)

# =====================================================
# CHARTS
# =====================================================

c1, c2 = st.columns(2)

with c1:
    if issue_fig:
        st.plotly_chart(
            issue_fig,
            use_container_width=True
        )

with c2:
    st.plotly_chart(
        pie_fig,
        use_container_width=True
    )

# =====================================================
# MODEL COMPARISON
# =====================================================

model_chart = (
    filtered_df
    .groupby("model_name")
    .size()
    .reset_index(name="count")
)

model_fig = px.bar(
    model_chart,
    x="count",
    y="model_name",
    orientation="h",
    title="🖨️ Model-wise Review Comparison",
    text_auto=True
)

st.plotly_chart(
    model_fig,
    use_container_width=True
)

# =====================================================
# REVIEW SEARCH
# =====================================================

st.divider()

st.subheader("📋 Review Details")

review_df = filtered_df.copy()

search_text = st.text_input(
    "🔍 Search Reviews"
)

if search_text:

    review_df = review_df[
        review_df["review"]
        .str.contains(
            search_text,
            case=False,
            na=False
        )
    ]

st.dataframe(
    review_df[
        [
            "model_name",
            "rating",
            "source",
            "sentiment",
            "issues",
            "review"
        ]
    ],
    use_container_width=True
)

# =====================================================
# DOWNLOAD REPORT
# =====================================================

st.divider()

st.subheader("📥 Download Analytics Report")

csv = review_df.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    label="Download CSV Report",
    data=csv,
    file_name="printer_review_analytics.csv",
    mime="text/csv"
)