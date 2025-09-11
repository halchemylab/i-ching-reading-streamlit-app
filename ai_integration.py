import streamlit as st
import openai

def get_ai_interpretation(reading, client):
    """Constructs a prompt and gets an interpretation from OpenAI."""
    primary_hex = reading['primary_hex']
    secondary_hex = reading['secondary_hex']
    
    changing_lines_text = ""
    if reading['changing_lines_indices']:
        changing_lines_text += "The following lines are in a state of transformation:\n"
        for i in reading['changing_lines_indices']:
            line_data = primary_hex['lines'][i]
            changing_lines_text += f"- **Line {i+1}:** {line_data['line_en']}\n"
    else:
        changing_lines_text = "There are no changing lines.\n"

    evolving_hex_text = ""
    if secondary_hex:
        evolving_hex_text = f"""
This is evolving into a new energetic pattern:
- **Evolving Hexagram:** {secondary_hex['number']}. {secondary_hex['name_en']} ({secondary_hex['name_zh']}) - This points to the potential direction of change and the lesson to be integrated.
- **Judgment:** {secondary_hex['judgment_en']}
"""

    prompt = f"""
You are a wise and compassionate guide to the I Ching, the Book of Changes. Your purpose is not to predict the future, but to offer timeless wisdom that illuminates the present moment and empowers the user to make conscious choices.

A user has approached you with the following inquiry: "{reading['question']}"

They have received a reading that reflects the energies surrounding their question:
- **Primary Hexagram:** {primary_hex['number']}. {primary_hex['name_en']} ({primary_hex['name_zh']}) - This represents the current state of things.
- **Judgment:** {primary_hex['judgment_en']}

{changing_lines_text}
{evolving_hex_text}

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
