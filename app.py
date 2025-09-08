import streamlit as st
import json
import random
import openai
import os
from dotenv import load_dotenv

# --- Page Configuration ---
st.set_page_config(
    page_title="易經 - The Book of Changes",
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
    load_dotenv()
    
    # Initialize OpenAI Client
    api_key = os.getenv("OPENAI_API_KEY")
    client = None
    openai_enabled = False
    if api_key:
        client = openai.OpenAI(api_key=api_key)
        openai_enabled = True

    if iching_data:
        # --- Introduction ---
        st.title("易經 - The Book of Changes ☯️")
        
        with st.expander("A Guide to Divination"):
            st.markdown("""
            The I Ching, or Book of Changes, is an ancient text for divination and wisdom. To consult it, you approach it with a sincere question. The oracle responds with a **hexagram**—a figure of six lines—that mirrors the cosmic energies at play in your situation.

            - **Solid lines (Yang)** represent the creative, active principle.
            - **Broken lines (Yin)** represent the receptive, yielding principle.

            At times, a line may be 'changing,' indicating a dynamic aspect of the present moment. This transformation reveals a second hexagram, offering insight into how the situation may evolve. This app is a vessel for this ancient dialogue, helping you cast a reading and contemplate its meaning.
            """)

        # --- User Input ---
        st.header("Consult the Oracle")
        
        sample_questions = [
            "What is the wisest way to approach my current challenge?",
            "What underlying dynamics are at play in my relationship with [Person's Name]?",
            "How can I cultivate more harmony and balance within myself?",
            "What is the most important lesson for me to embrace at this moment?",
            "What should I focus on for my spiritual growth right now?",
            "What do I need to understand about the flow of abundance in my life?",
            "How can I unlock my creative potential in my work?",
            "What is the nature of the obstacle I am contemplating?",
            "How can I best support my loved ones with compassion?",
            "What new perspective is waiting to be revealed?",
            "What is the path toward healing and integration in this situation?",
            "How can I cultivate a deeper sense of inner peace?",
            "What is the most graceful way to navigate the upcoming changes?",
            "Which aspect of my inner self requires my attention?",
            "What is the deeper significance of my current circumstances?"
        ]

        # Initialize session state for the question text
        if "question_text" not in st.session_state:
            st.session_state.question_text = ""

        # Handle button clicks BEFORE rendering the text_area
        col1, col2 = st.columns([1,1])
        with col1:
            cast_button_clicked = st.button("Cast Reading", type="primary", use_container_width=True)
        with col2:
            if st.button("Suggest a Question", use_container_width=True):
                st.session_state.question_text = random.choice(sample_questions)
                st.rerun() # Rerun to update the text area immediately

        question = st.text_area(
            "Center your mind and enter your inquiry below:",
            height=100, 
            key="question_text"
        )

        if cast_button_clicked:
            if question:
                with st.spinner("Casting the lines..."):
                    import time
                    time.sleep(1.5)
                    st.session_state.reading_cast = True
                    st.session_state.ai_interpretation = None
                    lines = cast_reading()
                    primary_hex_num, secondary_hex_num = get_hexagram_numbers(lines, iching_data)
                    
                    st.session_state.reading = {
                        "question": question,
                        "lines": lines,
                        "primary_hex": iching_data[str(primary_hex_num)],
                        "secondary_hex": iching_data[str(secondary_hex_num)] if secondary_hex_num else None,
                        "changing_lines_indices": [i for i, line in enumerate(lines) if line in [6, 9]]
                    }
                    st.rerun()
            else:
                st.warning("Please enter a question before casting a reading.")

        if 'reading' in st.session_state and st.session_state.reading_cast:
            display_reading(st.session_state.reading)
            
            st.divider()
            st.header("Contemplative Insight")
            if openai_enabled:
                if st.button("🤖 Generate AI-Powered Contemplation", help="Receive a modern contemplation on your reading."):
                    with st.spinner("The AI is consulting the oracle..."):
                        interpretation = get_ai_interpretation(st.session_state.reading, client)
                        st.session_state.ai_interpretation = interpretation
            else:
                st.warning("OpenAI API key not found. AI interpretations are disabled.", icon="⚠️")

        if 'ai_interpretation' in st.session_state and st.session_state.ai_interpretation:
            with st.expander("A Modern Contemplation", expanded=True):
                st.markdown(st.session_state.ai_interpretation)


# --- I Ching Logic and Display ---

def cast_reading():
    """Simulates casting 3 coins 6 times to get 6 lines."""
    return [random.choice([6, 7, 8, 9]) for _ in range(6)]

def get_hexagram_numbers(lines, iching_data):
    """Determines the primary and secondary hexagram numbers from the lines."""
    primary_binary = "".join(['1' if l in [7, 9] else '0' for l in reversed(lines)])
    
    primary_num = None
    for key, hex_data in iching_data.items():
        if hex_data.get('binary_code') == primary_binary:
            primary_num = hex_data['number']
            break

    secondary_num = None
    if any(line in [6, 9] for line in lines):
        secondary_lines = [l if l in [7, 8] else (7 if l == 6 else 8) for l in lines]
        secondary_binary = "".join(['1' if l in [7, 9] else '0' for l in reversed(secondary_lines)])
        for key, hex_data in iching_data.items():
            if hex_data.get('binary_code') == secondary_binary:
                secondary_num = hex_data['number']
                break
    
    # Default to 1 and 2 if not found, for placeholder data
    if primary_num is None: primary_num = 1
    if secondary_num is None and any(line in [6, 9] for line in lines): secondary_num = 2

    return primary_num, secondary_num

def display_reading(reading):
    """Displays the entire classical reading results in a modern, minimalist layout."""
    st.divider()
    st.header("Your Reading")

    primary_hex = reading['primary_hex']
    secondary_hex = reading['secondary_hex']
    lines = reading['lines']
    changing_lines_indices = reading['changing_lines_indices']

    # --- Layout ---
    col1, col2 = st.columns(2)

    # --- Primary Hexagram ---
    with col1:
        st.subheader(f"Primary Hexagram")
        st.markdown(get_hexagram_svg(lines, changing_lines_indices), unsafe_allow_html=True)
        st.subheader(f"{primary_hex['number']}: {primary_hex['name_en']}")
        st.caption(f"{primary_hex['name_zh']} ({primary_hex.get('name_pinyin', '')})")

        st.info("This hexagram reflects the present energetic landscape of your inquiry.", icon="🧭")

        with st.expander("Judgment"):
            display_bilingual_text(None, primary_hex['judgment_zh'], primary_hex['judgment_en'])
        with st.expander("Image"):
            display_bilingual_text(None, primary_hex['image_zh'], primary_hex['image_en'])

        if changing_lines_indices:
            with st.expander("Changing Lines"):
                for i in changing_lines_indices:
                    line_num = i + 1
                    line_data = primary_hex['lines'][i]
                    st.markdown(f"**Line {line_num}:**")
                    display_bilingual_text(None, line_data['line_zh'], line_data['line_en'])
                    if i != changing_lines_indices[-1]:
                        st.divider()

    # --- Secondary Hexagram ---
    if secondary_hex:
        with col2:
            st.subheader(f"Evolving Hexagram")
            secondary_lines_values = [l if l in [7, 8] else (7 if l == 6 else 8) for l in lines]
            st.markdown(get_hexagram_svg(secondary_lines_values, []), unsafe_allow_html=True)
            st.subheader(f"{secondary_hex['number']}: {secondary_hex['name_en']}")
            st.caption(f"{secondary_hex['name_zh']} ({secondary_hex.get('name_pinyin', '')})")
            
            st.info("This hexagram reveals the direction of change and the potential evolution of your situation.", icon="🦋")

            with st.expander("Judgment"):
                display_bilingual_text(None, secondary_hex['judgment_zh'], secondary_hex['judgment_en'])
            with st.expander("Image"):
                display_bilingual_text(None, secondary_hex['image_zh'], secondary_hex['image_en'])

def get_hexagram_svg(lines, changing_indices, line_height=15, line_width=100, gap=10):
    """Generates an SVG for a hexagram with animations."""
    svg_height = (line_height + gap) * 6 - gap
    svg_lines = []

    for i, line_val in enumerate(reversed(lines)):
        is_changing = (len(lines) - 1 - i) in changing_indices
        y = i * (line_height + gap)
        
        # Colors
        line_color = "#6c757d" # Default color
        if is_changing:
            line_color = "#ffc107" # A soft gold for changing lines

        # Animation
        animation = f'<animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{i*0.1}s" fill="freeze" />'

        if line_val in [6, 8]:  # Yin line (broken)
            svg_lines.append(
                f'<g transform="translate(0, {y})">'
                f'<rect x="0" y="0" width="{line_width * 0.45}" height="{line_height}" fill="{line_color}" rx="2">{animation}</rect>'
                f'<rect x="{line_width * 0.55}" y="0" width="{line_width * 0.45}" height="{line_height}" fill="{line_color}" rx="2">{animation}</rect>'
                f'</g>'
            )
        else:  # Yang line (solid)
            svg_lines.append(
                f'<g transform="translate(0, {y})">'
                f'<rect x="0" y="0" width="{line_width}" height="{line_height}" fill="{line_color}" rx="2">{animation}</rect>'
                f'</g>'
            )

    return f'''
        <div style="display: flex; justify-content: center; align-items: center;">
            <svg width="{line_width}" height="{svg_height}" viewbox="0 0 {line_width} {svg_height}">
                {''.join(svg_lines)}
            </svg>
        </div>
    ''' 

def display_bilingual_text(header, text_zh, text_en):
    """Displays Chinese and English text for a given section with improved styling."""
    if header:
        st.markdown(f"**{header}:**")
    
    st.markdown(f"<p style='font-size: 1.2em; font-family: serif;'>{text_zh}</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-style: italic; color: #888; border-left: 3px solid #ccc; padding-left: 10px;'>{text_en}</p>", unsafe_allow_html=True)

# --- AI Interpretation ---
def get_ai_interpretation(reading, client):
    """Constructs a prompt and gets an interpretation from OpenAI."""
    primary_hex = reading['primary_hex']
    secondary_hex = reading['secondary_hex']
    
    prompt = f"""
You are a wise and compassionate guide to the I Ching, the Book of Changes. Your purpose is not to predict the future, but to offer timeless wisdom that illuminates the present moment and empowers the user to make conscious choices.

A user has approached you with the following inquiry: "{reading['question']}"

They have received a reading that reflects the energies surrounding their question:
- **Primary Hexagram:** {primary_hex['number']}. {primary_hex['name_en']} ({primary_hex['name_zh']}) - This represents the current state of things.
- **Judgment:** {primary_hex['judgment_en']}

The following lines are in a state of transformation:
    """
    if reading['changing_lines_indices']:
        for i in reading['changing_lines_indices']:
            line_data = primary_hex['lines'][i]
            prompt += f"- **Line {i+1}:** {line_data['line_en']}\n"
    else:
        prompt += "- None\n"

    if secondary_hex:
        prompt += f"""
This is evolving into a new energetic pattern:
- **Evolving Hexagram:** {secondary_hex['number']}. {secondary_hex['name_en']} ({secondary_hex['name_zh']}) - This points to the potential direction of change and the lesson to be integrated.
"""

    prompt += f"""
Please offer a contemplative interpretation. Weave together the meanings of the primary hexagram, the changing lines, and the evolving hexagram into a unified message. Focus on the underlying themes, the psychological and spiritual lessons, and the practical wisdom the user can apply. Avoid definitive predictions. Instead, empower the user to reflect on their own inner wisdom. Use a tone that is serene, insightful, and supportive. Structure the guidance in clear, accessible paragraphs.
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