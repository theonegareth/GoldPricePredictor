import re
import json
from pathlib import Path

import pandas as pd


def extract_array_from_html(html_text: str) -> str:
    """
    Extract the JavaScript-style array of [timestamp_ms, value] pairs from the HTML.

    Assumes the content starts with [[timestamp,value], ... ] before any <script> tag.
    Returns the raw array string without trailing script or HTML.
    """
    # Find the first occurrence of [[ and the last occurrence of ]]
    start = html_text.find("[[")
    end = html_text.rfind("]]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Could not locate a JS array like [[timestamp, value], ...] in HTML.")
    array_str = html_text[start : end + 2]

    # Some HTML files may have trailing commas or minor issues; try a minimal cleanup
    # Ensure there is no trailing comma before final ]]
    array_str = re.sub(r",\s*]]$", "]]", array_str.strip())

    return array_str


def parse_pairs(array_str: str) -> pd.DataFrame:
    """
    Parse the array string into a DataFrame with columns [Time (ms), Gold Price].
    """
    # Safely convert JS-style array to Python list via json:
    # Replace single JS-specific artifacts if needed (here it is already JSON-compatible)
    try:
        data = json.loads(array_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse array string as JSON: {e}") from e

    if not isinstance(data, list) or not all(
        isinstance(row, (list, tuple)) and len(row) == 2 for row in data
    ):
        raise ValueError("Parsed data is not a list of [timestamp_ms, value] pairs.")

    # Build DataFrame with explicit column names
    df = pd.DataFrame(data, columns=["Time (ms)", "Gold Price"])
    return df


def convert_sell_htm_to_csv(
    html_path: Path,
    csv_path: Path,
) -> None:
    """
    End-to-end conversion:
    - Read sell.htm
    - Extract JS array
    - Parse to DataFrame
    - Convert timestamp_ms to UTC datetime
    - Save as CSV with [datetime, sell_price]
    """
    html_text = html_path.read_text(encoding="utf-8", errors="ignore")
    array_str = extract_array_from_html(html_text)
    df = parse_pairs(array_str)

    # Ensure Gold Price is numeric; drop invalids
    df["Gold Price"] = pd.to_numeric(df["Gold Price"], errors="coerce")
    df = df.dropna(subset=["Gold Price"])

    # Ensure Time (ms) is integer
    df["Time (ms)"] = pd.to_numeric(df["Time (ms)"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["Time (ms)"])

    # Write CSV with header: Time (ms),Gold Price
    df.to_csv(csv_path, index=False)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    html_file = base_dir / "sell.htm"
    out_file = base_dir / "sell.csv"

    if not html_file.exists():
        raise FileNotFoundError(f"Input file not found: {html_file}")

    convert_sell_htm_to_csv(html_file, out_file)
    print(f"Created {out_file} with cleaned columns [Time (ms), Gold Price].")