import random
import os
import time
import logging
from datetime import datetime

import openai
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from ai_integration import AIRateLimitError, AIInterpretationError, get_ai_interpretation
from constants import SAMPLE_QUESTIONS
from file_handler import (
    JOURNAL_FILE,
    IChingDataError,
    enrich_journal,
    load_iching_data,
    load_journal,
    reconstruct_reading_from_row,
    save_reading_to_csv,
)
from iching_logic import cast_reading, get_hexagram_numbers
from journal_ui import render_empty_journal_sidebar, render_journal_sidebar
from ui_components import display_reading


logging.basicConfig(
    level=logging.INFO,
    filename="app.log",
    filemode="a",
    format="%(name)s - %(levelname)s - %(message)s",
)

st.set_page_config(
    page_title="易經 - The Book of Changes",
    page_icon="☯️",
    layout="centered",
)


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
    
    try:
        iching_data, binary_to_hex_map = load_iching_data()
    except IChingDataError as e:
        st.error(f"Error: {e}")
        return

    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    client = None
    openai_enabled = True if api_key else False
    if openai_enabled:
        client = openai.OpenAI(api_key=api_key)

    if iching_data and binary_to_hex_map:
        render_main_ui(iching_data, binary_to_hex_map, openai_enabled, client)
        render_journal(iching_data)


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
    filtered_df = render_journal_sidebar(journal_df, iching_data)

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
                        except AIRateLimitError as e:
                            logging.error(f"OpenAI API rate limit error: {e}")
                            st.error(str(e))
                        except AIInterpretationError as e:
                            logging.error(f"OpenAI API error: {e}")
                            st.error(str(e))

        with col2:
            if st.button("💾 Save to Journal", use_container_width=True, disabled=st.session_state.reading_saved):
                save_reading_to_csv(st.session_state.reading)
                st.session_state.reading_saved = True
                st.success(f"Reading saved to {JOURNAL_FILE}")
                st.rerun()

        if st.session_state.get('ai_interpretation'):
            with st.expander("A Guided Reflection", expanded=True):
                st.markdown(st.session_state.ai_interpretation)

if __name__ == "__main__":
    main()
