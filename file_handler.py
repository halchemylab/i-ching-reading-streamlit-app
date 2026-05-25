import json
import os
import hashlib
import tempfile
import uuid
from functools import lru_cache
from pathlib import Path

import pandas as pd

from constants import ICHING_DATA_FILE, JOURNAL_FILE


class IChingDataError(Exception):
    """Raised when the I Ching source data cannot be loaded."""


class JournalValidationError(Exception):
    """Raised when a journal row or reading has invalid data."""


VALID_LINE_VALUES = {6, 7, 8, 9}
REQUIRED_JOURNAL_COLUMNS = [
    "Entry ID",
    "Date",
    "Question",
    "Lines",
    "Primary Hexagram Number",
    "Evolving Hexagram Number",
    "AI Interpretation",
    "Favorite",
    "Archived",
]


@lru_cache(maxsize=1)
def load_iching_data():
    """Loads the I Ching data and creates a binary-to-hexagram map for efficient lookups."""
    try:
        with open(ICHING_DATA_FILE, 'r', encoding='utf-8') as f:
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
    """Persists a single reading to the CSV journal."""
    validated_lines = parse_lines(reading.get("lines"))
    primary_hex = reading['primary_hex']
    secondary_hex = reading.get('secondary_hex')
    
    record = {
        "Entry ID": uuid.uuid4().hex,
        "Date": require_text(reading.get("timestamp"), "timestamp"),
        "Question": require_text(reading.get("question"), "question"),
        "Lines": ",".join(map(str, validated_lines)),
        "Primary Hexagram Number": primary_hex['number'],
        "Evolving Hexagram Number": secondary_hex['number'] if secondary_hex else None,
        "AI Interpretation": reading.get('ai_interpretation'),
        "Favorite": False,
        "Archived": False,
    }
    
    journal_df = load_journal()
    record_df = pd.DataFrame([record])
    updated_df = pd.concat(
        [journal_df, record_df],
        ignore_index=True,
        sort=False,
    )
    write_journal_df(updated_df)

def load_journal():
    """Loads the reading journal as a DataFrame."""
    try:
        journal_df = pd.read_csv(JOURNAL_FILE, on_bad_lines="skip")
        return ensure_journal_columns(journal_df)
    except FileNotFoundError:
        return empty_journal_df()
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return empty_journal_df()

def empty_journal_df():
    """Returns an empty journal DataFrame with the expected schema."""
    return pd.DataFrame(columns=REQUIRED_JOURNAL_COLUMNS)

def ensure_journal_columns(journal_df):
    """Adds missing journal columns so older or partial CSVs do not break rendering."""
    journal_df = journal_df.copy()

    for column in REQUIRED_JOURNAL_COLUMNS:
        if column not in journal_df.columns:
            journal_df[column] = None

    missing_entry_ids = journal_df["Entry ID"].isna() | (
        journal_df["Entry ID"].astype(str).str.strip() == ""
    )
    if missing_entry_ids.any():
        journal_df.loc[missing_entry_ids, "Entry ID"] = journal_df[missing_entry_ids].apply(
            make_legacy_entry_id,
            axis=1,
        )

    journal_df["Favorite"] = journal_df["Favorite"].apply(normalize_bool)
    journal_df["Archived"] = journal_df["Archived"].apply(normalize_bool)

    return journal_df

def make_legacy_entry_id(row):
    """Builds a stable ID for journal rows created before IDs existed."""
    identity_parts = [
        row.get("Date", ""),
        row.get("Question", ""),
        row.get("Lines", ""),
        row.get("Primary Hexagram Number", ""),
        row.get("Evolving Hexagram Number", ""),
    ]
    identity_text = "|".join("" if pd.isna(part) else str(part) for part in identity_parts)
    return hashlib.sha256(identity_text.encode("utf-8")).hexdigest()[:16]

def normalize_bool(value):
    """Normalizes CSV boolean-ish values for journal metadata."""
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False

    return str(value).strip().lower() in {"true", "1", "yes", "y"}

def update_journal_entry_flags(entry_id, favorite=None, archived=None):
    """Updates favorite/archive metadata for a single journal entry."""
    journal_df = load_journal()
    if journal_df.empty:
        raise JournalValidationError("Journal is empty.")

    entry_id = require_text(entry_id, "entry_id")
    matches = journal_df["Entry ID"].astype(str) == entry_id
    if not matches.any():
        raise JournalValidationError(f"Unknown journal entry ID: {entry_id}")

    if favorite is not None:
        journal_df.loc[matches, "Favorite"] = bool(favorite)
    if archived is not None:
        journal_df.loc[matches, "Archived"] = bool(archived)

    write_journal_df(journal_df)

def write_journal_df(journal_df):
    """Atomically writes the journal DataFrame to disk."""
    journal_path = Path(JOURNAL_FILE)
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=journal_path.parent,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            journal_df.to_csv(temp_file, index=False)

        os.replace(temp_path, journal_path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()

def require_text(value, field_name):
    """Validates required text fields before persistence."""
    if value is None or not str(value).strip():
        raise JournalValidationError(f"Missing required reading field: {field_name}")

    return str(value)

def parse_lines(value):
    """Parses and validates a six-line I Ching reading."""
    if isinstance(value, str):
        raw_lines = [line.strip() for line in value.split(",")]
    else:
        raw_lines = list(value or [])

    try:
        lines = [int(line) for line in raw_lines]
    except (TypeError, ValueError) as e:
        raise JournalValidationError("Reading lines must be numeric values.") from e

    if len(lines) != 6:
        raise JournalValidationError("A reading must contain exactly six lines.")

    invalid_lines = [line for line in lines if line not in VALID_LINE_VALUES]
    if invalid_lines:
        raise JournalValidationError(
            f"Reading lines must be one of {sorted(VALID_LINE_VALUES)}. Invalid values: {invalid_lines}"
        )

    return lines

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
    enriched_df["Has Changing Lines"] = enriched_df["Lines"].apply(has_changing_lines)

    return enriched_df

def has_changing_lines(lines):
    """Returns whether a saved line sequence contains changing lines."""
    try:
        return any(line in {6, 9} for line in parse_lines(lines))
    except JournalValidationError:
        return False

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
    lines = parse_lines(row['Lines'])
    primary_hex_num = normalize_hexagram_number(row['Primary Hexagram Number'], "Primary Hexagram Number")
    evolving_hex_num = row['Evolving Hexagram Number']
    
    # Correctly handle the case where iching_data might be a tuple from caching
    if isinstance(iching_data, tuple):
        iching_data_dict = iching_data[0]
    else:
        iching_data_dict = iching_data

    primary_hex = iching_data_dict.get(str(primary_hex_num))
    if not primary_hex:
        raise JournalValidationError(f"Unknown primary hexagram number: {primary_hex_num}")

    secondary_hex = None
    if pd.notna(evolving_hex_num):
        secondary_hex_num = normalize_hexagram_number(evolving_hex_num, "Evolving Hexagram Number")
        secondary_hex = iching_data_dict.get(str(secondary_hex_num))
        if not secondary_hex:
            raise JournalValidationError(f"Unknown evolving hexagram number: {secondary_hex_num}")

    reading = {
        "question": row['Question'],
        "lines": lines,
        "primary_hex": primary_hex,
        "secondary_hex": secondary_hex,
        "changing_lines_indices": [i for i, line in enumerate(lines) if line in [6, 9]],
        "timestamp": row['Date']
    }
    return reading

def normalize_hexagram_number(value, field_name):
    """Normalizes a saved hexagram number and raises a domain error if invalid."""
    try:
        return int(value)
    except (TypeError, ValueError) as e:
        raise JournalValidationError(f"Invalid {field_name}: {value}") from e
