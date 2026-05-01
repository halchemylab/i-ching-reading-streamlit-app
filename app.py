import streamlit as st
import random
import openai
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# --- Main Application ---
def main():
    """Main function to run the Streamlit app."""
    # --- CSS for Button Feel ---
    st.markdown("""
    <style>
        div[data-testid="stButton"] > button {
            transition: transform 150ms ease-in-out;
        }

        div[data-testid="stButton"] > button:hover {
            transform: scale(1.02);
        }

        div[data-testid="stButton"] > button:active {
            transform: scale(0.98);
        }
    </style>
    """, unsafe_allow_html=True)
    
    iching_data, binary_to_hex_map = load_iching_data()
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    client = None
    openai_enabled = True if api_key else False
    if openai_enabled:
        client = openai.OpenAI(api_key=api_key)

    if iching_data and binary_to_hex_map:
        render_main_ui(iching_data, binary_to_hex_map, openai_enabled, client)
        render_journal(iching_data)

import logging
# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, filename='app.log', filemode='a', format='%(name)s - %(levelname)s - %(message)s')


def render_journal(iching_data):
    """Renders the reading journal section, displaying past readings."""
    st.divider()
    st.header("Reading Journal")

    journal_df = load_journal()
    if journal_df.empty:
        logging.info("Journal file is empty or not found.")
        st.info("Your journal is empty. Saved readings will appear here.")
        render_empty_journal_sidebar()
        return

    journal_df = enrich_journal(journal_df, iching_data)
    filtered_df = render_journal_sidebar(journal_df)

    if filtered_df.empty:
        st.info("No saved readings match the current journal filters.")
        return

    for index, row in filtered_df.iterrows():
        reconstructed_reading = reconstruct_reading_from_row(row, iching_data)
        title_parts = [
            str(row["Date"]),
            str(row["Question"]),
            str(row.get("Primary Hexagram") or row["Primary Hexagram Number"]),
        ]

        if pd.notna(row.get("Evolving Hexagram")) and row.get("Evolving Hexagram"):
            title_parts[-1] = f"{title_parts[-1]} -> {row['Evolving Hexagram']}"

        with st.expander(" | ".join(title_parts)):
            st.caption(
                f"Lines: {row['Lines']} | "
                f"Changing lines: {'Yes' if row['Has Changing Lines'] else 'No'} | "
                f"AI contemplation: {'Yes' if row['Has AI Contemplation'] else 'No'}"
            )
            display_reading(reconstructed_reading, is_journal=True)
            if pd.notna(row['AI Interpretation']):
                st.markdown("**AI Contemplation:**")
                st.markdown(row['AI Interpretation'])


def render_empty_journal_sidebar():
    """Renders a quiet sidebar state before any readings have been saved."""
    with st.sidebar:
        st.header("Journal Tools")
        st.info("Save a reading to unlock search, filters, patterns, and exports.")


def render_journal_sidebar(journal_df):
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
        ai_only = st.checkbox("With AI contemplation only", key="journal_ai_only")
        changing_only = st.checkbox("With changing lines only", key="journal_changing_only")
        sort_order = st.selectbox("Sort", ["Newest first", "Oldest first"], key="journal_sort")

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

    if ai_only:
        filtered_df = filtered_df[filtered_df["Has AI Contemplation"]]

    if changing_only:
        filtered_df = filtered_df[filtered_df["Has Changing Lines"]]

    filtered_df = filtered_df.sort_values(
        "Date Parsed",
        ascending=(sort_order == "Oldest first"),
        na_position="last",
    )

    render_journal_sidebar_summary(journal_df, filtered_df, stats_container)
    render_journal_sidebar_exports(filtered_df)

    return filtered_df


def render_journal_sidebar_summary(journal_df, filtered_df, container):
    """Shows compact journal patterns in the sidebar."""
    with container:
        st.subheader("Stats")
        st.metric("Total readings", len(journal_df))

        if not filtered_df.empty:
            most_common = filtered_df["Primary Hexagram"].mode()
            if not most_common.empty:
                st.caption(f"Most common: {most_common.iloc[0]}")

            latest_date = filtered_df["Date Parsed"].dropna().max()
            if pd.notna(latest_date):
                st.caption(f"Most recent: {latest_date.strftime('%Y-%m-%d')}")

            top_hexagrams = (
                filtered_df["Primary Hexagram"]
                .value_counts()
                .head(5)
                .rename_axis("Hexagram")
                .reset_index(name="Readings")
            )
            st.bar_chart(top_hexagrams, x="Hexagram", y="Readings", height=180)


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


def render_main_ui(iching_data, binary_to_hex_map, openai_enabled, client):
    """Renders the main user interface for casting and viewing readings."""
    if "question_text" not in st.session_state:
        st.session_state.question_text = ""
    if "reading_saved" not in st.session_state:
        st.session_state.reading_saved = False

    st.title("☯️ 易經 - The Book of Changes")
    
    with st.expander("A Guide to Divination"):
        st.markdown("""
    The I Ching, or Book of Changes, is an ancient text for divination and wisdom. To consult it, you approach it with a sincere question. The oracle responds with a **hexagram**—a figure of six lines—that mirrors the cosmic energies at play in your situation.\
\
- **Solid lines (Yang)** represent the creative, active principle.\
- **Broken lines (Yin)** represent the receptive, yielding principle.\
\
At times, a line may be 'changing,' indicating a dynamic aspect of the present moment. This transformation reveals a second hexagram, offering insight into how the situation may evolve. This app is a vessel for this ancient dialogue, helping you cast a reading and contemplate its meaning.\
""")

    st.header("Consult the Oracle")

    col1, col2 = st.columns([1,1])
    with col1:
        cast_button_clicked = st.button("Cast Reading", type="primary", use_container_width=True)
    with col2:
        if st.button("Suggest a Question", use_container_width=True):
            st.session_state.question_text = random.choice(SAMPLE_QUESTIONS)
            st.rerun()

    question = st.text_area(
        "Center your mind and enter your inquiry below:",
        height=100, 
        key="question_text"
    )

    if cast_button_clicked and question:
        with st.spinner("Casting the lines..."):
            import time
            time.sleep(1.5)
            st.session_state.reading_cast = True
            st.session_state.ai_interpretation = None
            st.session_state.reading_saved = False
            lines = cast_reading()
            primary_hex_num, secondary_hex_num = get_hexagram_numbers(lines, binary_to_hex_map)
            
            st.session_state.reading = {
                "question": question,
                "lines": lines,
                "primary_hex": iching_data[str(primary_hex_num)],
                "secondary_hex": iching_data[str(secondary_hex_num)] if secondary_hex_num else None,
                "changing_lines_indices": [i for i, line in enumerate(lines) if line in [6, 9]],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.rerun()

    if st.session_state.get('reading_cast'):
        display_reading(st.session_state.reading)
        
        st.divider()
        st.header("Contemplation & Journal")
        
        col1, col2 = st.columns(2)
        with col1:
            if openai_enabled:
                if st.button("🤖 Generate AI Contemplation", use_container_width=True):
                    with st.spinner("The AI is consulting the oracle..."):
                        try:
                            interpretation = get_ai_interpretation(st.session_state.reading, client)
                            if interpretation:
                                st.session_state.ai_interpretation = interpretation
                                st.session_state.reading['ai_interpretation'] = interpretation
                                st.rerun()
                        except Exception as e:
                            logging.error(f"OpenAI API error: {e}")
                            st.error(f"An error occurred with the AI integration: {e}")

        with col2:
            if st.button("💾 Save to Journal", use_container_width=True, disabled=st.session_state.reading_saved):
                save_reading_to_csv(st.session_state.reading)
                st.session_state.reading_saved = True
                st.success(f"Reading saved to {JOURNAL_FILE}")
                st.rerun()

        if st.session_state.get('ai_interpretation'):
            with st.expander("A Guided Reflection", expanded=True):
                st.markdown(st.session_state.ai_interpretation)


from iching_logic import cast_reading, get_hexagram_numbers
from file_handler import (
    enrich_journal,
    journal_to_markdown,
    load_iching_data,
    load_journal,
    save_reading_to_csv,
    reconstruct_reading_from_row,
    JOURNAL_FILE,
)
from ui_components import display_reading
from ai_integration import get_ai_interpretation
from constants import SAMPLE_QUESTIONS

# --- Page Configuration ---
st.set_page_config(
    page_title="易經 - The Book of Changes",
    page_icon="☯️",
    layout="centered"
)

# --- Main Application ---

if __name__ == "__main__":
    main()
