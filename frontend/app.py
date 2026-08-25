import streamlit as st

from services.api_client import get_analytics

st.set_page_config(
    page_title="Review Intelligence Platform",
    layout="wide"
)

st.title("📊 Product Review Intelligence Dashboard")

data = get_analytics()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Reviews",
        data["total_reviews"]
    )

with col2:
    st.metric(
        "Positive",
        data["positive_reviews"]
    )

with col3:
    st.metric(
        "Negative",
        data["negative_reviews"]
    )

with col4:
    st.metric(
        "Neutral",
        data["neutral_reviews"]
    )

st.divider()

# st.subheader("Issue Distribution")

# st.json(
#     data["issue_distribution"]
# )