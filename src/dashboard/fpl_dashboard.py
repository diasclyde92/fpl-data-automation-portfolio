"""Interactive Fantasy Premier League Analytics Dashboard built with Streamlit.

Consumes validated data via FPLAnalytics and FPLStorage.
No direct SQL queries or duplicated analytical algorithms exist here.
"""

from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

# Ensure repository root is on path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.analytics.fpl_analytics import FPLAnalytics, FPLAnalyticsResult
from src.dashboard.fpl_dashboard_service import (
    DashboardFilterCriteria,
    filter_players_dataframe,
    get_fpl_analytics_bundle,
    get_player_card_details,
)
from src.storage.fpl_storage import FPLStorage


@st.cache_data(show_spinner=False)
def load_cached_data_bundle(db_path_str: str) -> tuple[pd.DataFrame, dict, datetime | None]:
    """Cache data loading and analytics to optimize UI re-renders."""
    df, result, latest_scraped = get_fpl_analytics_bundle(db_path=db_path_str)
    return df, result.to_dict(), latest_scraped


def render_kpi_overview(summary_dict: dict) -> None:
    """Render high-level KPI cards at the top of the dashboard."""
    st.markdown("### 📌 KPI Overview")
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

    total_players = summary_dict.get("total_players", 0)
    avg_price = summary_dict.get("average_price")
    tot_points = summary_dict.get("total_points", 0)
    avg_points = summary_dict.get("average_points")
    highest_points = summary_dict.get("highest_points")
    avg_ownership = summary_dict.get("average_ownership")

    kpi1.metric("Total Players", f"{total_players:,}")
    kpi2.metric("Average Price", f"£{avg_price:.2f}m" if avg_price is not None else "N/A")
    kpi3.metric("Total Points", f"{tot_points:,}")
    kpi4.metric("Average Points", f"{avg_points:.1f}" if avg_points is not None else "N/A")
    kpi5.metric("Highest Points", f"{highest_points}" if highest_points is not None else "N/A")
    kpi6.metric("Average Ownership", f"{avg_ownership:.1f}%" if avg_ownership is not None else "N/A")


def render_top_players_section(analytics: FPLAnalytics, df: pd.DataFrame) -> None:
    """Render top player tables with selectable display depth."""
    st.markdown("### 🏆 Top Player Performance")
    top_n = st.radio(
        "Display count:",
        options=[5, 10, 20],
        index=0,
        horizontal=True,
        key="top_players_n_selector",
    )

    tab_points, tab_value, tab_form, tab_goals, tab_assists = st.tabs(
        ["Total Points", "Value (PPM)", "Current Form", "Top Goals", "Top Assists"]
    )

    format_cols = {
        "price": "£{:.1f}m",
        "points_per_million": "{:.2f}",
        "form": "{:.1f}",
        "selected_by_percent": "{:.1f}%",
    }

    def display_top_table(column_name: str) -> None:
        top_records = analytics.get_top_by_column(df, column=column_name, n=top_n)
        if top_records:
            tdf = pd.DataFrame(top_records)
            display_cols = [
                "web_name", "team", "position", "price", "total_points",
                "points_per_million", "form", "goals", "assists", "selected_by_percent"
            ]
            valid_cols = [c for c in display_cols if c in tdf.columns]
            st.dataframe(
                tdf[valid_cols].style.format({c: fmt for c, fmt in format_cols.items() if c in valid_cols}),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No player records available.")

    with tab_points:
        st.caption(f"Top {top_n} players ranked by cumulative total points.")
        display_top_table("total_points")

    with tab_value:
        st.caption(f"Top {top_n} value players ranked by points per million (£m).")
        display_top_table("points_per_million")

    with tab_form:
        st.caption(f"Top {top_n} in-form players based on recent gameweek performance.")
        display_top_table("form")

    with tab_goals:
        st.caption(f"Top {top_n} goalscorers across all competitions.")
        display_top_table("goals")

    with tab_assists:
        st.caption(f"Top {top_n} playmakers ranked by assists provided.")
        display_top_table("assists")


def render_value_analysis(analytics: FPLAnalytics, df: pd.DataFrame) -> None:
    """Render value metrics, leaderboard, and price vs points scatter plot."""
    st.markdown("### 💎 Value Analysis (Points per Million)")
    st.write(
        "Value efficiency identifies players providing the highest return on budget "
        "investment (Total Points / Current Price in £m)."
    )

    col_chart, col_table = st.columns([1.2, 1])

    with col_chart:
        st.markdown("#### Price vs Total Points")
        if not df.empty:
            scatter_df = df[["price", "total_points", "web_name", "team", "position", "points_per_million"]].copy()
            st.scatter_chart(
                scatter_df,
                x="price",
                y="total_points",
                color="position",
                size="points_per_million",
            )
        else:
            st.info("No data available for scatter plot.")

    with col_table:
        st.markdown("#### Top 10 Value Leaders")
        top_val = analytics.get_top_by_column(df, "points_per_million", n=10)
        if top_val:
            vdf = pd.DataFrame(top_val)[["web_name", "team", "position", "price", "total_points", "points_per_million"]]
            st.dataframe(
                vdf.style.format({"price": "£{:.1f}m", "points_per_million": "{:.2f}"}),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No value data available.")


def render_team_and_position_analysis(analytics: FPLAnalytics, df: pd.DataFrame) -> None:
    """Render team and position breakdowns using native Streamlit bar charts."""
    st.markdown("### 🏟️ Team & Position Breakdown")
    col_team, col_pos = st.columns(2)

    with col_team:
        st.markdown("#### Team Performance")
        team_summary = analytics.get_team_summary(df)
        if not team_summary.empty:
            st.bar_chart(team_summary["total_points"])
            with st.expander("View Team Summary Table"):
                st.dataframe(
                    team_summary.style.format({"average_price": "£{:.2f}m"}),
                    use_container_width=True,
                )
        else:
            st.info("No team data available.")

    with col_pos:
        st.markdown("#### Position Breakdown")
        pos_summary = analytics.get_position_summary(df)
        if not pos_summary.empty:
            st.bar_chart(pos_summary["total_points"])
            with st.expander("View Position Summary Table"):
                st.dataframe(
                    pos_summary.style.format({
                        "average_points": "{:.1f}",
                        "average_price": "£{:.2f}m",
                    }),
                    use_container_width=True,
                )
        else:
            st.info("No position data available.")


def render_player_explorer(df: pd.DataFrame) -> None:
    """Render individual player inspection module with detailed statistical scorecard."""
    st.markdown("### 🔍 Player Explorer")

    if df.empty:
        st.info("No players available for exploration.")
        return

    player_options = {}
    for _, row in df.sort_values(by="total_points", ascending=False).iterrows():
        label = f"{row['web_name']} ({row['team']} - {row['position']}) | {row['total_points']} pts"
        player_options[label] = int(row["id"])

    selected_label = st.selectbox("Select Player:", options=list(player_options.keys()))
    if not selected_label:
        return

    player_id = player_options[selected_label]
    player = get_player_card_details(df, player_id)

    if not player:
        st.warning("Player details not found.")
        return

    # Header details
    full_name = f"{player.get('first_name', '')} {player.get('second_name', '')}".strip()
    st.markdown(f"#### **{player.get('web_name')}** ({full_name})")

    # Metrics row 1
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Club", player.get("team"))
    m2.metric("Position", player.get("position"))
    m3.metric("Price", f"£{player.get('price', 0.0):.1f}m")
    m4.metric("Total Points", player.get("total_points", 0))
    m5.metric("Gameweek Pts", player.get("event_points", 0))
    m6.metric("Form", f"{player.get('form', 0.0):.1f}")

    # Metrics row 2
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    s1.metric("Ownership", f"{player.get('selected_by_percent', 0.0):.1f}%")
    s2.metric("Goals", player.get("goals", 0))
    s3.metric("Assists", player.get("assists", 0))
    s4.metric("Clean Sheets", player.get("clean_sheets", 0))
    s5.metric("Minutes", f"{player.get('minutes', 0):,}")
    s6.metric("Bonus Points", player.get("bonus", 0))


def render_data_quality_section(quality_dict: dict, db_path: str, latest_scraped: datetime | None) -> None:
    """Render technical pipeline health and data validation diagnostics."""
    with st.expander("🛠️ Technical Pipeline Status & Data Quality Audit", expanded=False):
        status_col, audit_col = st.columns(2)
        with status_col:
            st.markdown("**Pipeline Infrastructure**")
            st.write(f"- **Target Database**: `{db_path}`")
            st.write(f"- **Total Stored Records**: `{quality_dict.get('total_records', 0)}`")
            updated_str = latest_scraped.strftime("%Y-%m-%d %H:%M:%S UTC") if latest_scraped else "Never / Empty"
            st.write(f"- **Data Last Updated**: `{updated_str}`")
            status = "EMPTY" if quality_dict.get("is_empty") else "HEALTHY"
            st.write(f"- **Dataset Health**: `{status}`")

        with audit_col:
            st.markdown("**Data Integrity Checks**")
            st.write(f"- Missing Prices: `{quality_dict.get('missing_prices', 0)}`")
            st.write(f"- Missing Teams: `{quality_dict.get('missing_teams', 0)}`")
            st.write(f"- Missing Positions: `{quality_dict.get('missing_positions', 0)}`")
            st.write(f"- Duplicate IDs: `{quality_dict.get('duplicate_ids', 0)}`")


def main() -> None:
    """Main Streamlit dashboard application entrypoint."""
    st.set_page_config(
        page_title="FPL Analytics Dashboard",
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("Fantasy Premier League Analytics Dashboard")
    st.caption("Current FPL player performance, value and ownership analysis")

    db_path = "data/processed/fpl.db"
    df, result_dict, latest_scraped = load_cached_data_bundle(db_path)

    # Empty State Handling
    if df.empty or result_dict.get("quality", {}).get("is_empty"):
        st.warning("⚠️ No FPL data available in the database.")
        st.info(
            "Please run the FPL extraction pipeline first to populate the database:\n\n"
            "```bash\npython -m src.pipeline.fpl_pipeline --save-raw\n```"
        )
        render_data_quality_section(result_dict.get("quality", {}), db_path, latest_scraped)
        return

    analytics = FPLAnalytics(storage=FPLStorage(db_path=db_path))

    # Sidebar Filter Controls
    st.sidebar.header("Filter Players")

    all_positions = sorted(df["position"].dropna().unique().tolist())
    all_teams = sorted(df["team"].dropna().unique().tolist())
    all_statuses = sorted(df["status"].dropna().unique().tolist())

    selected_positions = st.sidebar.multiselect("Position", options=all_positions, default=[])
    selected_teams = st.sidebar.multiselect("Team", options=all_teams, default=[])
    selected_statuses = st.sidebar.multiselect("Availability Status", options=all_statuses, default=[])

    min_p = float(df["price"].min()) if not df.empty else 0.0
    max_p = float(df["price"].max()) if not df.empty else 15.0
    price_range = st.sidebar.slider("Price Range (£m)", min_value=min_p, max_value=max_p, value=(min_p, max_p), step=0.1)

    min_own = st.sidebar.slider("Min Ownership (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    min_mins = st.sidebar.slider("Min Minutes Played", min_value=0, max_value=int(df["minutes"].max()), value=0, step=90)

    criteria = DashboardFilterCriteria(
        positions=selected_positions if selected_positions else None,
        teams=selected_teams if selected_teams else None,
        statuses=selected_statuses if selected_statuses else None,
        min_price=price_range[0],
        max_price=price_range[1],
        min_ownership=min_own if min_own > 0 else None,
        min_minutes=min_mins if min_mins > 0 else None,
    )

    filtered_df = filter_players_dataframe(df, criteria)

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Matching Players**: {len(filtered_df)} / {len(df)}")
    if latest_scraped:
        st.sidebar.caption(f"Data snapshot: {latest_scraped.strftime('%Y-%m-%d %H:%M UTC')}")

    # Section 1: KPI Overview
    render_kpi_overview(result_dict.get("summary", {}))
    st.markdown("---")

    # Section 2 & 3: Top Players and Value Analysis
    render_top_players_section(analytics, filtered_df)
    st.markdown("---")
    render_value_analysis(analytics, filtered_df)
    st.markdown("---")

    # Section 4: Team & Position Breakdown
    render_team_and_position_analysis(analytics, filtered_df)
    st.markdown("---")

    # Section 5: Player Explorer
    render_player_explorer(filtered_df if not filtered_df.empty else df)
    st.markdown("---")

    # Section 6: Data Quality & Technical Status
    render_data_quality_section(result_dict.get("quality", {}), db_path, latest_scraped)


if __name__ == "__main__":
    main()
