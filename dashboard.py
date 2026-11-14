
import os
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px

from dotenv import load_dotenv
from sqlalchemy import create_engine, URL, text


# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="GitHub Trends Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("📊 GitHub Repository Trends Analytics")
st.caption(
    "Analyze repository popularity, programming languages "
    "and historical growth using GitHub API data."
)


# --------------------------------------------------
# 2. DATABASE CONNECTION
# --------------------------------------------------


# --------------------------------------------------
# 2. DATABASE CONNECTION
# --------------------------------------------------

# Local development support
load_dotenv(
    Path(__file__).resolve().parent / ".env",
    override=True
)

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "4000"))
DB_NAME = os.getenv("DB_NAME", "github_analytics")
DB_CA_PATH = os.getenv("DB_CA_PATH", "ca.pem")

if not DB_USER or not DB_PASSWORD or not DB_HOST:
    st.error("Database credentials are missing.")
    st.stop()

ca_path = Path(DB_CA_PATH)

if not ca_path.is_absolute():
    ca_path = Path(__file__).resolve().parent / ca_path

if not ca_path.exists():
    st.error("TiDB CA certificate not found.")
    st.stop()

db_url = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)

engine = create_engine(
    db_url,
    connect_args={
        "ssl_verify_cert": True,
        "ssl_verify_identity": True,
        "ssl_ca": str(ca_path)
    },
    pool_recycle=300,
    pool_pre_ping=True
)


# --------------------------------------------------
# 3. FETCH HISTORICAL DATA FROM MYSQL
# --------------------------------------------------

query = text("""
    SELECT
        repository,
        language,
        stars,
        forks,
        open_issues,
        repository_url,
        collected_at
    FROM repository_snapshots
    ORDER BY collected_at DESC
""")

try:
    with engine.connect() as connection:
        all_df = pd.read_sql_query(query, connection)
finally:
    engine.dispose()


if all_df.empty:
    st.warning("No repository data found. Run main.py first.")
    st.stop()


# --------------------------------------------------
# 4. PREPARE DATA
# --------------------------------------------------

all_df["collected_at"] = pd.to_datetime(
    all_df["collected_at"]
)

latest_time = all_df["collected_at"].max()

df = all_df[
    all_df["collected_at"] == latest_time
].copy()


# --------------------------------------------------
# 5. SIDEBAR FILTERS
# --------------------------------------------------

st.sidebar.header("Dashboard Filters")

languages = sorted(
    df["language"].dropna().unique().tolist()
)

selected_language = st.sidebar.selectbox(
    "Select Programming Language",
    ["All"] + languages
)

filtered_df = df.copy()

if selected_language != "All":
    filtered_df = filtered_df[
        filtered_df["language"] == selected_language
    ]


# --------------------------------------------------
# 6. KEY PERFORMANCE INDICATORS
# --------------------------------------------------

st.subheader("Repository Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total Repositories",
    f"{len(filtered_df):,}"
)

col2.metric(
    "Total Stars",
    f"{filtered_df['stars'].sum():,}"
)

col3.metric(
    "Total Forks",
    f"{filtered_df['forks'].sum():,}"
)

col4.metric(
    "Open Issues",
    f"{filtered_df['open_issues'].sum():,}"
)

st.divider()


# --------------------------------------------------
# 7. TOP 10 REPOSITORIES
# --------------------------------------------------

st.subheader("🏆 Top 10 Repositories by Stars")

top_repos = filtered_df.nlargest(
    10,
    "stars"
)

fig1 = px.bar(
    top_repos,
    x="stars",
    y="repository",
    orientation="h",
    title="Most Popular GitHub Repositories",
    labels={
        "stars": "Number of Stars",
        "repository": "Repository"
    },
    hover_data=["language", "forks", "open_issues"]
)

fig1.update_layout(
    yaxis={"categoryorder": "total ascending"}
)

st.plotly_chart(
    fig1,
    use_container_width=True
)


# --------------------------------------------------
# 8. PROGRAMMING LANGUAGE ANALYSIS
# --------------------------------------------------

st.subheader("💻 Programming Language Analysis")

language_stats = (
    df.groupby("language")
    .agg(
        total_repositories=("repository", "count"),
        average_stars=("stars", "mean"),
        total_forks=("forks", "sum")
    )
    .reset_index()
)

col1, col2 = st.columns(2)

with col1:

    fig2 = px.pie(
        language_stats,
        names="language",
        values="total_repositories",
        title="Repositories by Programming Language"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

with col2:

    fig3 = px.bar(
        language_stats,
        x="language",
        y="average_stars",
        title="Average Stars by Programming Language",
        labels={
            "language": "Programming Language",
            "average_stars": "Average Stars"
        }
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )


# --------------------------------------------------
# 9. HISTORICAL REPOSITORY GROWTH
# --------------------------------------------------

st.divider()

st.subheader("📈 Historical Repository Growth")

repo_options = sorted(
    all_df["repository"].dropna().unique().tolist()
)

selected_repo = st.selectbox(
    "Select Repository for Growth Analysis",
    repo_options
)

history = all_df[
    all_df["repository"] == selected_repo
].sort_values("collected_at")

history = history.drop_duplicates(
    subset=["collected_at"],
    keep="last"
)

if history["collected_at"].nunique() < 2:

    st.info(
        "Only one snapshot is available for this repository. "
        "Run main.py again later to collect another snapshot."
    )

else:

    first_snapshot = history.iloc[0]
    latest_snapshot = history.iloc[-1]

    star_growth = (
        latest_snapshot["stars"] - first_snapshot["stars"]
    )

    fork_growth = (
        latest_snapshot["forks"] - first_snapshot["forks"]
    )

    col1, col2 = st.columns(2)

    col1.metric(
        "Star Change",
        f"{star_growth:+,}"
    )

    col2.metric(
        "Fork Change",
        f"{fork_growth:+,}"
    )

    fig4 = px.line(
        history,
        x="collected_at",
        y="stars",
        markers=True,
        title=f"Star Growth: {selected_repo}",
        labels={
            "collected_at": "Collection Date",
            "stars": "Number of Stars"
        }
    )

    st.plotly_chart(
        fig4,
        use_container_width=True
    )

    fig5 = px.line(
        history,
        x="collected_at",
        y="forks",
        markers=True,
        title=f"Fork Growth: {selected_repo}",
        labels={
            "collected_at": "Collection Date",
            "forks": "Number of Forks"
        }
    )

    st.plotly_chart(
        fig5,
        use_container_width=True
    )


# --------------------------------------------------
# 10. REPOSITORY DETAILS
# --------------------------------------------------

st.divider()

st.subheader("📋 Repository Details")

display_df = filtered_df.sort_values(
    "stars",
    ascending=False
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# 11. FOOTER
# --------------------------------------------------

st.caption(
    "Data Source: GitHub REST API | "
    f"Latest Snapshot: {latest_time}"
)

st.caption(
    "GitHub Repository Trends Analytics System"
)
