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

Please offer a contemplative interpretation organized into the following four sections, using the bolded titles exactly as written:

**The Present Situation:**
Start here. Interpret the primary hexagram and its judgment in the context of the user's question. Describe the current energies at play.

**The Dynamics of Change:**
Next, explain the significance of the changing lines. If there are no changing lines, briefly state that the situation is stable and focus on the primary hexagram's wisdom.

**The Emerging Direction:**
Then, interpret the secondary (evolving) hexagram. Describe the potential future, the direction of change, or the lesson to be integrated. If there is no secondary hexagram, you can omit this section.

**Guidance for Reflection:**
Conclude with a paragraph of practical, supportive advice. Offer questions for reflection or suggest a focus for the user's energy that weaves together all the elements of the reading.

Your tone should be serene, insightful, and supportive throughout.
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
