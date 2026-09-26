from __future__ import annotations

from datetime import UTC, datetime
import json

import pandas as pd

from core.config import Settings
from core.utils import write_csv, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import parse_crossref_payload


def repair_from_raw_snapshot(
    settings: Settings, run_date: datetime | None = None
) -> pd.DataFrame:
    """Rebuild clean records from the preserved Crossref response, without network access."""
    raw_path = settings.paths.raw_api_response
    if not raw_path.is_file():
        raise FileNotFoundError(f"Raw Crossref snapshot is missing: {raw_path}")

    payload = json.loads(raw_path.read_bytes())
    records = parse_crossref_payload(payload)
    repaired = build_clean_dataframe(records, run_date or datetime.now(UTC))
    if repaired.empty:
        raise ValueError(f"Raw Crossref snapshot produced no repairable records: {raw_path}")

    write_csv(repaired, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired.to_dict(orient="records"))
    return repaired
