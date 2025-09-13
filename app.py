import streamlit as st
import random
import openai
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

from iching_logic import cast_reading, get_hexagram_numbers
from file_handler import load_iching_data, save_reading_to_csv, reconstruct_reading_from_row, JOURNAL_FILE
from ui_components import display_reading
from ai_integration import get_ai_interpretation

# --- Page Configuration ---
st.set_page_config(
    page_title="易經 - The Book of Changes",
    page_icon="☯️",
    layout="centered"
)

# --- Main Application ---
def main():
    """Main function to run the Streamlit app."""
    iching_data, binary_to_hex_map = load_iching_data()
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    client = None
    openai_enabled = True if api_key else False
    if openai_enabled:
        client = openai.OpenAI(api_key=api_key)

    if iching_data and binary_to_hex_map:
        if "question_text" not in st.session_state:
            st.session_state.question_text = ""
        if "reading_saved" not in st.session_state:
            st.session_state.reading_saved = False

        st.title("☯️ 易經 - The Book of Changes")
        
        with st.expander("A Guide to Divination"):
            st.markdown("""
The I Ching, or Book of Changes, is an ancient text for divination and wisdom. To consult it, you approach it with a sincere question. The oracle responds with a **hexagram**—a figure of six lines—that mirrors the cosmic energies at play in your situation.\n\n- **Solid lines (Yang)** represent the creative, active principle.\n- **Broken lines (Yin)** represent the receptive, yielding principle.\n\nAt times, a line may be 'changing,' indicating a dynamic aspect of the present moment. This transformation reveals a second hexagram, offering insight into how the situation may evolve. This app is a vessel for this ancient dialogue, helping you cast a reading and contemplate its meaning.\n""")

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
                            interpretation = get_ai_interpretation(st.session_state.reading, client)
                            st.session_state.ai_interpretation = interpretation
                            st.session_state.reading['ai_interpretation'] = interpretation
                            st.rerun()

            with col2:
                if st.button("💾 Save to Journal", use_container_width=True, disabled=st.session_state.reading_saved):
                    save_reading_to_csv(st.session_state.reading)
                    st.session_state.reading_saved = True
                    st.success(f"Reading saved to {JOURNAL_FILE}")
                    st.rerun()

            if st.session_state.get('ai_interpretation'):
                with st.expander("A Modern Contemplation", expanded=True):
                    st.markdown(st.session_state.ai_interpretation)

        st.divider()
        st.header("Reading Journal")
        if os.path.exists(JOURNAL_FILE):
            try:
                journal_df = pd.read_csv(JOURNAL_FILE)
                if not journal_df.empty:
                    for index, row in journal_df.iloc[::-1].iterrows():
                        reconstructed_reading = reconstruct_reading_from_row(row, iching_data)
                        with st.expander(f"**{row['Date']}** - {row['Question']}"):
                            display_reading(reconstructed_reading, is_journal=True)
                            if pd.notna(row['AI Interpretation']):
                                st.markdown("**AI Contemplation:**")
                                st.markdown(row['AI Interpretation'])
                else:
                    st.info("Your journal is empty. Saved readings will appear here.")
            except pd.errors.EmptyDataError:
                st.info("Your journal is empty. Saved readings will appear here.")
        else:
            st.info("Your journal is empty. Saved readings will appear here.")

if __name__ == "__main__":
    main()
