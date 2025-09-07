import streamlit as st
import json
import random
import openai

# --- Page Configuration ---
st.set_page_config(
    page_title="I Ching - The Book of Changes",
    page_icon="☯️",
    layout="centered"
)

# --- Data Loading ---
@st.cache_data
def load_iching_data():
    """Loads the I Ching data from the JSON file."""
    try:
        with open('i_ching_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Error: i_ching_data.json not found. Please make sure the data file is in the same directory as the app.")
        return None
    except json.JSONDecodeError:
        st.error("Error: Could not decode i_ching_data.json. Please check the file for formatting errors.")
        return None

# --- Main Application ---
def main():
    """Main function to run the Streamlit app."""
    iching_data = load_iching_data()
    
    # Initialize OpenAI Client
    try:
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        openai_enabled = True
    except (FileNotFoundError, KeyError):
        openai_enabled = False


    if iching_data:
        # --- Introduction ---
        st.title("I Ching - The Book of Changes ☯️")
        st.markdown("""
        Welcome to the digital I Ching, the ancient Chinese oracle known as the Book of Changes. 
        This tool is designed to help you find clarity and wisdom through its timeless teachings.
        """)

        with st.expander("How Readings Work"):
            st.markdown("""
            1.  **Quiet Your Mind:** Take a moment to focus on a specific question or situation you're facing. The clearer your question, the more insightful the answer will be.
            2.  **Cast Your Reading:** When you are ready, enter your question and click the "Cast Reading" button.
            3.  **The Reading:** The app will simulate the traditional method of casting coins to generate six lines, which form a **hexagram**. 
            4.  **Changing Lines:** Some lines may be "changing," which means they are in a state of transformation. These lines are especially significant and create a second hexagram, showing the direction your situation is heading.
            5.  **Interpretation:** You will receive the texts for your primary hexagram, any changing lines, and your transformed hexagram. You can then request a modern interpretation from an AI assistant.
            """)

        # --- User Input ---
        st.header("Consult the Oracle")
        question = st.text_area("Enter your question or situation below:", height=100, placeholder="e.g., What should I focus on in my career right now?", key="question_text")

        if st.button("Cast Reading", type="primary"):
            if question:
                st.session_state.reading_cast = True
                st.session_state.ai_interpretation = None # Reset AI interpretation
                lines = cast_reading()
                primary_hex_num, secondary_hex_num = get_hexagram_numbers(lines)
                
                st.session_state.reading = {
                    "question": question,
                    "lines": lines,
                    "primary_hex": iching_data[str(primary_hex_num)],
                    "secondary_hex": iching_data[str(secondary_hex_num)] if secondary_hex_num else None,
                    "changing_lines_indices": [i for i, line in enumerate(lines) if line in [6, 9]]
                }
            else:
                st.warning("Please enter a question before casting a reading.")

        if 'reading' in st.session_state and st.session_state.reading_cast:
            display_reading(st.session_state.reading)
            
            if openai_enabled:
                if st.button("🤖 Generate AI Interpretation"):
                    with st.spinner("The AI is consulting the oracle..."):
                        interpretation = get_ai_interpretation(st.session_state.reading, client)
                        st.session_state.ai_interpretation = interpretation
            else:
                st.warning("OpenAI API key not found. Please add it to your `.streamlit/secrets.toml` file to enable AI interpretations.", icon="⚠️")

        if 'ai_interpretation' in st.session_state and st.session_state.ai_interpretation:
            st.divider()
            st.header("Modern Interpretation")
            st.markdown(st.session_state.ai_interpretation)


# --- I Ching Logic and Display ---

def cast_reading():
    """Simulates casting 3 coins 6 times to get 6 lines."""
    return [random.choice([6, 7, 8, 9]) for _ in range(6)]

def get_hexagram_numbers(lines):
    """Determines the primary and secondary hexagram numbers from the lines."""
    hexagram_map = { "111111": 1, "000000": 2 } # Placeholder map

    primary_binary = "".join(['1' if l in [7, 9] else '0' for l in reversed(lines)])
    
    changing_lines = any(line in [6, 9] for line in lines)
    secondary_binary = None
    if changing_lines:
        secondary_lines = [l if l in [7, 8] else (7 if l == 6 else 8) for l in lines]
        secondary_binary = "".join(['1' if l in [7, 9] else '0' for l in reversed(secondary_lines)])

    primary_num = hexagram_map.get(primary_binary, 1)
    secondary_num = hexagram_map.get(secondary_binary, 2) if secondary_binary else None
    
    return primary_num, secondary_num

def display_reading(reading):
    """Displays the entire classical reading results."""
    st.divider()
    st.success(f'Reading for: *"{reading["question"]}"*')
    st.header("Your Reading")

    primary_hex = reading['primary_hex']
    secondary_hex = reading['secondary_hex']
    lines = reading['lines']
    changing_lines_indices = reading['changing_lines_indices']

    col1, col2 = st.columns([1, 3])
    with col1:
        draw_hexagram(lines, changing_lines_indices)
    with col2:
        st.subheader(f"Hexagram {primary_hex['number']}: {primary_hex['name_zh']} ({primary_hex['name_en']})")

    display_bilingual_text("Judgment", primary_hex['judgment_zh'], primary_hex['judgment_en'])
    display_bilingual_text("Image", primary_hex['image_zh'], primary_hex['image_en'])

    if changing_lines_indices:
        st.subheader("Changing Lines")
        for i in changing_lines_indices:
            line_num = i + 1
            line_data = primary_hex['lines'][i]
            st.markdown(f"**Line {line_num}:**")
            display_bilingual_text(None, line_data['line_zh'], line_data['line_en'])

    if secondary_hex:
        st.divider()
        st.header("Transformed Hexagram")
        col3, col4 = st.columns([1, 3])
        with col3:
            secondary_lines_values = [l if l in [7, 8] else (7 if l == 6 else 8) for l in lines]
            draw_hexagram(secondary_lines_values, [])
        with col4:
            st.subheader(f"Hexagram {secondary_hex['number']}: {secondary_hex['name_zh']} ({secondary_hex['name_en']})")
            st.markdown("This hexagram shows the direction your situation is moving toward.")

def draw_hexagram(lines, changing_indices):
    """Draws a single hexagram using text characters."""
    hex_html = "<div style='font-family: monospace; line-height: 1.2; font-size: 1.6em; text-align: center;'>"
    for i, line_val in enumerate(reversed(lines)):
        line_char = "---&nbsp;&nbsp;&nbsp;--- " if line_val in [6, 8] else "---------"
        is_changing = (len(lines) - 1 - i) in changing_indices
        if is_changing:
            line_char += " o" if line_val == 9 else " x"
        hex_html += f"<div>{line_char}</div>"
    hex_html += "</div>"
    st.markdown(hex_html, unsafe_allow_html=True)

def display_bilingual_text(header, text_zh, text_en):
    """Displays Chinese and English text for a given section."""
    if header:
        st.markdown(f"**{header}:**")
    st.markdown(f"<p style='font-size: 1.1em;'>{text_zh}</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-style: italic; color: #888;'>{text_en}</p>", unsafe_allow_html=True)

# --- AI Interpretation ---
def get_ai_interpretation(reading, client):
    """Constructs a prompt and gets an interpretation from OpenAI."""
    primary_hex = reading['primary_hex']
    secondary_hex = reading['secondary_hex']
    
    prompt = f"""
You are a wise, modern, and compassionate interpreter of the I Ching, the Book of Changes.
A user has asked the following question: "{reading['question']}"

They received the following reading:
- **Primary Hexagram:** {primary_hex['number']}. {primary_hex['name_en']} ({primary_hex['name_zh']})
- **Judgment:** {primary_hex['judgment_en']}

The following lines were changing:
    """
    if reading['changing_lines_indices']:
        for i in reading['changing_lines_indices']:
            line_data = primary_hex['lines'][i]
            prompt += f"- **Line {i+1}:** {line_data['line_en']}\n"
    else:
        prompt += "- None\n"

    if secondary_hex:
        prompt += f"""
This transforms into the following hexagram:
- **Transformed Hexagram:** {secondary_hex['number']}. {secondary_hex['name_en']} ({secondary_hex['name_zh']})
"""

    prompt += f"""
Please provide a thoughtful, modern interpretation. Synthesize the meaning of the primary hexagram, the changing lines, and the transformed hexagram (if any) into a cohesive narrative. Address the user's question directly, offering practical wisdom and insight. Speak in a clear, encouraging, and accessible tone. Structure your answer with paragraphs for readability.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a wise and compassionate I Ching interpreter."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"An error occurred while contacting the AI: {e}")
        return "Sorry, the AI interpretation could not be generated at this time."

if __name__ == "__main__":
    main()