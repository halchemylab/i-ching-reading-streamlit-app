import streamlit as st

def display_reading(reading, is_journal=False):
    """Displays the entire classical reading results."""
    if not is_journal:
        st.divider()
        st.header("Your Reading")

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
        if not is_journal:
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

    if secondary_hex:
        with col2:
            st.subheader("Evolving Hexagram")
            secondary_lines_values = [l if l in [7, 8] else (7 if l == 6 else 8) for l in lines]
            st.markdown(get_hexagram_svg(secondary_lines_values, []), unsafe_allow_html=True)
            st.subheader(f"{secondary_hex['number']}: {secondary_hex['name_en']}")
            st.caption(f"{secondary_hex['name_zh']} ({secondary_hex.get('name_pinyin', '')})")
            if not is_journal:
                st.info("This hexagram reveals the direction of change and the potential evolution of your situation.", icon="🦋")
            with st.expander("Judgment"):
                display_bilingual_text(None, secondary_hex['judgment_zh'], secondary_hex['judgment_en'])
            with st.expander("Image"):
                display_bilingual_text(None, secondary_hex['image_zh'], secondary_hex['image_en'])

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
    st.markdown(f"<p style='font-size: 1.2em; font-family: serif;'>{text_zh}</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-style: italic; color: #888; border-left: 3px solid #ccc; padding-left: 10px;'>{text_en}</p>", unsafe_allow_html=True)
