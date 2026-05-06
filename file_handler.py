import json
import os
from functools import lru_cache

import pandas as pd

from constants import JOURNAL_FILE


class IChingDataError(Exception):
    """Raised when the I Ching source data cannot be loaded."""


@lru_cache(maxsize=1)
def load_iching_data():
    """Loads the I Ching data and creates a binary-to-hexagram map for efficient lookups."""
    try:
        with open('i_ching_data.json', 'r', encoding='utf-8') as f:
            iching_data = json.load(f)
        
        binary_to_hex_map = {
            hex_data['binary_code']: hex_data['number'] 
            for key, hex_data in iching_data.items() 
            if 'binary_code' in hex_data
        }
        
        return iching_data, binary_to_hex_map
    except FileNotFoundError as e:
        raise IChingDataError(
            "i_ching_data.json not found. Please make sure the data file is in the same directory as the app."
        ) from e
    except json.JSONDecodeError as e:
        raise IChingDataError(
            "Could not decode i_ching_data.json. Please check the file for formatting errors."
        ) from e

def save_reading_to_csv(reading):
    """Appends a single reading to the CSV journal."""
    primary_hex = reading['primary_hex']
    secondary_hex = reading.get('secondary_hex')
    
    record = {
        "Date": reading['timestamp'],
        "Question": reading['question'],
        "Lines": ",".join(map(str, reading['lines'])),
        "Primary Hexagram Number": primary_hex['number'],
        "Evolving Hexagram Number": secondary_hex['number'] if secondary_hex else None,
        "AI Interpretation": reading.get('ai_interpretation')
    }
    
    df = pd.DataFrame([record])
    df.to_csv(JOURNAL_FILE, mode='a', header=not os.path.exists(JOURNAL_FILE), index=False)

def load_journal():
    """Loads the reading journal as a DataFrame."""
    try:
        return pd.read_csv(JOURNAL_FILE)
    except FileNotFoundError:
        return pd.DataFrame()
    except pd.errors.EmptyDataError:
        return pd.DataFrame()

def enrich_journal(journal_df, iching_data):
    """Adds display and filtering fields to journal rows without changing the CSV."""
    if journal_df.empty:
        return journal_df

    enriched_df = journal_df.copy()
    enriched_df["Date Parsed"] = pd.to_datetime(enriched_df["Date"], errors="coerce")
    enriched_df["Primary Hexagram Number"] = pd.to_numeric(
        enriched_df["Primary Hexagram Number"], errors="coerce"
    )
    enriched_df["Evolving Hexagram Number"] = pd.to_numeric(
        enriched_df["Evolving Hexagram Number"], errors="coerce"
    )

    def hexagram_label(number):
        if pd.isna(number):
            return None

        hexagram = iching_data.get(str(int(number)))
        if not hexagram:
            return f"{int(number)}"

        return f"{hexagram['number']}: {hexagram['name_en']}"

    enriched_df["Primary Hexagram"] = enriched_df["Primary Hexagram Number"].apply(hexagram_label)
    enriched_df["Evolving Hexagram"] = enriched_df["Evolving Hexagram Number"].apply(hexagram_label)
    enriched_df["Has AI Contemplation"] = enriched_df["AI Interpretation"].notna() & (
        enriched_df["AI Interpretation"].astype(str).str.strip() != ""
    )
    enriched_df["Has Changing Lines"] = enriched_df["Lines"].astype(str).apply(
        lambda lines: any(line.strip() in ["6", "9"] for line in lines.split(","))
    )

    return enriched_df

def journal_to_markdown(journal_df):
    """Formats a journal DataFrame as a readable Markdown export."""
    sections = ["# I Ching Reading Journal\n"]

    for _, row in journal_df.iterrows():
        date = row.get("Date", "")
        question = row.get("Question", "")
        primary = row.get("Primary Hexagram", row.get("Primary Hexagram Number", ""))
        evolving = row.get("Evolving Hexagram")
        lines = row.get("Lines", "")
        ai_interpretation = row.get("AI Interpretation")

        sections.append(f"## {date} - {question}\n")
        sections.append(f"Primary: {primary}\n")
        if pd.notna(evolving) and evolving:
            sections.append(f"Evolving: {evolving}\n")
        sections.append(f"Lines: {lines}\n")

        if pd.notna(ai_interpretation) and str(ai_interpretation).strip():
            sections.append("\n### AI Contemplation\n")
            sections.append(str(ai_interpretation).strip())
            sections.append("\n")

    return "\n".join(sections)

def reconstruct_reading_from_row(row, iching_data):
    """Reconstructs a reading dictionary from a DataFrame row."""
    lines = [int(x) for x in row['Lines'].split(',')]
    primary_hex_num = int(row['Primary Hexagram Number'])
    evolving_hex_num = row['Evolving Hexagram Number']
    
    # Correctly handle the case where iching_data might be a tuple from caching
    if isinstance(iching_data, tuple):
        iching_data_dict = iching_data[0]
    else:
        iching_data_dict = iching_data

    reading = {
        "question": row['Question'],
        "lines": lines,
        "primary_hex": iching_data_dict[str(primary_hex_num)],
        "secondary_hex": iching_data_dict[str(int(evolving_hex_num))] if pd.notna(evolving_hex_num) else None,
        "changing_lines_indices": [i for i, line in enumerate(lines) if line in [6, 9]],
        "timestamp": row['Date']
    }
    return reading
