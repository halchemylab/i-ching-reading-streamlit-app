import streamlit as st
import json
import os
import pandas as pd

from constants import JOURNAL_FILE

@st.cache_data
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
    except FileNotFoundError:
        st.error("Error: i_ching_data.json not found. Please make sure the data file is in the same directory as the app.")
        return None, None
    except json.JSONDecodeError:
        st.error("Error: Could not decode i_ching_data.json. Please check the file for formatting errors.")
        return None, None

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

def reconstruct_reading_from_row(row, iching_data):
    """Reconstructs a reading dictionary from a DataFrame row."""
    lines = [int(x) for x in row['Lines'].split(',')]
    primary_hex_num = row['Primary Hexagram Number']
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
