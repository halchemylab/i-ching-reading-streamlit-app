import html

import streamlit as st

from constants import HEXAGRAM_THEME_SUMMARIES


def display_reading(reading, is_journal=False):
    """Displays a reading as either a guided live experience or compact journal entry."""
    if is_journal:
        display_compact_reading(reading)
        return

    display_guided_reading(reading)


def display_guided_reading(reading):
    """Displays a live reading as a sequenced interpretive journey."""
    inject_reading_styles()

    st.divider()
    st.header("Your Guided Reading")
    display_inquiry_anchor(reading)
    display_key_takeaway(reading)
    display_reading_path(reading)
    display_primary_hexagram_step(reading)
    display_changing_lines_step(reading)
    display_evolving_hexagram_step(reading)
    display_reflection_step(reading)


def display_compact_reading(reading):
    """Displays the classical reading results in a compact two-column layout."""
    inject_reading_styles()

    primary_hex = reading['primary_hex']
    secondary_hex = reading['secondary_hex']
    lines = reading['lines']
    changing_lines_indices = reading['changing_lines_indices']

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Primary Hexagram")
        st.markdown(get_hexagram_svg(lines, changing_lines_indices), unsafe_allow_html=True)
        st.subheader(f"{primary_hex['number']}: {primary_hex['name_en']}")
        st.caption(f"{primary_hex['name_zh']} ({primary_hex.get('name_pinyin', '')})")
        with st.expander("Judgment"):
            display_bilingual_text(None, primary_hex.get('judgment_zh'), primary_hex['judgment_en'])
        with st.expander("Image"):
            display_bilingual_text(None, primary_hex.get('image_zh'), primary_hex['image_en'])
        if changing_lines_indices:
            with st.expander("Changing Lines"):
                for i in changing_lines_indices:
                    line_num = i + 1
                    line_data = primary_hex['lines'][i]
                    st.markdown(f"**Line {line_num}:**")
                    display_bilingual_text(None, line_data.get('line_zh'), line_data['line_en'])
                    if i != changing_lines_indices[-1]:
                        st.divider()

    if secondary_hex:
        with col2:
            st.subheader("Evolving Hexagram")
            secondary_lines_values = [l if l in [7, 8] else (7 if l == 6 else 8) for l in lines]
            st.markdown(get_hexagram_svg(secondary_lines_values, []), unsafe_allow_html=True)
            st.subheader(f"{secondary_hex['number']}: {secondary_hex['name_en']}")
            st.caption(f"{secondary_hex['name_zh']} ({secondary_hex.get('name_pinyin', '')})")
            with st.expander("Judgment"):
                display_bilingual_text(None, secondary_hex.get('judgment_zh'), secondary_hex['judgment_en'])
            with st.expander("Image"):
                display_bilingual_text(None, secondary_hex.get('image_zh'), secondary_hex['image_en'])


def inject_reading_styles():
    """Adds reading-specific visual treatments."""
    st.markdown(
        """
        <style>
            .reading-card {
                border: 1px solid rgba(128, 128, 128, 0.28);
                border-radius: 8px;
                margin: 1rem 0;
                padding: 1.1rem 1.2rem;
            }

            .reading-card h3,
            .reading-card h4,
            .reading-card p {
                margin: 0;
            }

            .reading-card .eyebrow {
                color: #ffc107;
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0;
                margin-bottom: 0.45rem;
                text-transform: uppercase;
            }

            .muted,
            .reading-card .muted {
                color: #9aa3ad;
                line-height: 1.5;
                margin-top: 0.5rem;
            }

            .reading-card .question {
                font-size: 1.25rem;
                font-weight: 650;
                line-height: 1.35;
            }

            .reading-path {
                align-items: stretch;
                display: grid;
                gap: 0.75rem;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                margin: 1rem 0 1.5rem;
            }

            .reading-path-item {
                border: 1px solid rgba(128, 128, 128, 0.26);
                border-radius: 8px;
                padding: 0.85rem;
            }

            .reading-path-item strong {
                display: block;
                font-size: 0.95rem;
                line-height: 1.25;
            }

            .reading-path-item span {
                color: #9aa3ad;
                display: block;
                font-size: 0.82rem;
                line-height: 1.35;
                margin-top: 0.25rem;
            }

            .line-card {
                border-left: 4px solid #ffc107;
                margin: 0.9rem 0;
                padding: 0.2rem 0 0.2rem 1rem;
            }

            .reflection-card {
                background: rgba(255, 193, 7, 0.1);
                border-color: rgba(255, 193, 7, 0.4);
            }

            .takeaway-card {
                background: linear-gradient(135deg, rgba(255, 193, 7, 0.14), rgba(108, 117, 125, 0.08));
                border-color: rgba(255, 193, 7, 0.5);
            }

            @media (max-width: 760px) {
                .reading-path {
                    grid-template-columns: 1fr;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def display_key_takeaway(reading):
    """Displays a concise summary before the full reading detail."""
    st.markdown(
        f"""
        <div class="reading-card takeaway-card">
            <p class="eyebrow">Key Takeaway</p>
            <p>{html.escape(get_key_takeaway(reading))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_key_takeaway(reading):
    """Returns a concise, plain-language summary of the reading."""
    primary_hex = reading["primary_hex"]
    secondary_hex = reading["secondary_hex"]
    changing_lines_indices = reading["changing_lines_indices"]
    primary_name = primary_hex["name_en"]

    if changing_lines_indices:
        line_label = format_changing_lines(changing_lines_indices)
        if secondary_hex:
            return (
                f"This reading begins with {primary_name} and moves toward "
                f"{secondary_hex['name_en']}. The active pressure is in {line_label}, "
                "so focus on the part of the situation that is already shifting."
            )

        return (
            f"This reading centers on {primary_name}. The active pressure is in "
            f"{line_label}, so look for the specific place where a response is needed."
        )

    return (
        f"This reading centers on {primary_name}. With no changing lines, the counsel "
        "is to stay with the present pattern and let its guidance settle before forcing movement."
    )


def format_changing_lines(changing_lines_indices):
    """Formats zero-based changing line indices for reader-facing copy."""
    line_numbers = [str(index + 1) for index in changing_lines_indices]
    if len(line_numbers) == 1:
        return f"line {line_numbers[0]}"
    if len(line_numbers) == 2:
        return f"lines {line_numbers[0]} and {line_numbers[1]}"
    return f"lines {', '.join(line_numbers[:-1])}, and {line_numbers[-1]}"


def display_inquiry_anchor(reading):
    question = html.escape(reading.get("question", "").strip())
    if not question:
        return

    st.markdown(
        f"""
        <div class="reading-card">
            <p class="eyebrow">Inquiry</p>
            <p class="question">{question}</p>
            <p class="muted">Hold this question as the center of the reading.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def display_reading_path(reading):
    primary_hex = reading["primary_hex"]
    secondary_hex = reading["secondary_hex"]
    changing_count = len(reading["changing_lines_indices"])
    moving_label = f"{changing_count} changing line{'s' if changing_count != 1 else ''}"
    evolving_label = (
        f"{secondary_hex['number']}: {secondary_hex['name_en']}"
        if secondary_hex else
        "No evolving hexagram"
    )

    st.markdown(
        f"""
        <div class="reading-path">
            <div class="reading-path-item">
                <strong>1. Present situation</strong>
                <span>{primary_hex['number']}: {html.escape(primary_hex['name_en'])}</span>
            </div>
            <div class="reading-path-item">
                <strong>2. What is moving</strong>
                <span>{moving_label}</span>
            </div>
            <div class="reading-path-item">
                <strong>3. Direction of change</strong>
                <span>{html.escape(evolving_label)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def display_primary_hexagram_step(reading):
    primary_hex = reading["primary_hex"]

    st.subheader("1. The Present Situation")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(get_hexagram_svg(reading["lines"], reading["changing_lines_indices"], line_width=120), unsafe_allow_html=True)
    with col2:
        st.markdown(f"### {primary_hex['number']}: {primary_hex['name_en']}")
        st.caption(f"{primary_hex['name_zh']} ({primary_hex.get('name_pinyin', '')})")
        st.info(get_hexagram_summary(primary_hex, "present"), icon="🧭")

    with st.expander("Read the Judgment"):
        display_bilingual_text(None, primary_hex.get("judgment_zh"), primary_hex["judgment_en"])
    with st.expander("Read the Image"):
        display_bilingual_text(None, primary_hex.get("image_zh"), primary_hex["image_en"])


def display_changing_lines_step(reading):
    changing_lines_indices = reading["changing_lines_indices"]
    primary_hex = reading["primary_hex"]

    st.subheader("2. The Turning Point")

    if not changing_lines_indices:
        st.markdown(
            """
            <div class="reading-card">
                <p class="eyebrow">Stable reading</p>
                <p>No lines are changing. Let the primary hexagram stand as the central answer, with emphasis on steadiness, integration, and returning to the core image.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        """
        <div class="reading-card">
            <p class="eyebrow">Changing lines</p>
            <p>These lines show where the situation is active, unstable, or ready to transform.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for i in changing_lines_indices:
        line_num = i + 1
        line_data = primary_hex["lines"][i]
        st.markdown(
            f"""
            <div class="line-card">
                <h4>Line {line_num}: {get_line_change_label(reading['lines'][i])}</h4>
                <p class="muted">{get_line_reflection_prompt(line_num)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        display_bilingual_text(None, line_data.get("line_zh"), line_data["line_en"])


def display_evolving_hexagram_step(reading):
    secondary_hex = reading["secondary_hex"]

    st.subheader("3. The Direction of Change")

    if not secondary_hex:
        st.markdown(
            """
            <div class="reading-card">
                <p class="eyebrow">No second hexagram</p>
                <p>Because there are no changing lines, this reading does not point to a separate evolving hexagram. Stay with the primary image and its counsel.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    secondary_lines_values = [
        line if line in [7, 8] else (7 if line == 6 else 8)
        for line in reading["lines"]
    ]

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(get_hexagram_svg(secondary_lines_values, [], line_width=120), unsafe_allow_html=True)
    with col2:
        st.markdown(f"### {secondary_hex['number']}: {secondary_hex['name_en']}")
        st.caption(f"{secondary_hex['name_zh']} ({secondary_hex.get('name_pinyin', '')})")
        st.info(get_hexagram_summary(secondary_hex, "evolving"), icon="🦋")

    with st.expander("Read the Judgment"):
        display_bilingual_text(None, secondary_hex.get("judgment_zh"), secondary_hex["judgment_en"])
    with st.expander("Read the Image"):
        display_bilingual_text(None, secondary_hex.get("image_zh"), secondary_hex["image_en"])


def display_reflection_step(reading):
    primary_hex = reading["primary_hex"]
    secondary_hex = reading["secondary_hex"]
    prompt = get_closing_reflection(primary_hex, secondary_hex, reading["changing_lines_indices"])

    st.subheader("4. Reflection")
    st.markdown(
        f"""
        <div class="reading-card reflection-card">
            <p class="eyebrow">Journal prompt</p>
            <p class="question">{prompt}</p>
            <p class="muted">Use this as the bridge between the oracle and your next concrete choice.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_hexagram_summary(hexagram, mode):
    """Returns a concise, plain-language summary for a hexagram."""
    theme = HEXAGRAM_THEME_SUMMARIES.get(hexagram["number"])
    if theme:
        theme = theme.replace("Your journal has recently emphasized ", "")
        theme = theme.rstrip(".")
    else:
        theme = hexagram["judgment_en"].rstrip(".")

    if mode == "evolving":
        return f"As this situation develops, the reading points toward {theme}."

    return f"This hexagram describes the present field of the question: {theme}."


def get_line_change_label(line_value):
    if line_value == 6:
        return "old yin changing into yang"
    if line_value == 9:
        return "old yang changing into yin"
    return "active line"


def get_line_reflection_prompt(line_num):
    prompts = {
        1: "Notice the first impulse. What is beginning beneath the surface?",
        2: "Look for the practical response. Where is alignment already available?",
        3: "Watch the pressure point. What becomes strained when you push too hard?",
        4: "Consider the threshold. What needs discernment before you step forward?",
        5: "Find the mature center. What would wise leadership look like here?",
        6: "Look at the culmination. What has reached its limit and needs release?",
    }
    return prompts.get(line_num, "What part of the situation is asking to move?")


def get_closing_reflection(primary_hex, secondary_hex, changing_lines_indices):
    if secondary_hex:
        return (
            f"If {primary_hex['name_en']} is the present condition and "
            f"{secondary_hex['name_en']} is where change leads, what one action would honor both?"
        )

    if changing_lines_indices:
        return f"What is {primary_hex['name_en']} asking you to change without losing your center?"

    return f"What would it mean to fully practice {primary_hex['name_en']} before seeking the next answer?"

def get_hexagram_svg(lines, changing_indices, line_height=15, line_width=100, gap=10):
    """Generates an SVG for a hexagram."""
    svg_height = (line_height + gap) * 6 - gap
    svg_lines = []
    for i, line_val in enumerate(reversed(lines)):
        is_changing = (len(lines) - 1 - i) in changing_indices
        y = i * (line_height + gap)
        line_color = "#ffc107" if is_changing else "#6c757d"
        animation = f'<animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{i*0.1}s" fill="freeze" />'
        if line_val in [6, 8]:
            svg_lines.append(f'<g transform="translate(0, {y})"><rect x="0" y="0" width="{line_width * 0.45}" height="{line_height}" fill="{line_color}" rx="2">{animation}</rect><rect x="{line_width * 0.55}" y="0" width="{line_width * 0.45}" height="{line_height}" fill="{line_color}" rx="2">{animation}</rect></g>')
        else:
            svg_lines.append(f'<g transform="translate(0, {y})"><rect x="0" y="0" width="{line_width}" height="{line_height}" fill="{line_color}" rx="2">{animation}</rect></g>')
    
    return f"""
        <div style="display: flex; justify-content: center; align-items: center;">
            <svg width="{line_width}" height="{svg_height}" viewbox="0 0 {line_width} {svg_height}">
                {''.join(svg_lines)}
            </svg>
        </div>
    """

def display_bilingual_text(header, text_zh, text_en):
    """Displays Chinese and English text."""
    if header:
        st.markdown(f"**{header}:**")
    if text_zh:
        st.markdown(f"<p style='font-size: 1.2em; font-family: serif;'>{html.escape(text_zh)}</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-style: italic; color: #888; border-left: 3px solid #ccc; padding-left: 10px;'>{html.escape(text_en)}</p>", unsafe_allow_html=True)
