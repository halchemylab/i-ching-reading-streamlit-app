import html

import pandas as pd
import streamlit as st

from constants import HEXAGRAM_THEME_SUMMARIES
from file_handler import journal_to_markdown


def render_empty_journal_sidebar():
    """Renders a quiet sidebar state before any readings have been saved."""
    with st.sidebar:
        st.header("Journal Tools")
        st.info("Save a reading to unlock search, filters, patterns, and exports.")


def render_journal_sidebar(journal_df, iching_data):
    """Renders sidebar filters and exports, returning the filtered journal."""
    filtered_df = journal_df.copy()
    valid_dates = filtered_df["Date Parsed"].dropna()
    default_date_range = None

    if not valid_dates.empty:
        default_date_range = (valid_dates.min().date(), valid_dates.max().date())

    with st.sidebar:
        stats_container = st.container()

    with st.sidebar:
        st.divider()
        st.subheader("Filters")

        if st.button("Clear filters", use_container_width=True):
            st.session_state.journal_search = ""
            st.session_state.journal_primary = "All"
            st.session_state.journal_evolving = "All"
            st.session_state.journal_ai_only = False
            st.session_state.journal_changing_only = False
            st.session_state.journal_favorites_only = False
            st.session_state.journal_show_archived = False
            st.session_state.journal_sort = "Newest first"
            if default_date_range:
                st.session_state.journal_date_range = default_date_range
            st.rerun()

        search_query = st.text_input(
            "Search readings",
            placeholder="Question or AI text",
            key="journal_search",
        )

        if not valid_dates.empty:
            min_date, max_date = default_date_range
            date_range = st.date_input(
                "Date range",
                value=default_date_range,
                min_value=min_date,
                max_value=max_date,
                key="journal_date_range",
            )
        else:
            date_range = None

        primary_options = ["All"] + sorted(
            [value for value in filtered_df["Primary Hexagram"].dropna().unique()]
        )
        evolving_options = ["All"] + sorted(
            [value for value in filtered_df["Evolving Hexagram"].dropna().unique()]
        )

        if st.session_state.get("journal_primary") not in primary_options:
            st.session_state.journal_primary = "All"
        if st.session_state.get("journal_evolving") not in evolving_options:
            st.session_state.journal_evolving = "All"

        primary_filter = st.selectbox("Primary hexagram", primary_options, key="journal_primary")
        evolving_filter = st.selectbox("Evolving hexagram", evolving_options, key="journal_evolving")
        favorites_only = st.checkbox("Favorites only", key="journal_favorites_only")
        show_archived = st.checkbox("Show archived readings", key="journal_show_archived")
        ai_only = st.checkbox("With AI contemplation only", key="journal_ai_only")
        changing_only = st.checkbox("With changing lines only", key="journal_changing_only")
        sort_order = st.selectbox("Sort", ["Newest first", "Oldest first"], key="journal_sort")

    filtered_df = apply_journal_filters(
        filtered_df,
        search_query=search_query,
        date_range=date_range,
        primary_filter=primary_filter,
        evolving_filter=evolving_filter,
        favorites_only=favorites_only,
        show_archived=show_archived,
        ai_only=ai_only,
        changing_only=changing_only,
        sort_order=sort_order,
    )

    render_journal_sidebar_summary(journal_df, filtered_df, stats_container, iching_data)
    render_journal_sidebar_exports(filtered_df)

    return filtered_df


def apply_journal_filters(
    journal_df,
    search_query="",
    date_range=None,
    primary_filter="All",
    evolving_filter="All",
    favorites_only=False,
    show_archived=False,
    ai_only=False,
    changing_only=False,
    sort_order="Newest first",
):
    """Applies journal filters independently of Streamlit widgets."""
    filtered_df = journal_df.copy()

    if not show_archived:
        filtered_df = filtered_df[~filtered_df["Archived"]]

    if search_query:
        searchable_text = (
            filtered_df["Question"].fillna("") + " " +
            filtered_df["AI Interpretation"].fillna("")
        )
        filtered_df = filtered_df[
            searchable_text.str.contains(search_query, case=False, na=False)
        ]

    if date_range and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df["Date Parsed"].dt.date >= start_date) &
            (filtered_df["Date Parsed"].dt.date <= end_date)
        ]

    if primary_filter != "All":
        filtered_df = filtered_df[filtered_df["Primary Hexagram"] == primary_filter]

    if evolving_filter != "All":
        filtered_df = filtered_df[filtered_df["Evolving Hexagram"] == evolving_filter]

    if favorites_only:
        filtered_df = filtered_df[filtered_df["Favorite"]]

    if ai_only:
        filtered_df = filtered_df[filtered_df["Has AI Contemplation"]]

    if changing_only:
        filtered_df = filtered_df[filtered_df["Has Changing Lines"]]

    return filtered_df.sort_values(
        "Date Parsed",
        ascending=(sort_order == "Oldest first"),
        na_position="last",
    )


def render_journal_sidebar_summary(journal_df, filtered_df, container, iching_data):
    """Shows compact journal patterns in the sidebar."""
    with container:
        st.subheader("Stats")
        st.metric("Total readings", len(journal_df))

        if not filtered_df.empty:
            hexagram_counts = filtered_df["Primary Hexagram"].value_counts().head(3)
            if not hexagram_counts.empty:
                st.caption("Most common:")
                st.markdown(build_top_hexagram_bars(hexagram_counts), unsafe_allow_html=True)
                theme_title, theme_text = get_recurring_theme(filtered_df, iching_data)
                if theme_title and theme_text:
                    st.caption(f"Recurring theme: {theme_title}")
                    st.markdown(
                        f"<p class='theme-summary-text'>{html.escape(theme_text)}</p>",
                        unsafe_allow_html=True,
                    )

            latest_date = filtered_df["Date Parsed"].dropna().max()
            if pd.notna(latest_date):
                st.caption(f"Most recent: {latest_date.strftime('%Y-%m-%d')}")


def get_recurring_theme(filtered_df, iching_data):
    """Returns a deterministic theme summary for the most common primary hexagram."""
    primary_numbers = filtered_df["Primary Hexagram Number"].dropna()
    if primary_numbers.empty:
        return None, None

    hexagram_number = int(primary_numbers.value_counts().index[0])
    hexagram = iching_data.get(str(hexagram_number))
    if not hexagram:
        return None, None

    theme_text = HEXAGRAM_THEME_SUMMARIES.get(
        hexagram_number,
        "Your journal has recently returned to this hexagram's themes. Revisit its Judgment and Image for the pattern beneath these questions.",
    )

    return hexagram["name_en"], theme_text


def build_top_hexagram_bars(hexagram_counts):
    """Builds a compact horizontal top-3 hexagram chart for the sidebar."""
    max_count = int(hexagram_counts.iloc[0])
    rows = []

    for label, count in hexagram_counts.items():
        count = int(count)
        width = 100 if max_count == 0 else int((count / max_count) * 100)
        safe_label = html.escape(str(label))
        rows.append(
            f'<div class="hexagram-stat-row">'
            f'<div class="hexagram-stat-label">'
            f'<span>{safe_label}</span>'
            f'<strong>{count}</strong>'
            f'</div>'
            f'<div class="hexagram-stat-track">'
            f'<div class="hexagram-stat-fill" style="width: {width}%;"></div>'
            f'</div>'
            f'</div>'
        )

    return (
        '<style>'
        '.hexagram-stat-row{margin:0.65rem 0;}'
        '.hexagram-stat-label{align-items:baseline;display:flex;font-size:0.86rem;'
        'gap:0.5rem;justify-content:space-between;line-height:1.2;}'
        '.hexagram-stat-label span{overflow-wrap:anywhere;}'
        '.hexagram-stat-label strong{color:#6c757d;flex:0 0 auto;font-size:0.8rem;}'
        '.hexagram-stat-track{background:rgba(108,117,125,0.18);border-radius:999px;'
        'height:0.45rem;margin-top:0.25rem;overflow:hidden;}'
        '.hexagram-stat-fill{background:#ffc107;border-radius:999px;height:100%;}'
        '.theme-summary-text{color:#000;font-size:0.9rem;line-height:1.35;margin:0.25rem 0 0;}'
        '</style>'
        f'<div>{"".join(rows)}</div>'
    )


def render_journal_sidebar_exports(filtered_df):
    """Adds filtered journal export actions to the sidebar."""
    export_df = filtered_df.drop(columns=["Date Parsed"], errors="ignore")

    with st.sidebar:
        st.divider()
        st.subheader("Export")
        st.download_button(
            "Download filtered CSV",
            data=export_df.to_csv(index=False).encode("utf-8"),
            file_name="i_ching_journal_filtered.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=filtered_df.empty,
        )
        st.download_button(
            "Download Markdown",
            data=journal_to_markdown(filtered_df).encode("utf-8"),
            file_name="i_ching_journal.md",
            mime="text/markdown",
            use_container_width=True,
            disabled=filtered_df.empty,
        )
