from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
import json
from math import ceil
from pathlib import Path

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    """Inject six reproducible data faults and log every affected source row."""
    required = {
        "paper_id", "title", "summary", "published", "age_days",
        "authors_joined", "categories_joined", "text_for_embedding",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Clean dataframe is missing columns: {', '.join(missing)}")

    work = df.copy(deep=True).reset_index(drop=True)
    work["_source_index"] = work.index
    events: list[dict] = []
    operations = (
        "drop_latest_records", "blank_summary", "inject_noise",
        "truncate_title", "stale_date", "duplicate_rows",
    )

    def snapshot(row: pd.Series) -> dict:
        values = row.drop(labels="_source_index").to_dict()
        return json.loads(pd.DataFrame([values]).to_json(orient="records", date_format="iso"))[0]

    def rebuild_text(index: int) -> None:
        row = work.loc[index]
        work.at[index, "text_for_embedding"] = "\n".join((
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Published: {row['published']}",
            f"Categories: {row['categories_joined']}",
            f"Summary: {row['summary']}",
        ))

    drop_count = min(max(len(work) - 1, 0), ceil(len(work) * 0.20))
    if drop_count:
        ranked = work.assign(_sort_date=pd.to_datetime(work["published"]))
        latest = ranked.sort_values(
            ["_sort_date", "paper_id"], ascending=[False, True]
        ).head(drop_count).index
        for index in latest:
            row = work.loc[index]
            events.append({
                "operation": "drop_latest_records",
                "source_index": int(row["_source_index"]),
                "paper_id": str(row["paper_id"]),
                "before": snapshot(row),
                "after": None,
            })
        work = work.drop(index=latest).reset_index(drop=True)

    if not work.empty:
        mutation_count = max(1, len(work) // 5)
        for operation_index, operation in enumerate(operations[1:5]):
            for offset in range(mutation_count):
                index = (operation_index * mutation_count + offset) % len(work)
                row = work.loc[index]
                before = snapshot(row)
                if operation == "blank_summary":
                    work.at[index, "summary"] = ""
                elif operation == "inject_noise":
                    work.at[index, "summary"] = (
                        str(row["summary"]) + " CORRUPTED NOISE @@@ ### $$$"
                    )
                elif operation == "truncate_title":
                    title = str(row["title"])
                    work.at[index, "title"] = title[:7] if len(title) > 7 else (
                        "X" if title != "X" else "Y"
                    )
                else:
                    published = date.fromisoformat(str(row["published"])[:10])
                    work.at[index, "published"] = (
                        published - timedelta(days=365)
                    ).isoformat()
                    work.at[index, "age_days"] = int(row["age_days"]) + 365
                if operation in {"blank_summary", "inject_noise"} and "summary_chars" in work:
                    work.at[index, "summary_chars"] = len(work.at[index, "summary"])
                rebuild_text(index)
                events.append({
                    "operation": operation,
                    "source_index": int(row["_source_index"]),
                    "paper_id": str(row["paper_id"]),
                    "before": before,
                    "after": snapshot(work.loc[index]),
                })

        duplicates = []
        for index in range(len(work) - mutation_count, len(work)):
            row = work.loc[index]
            before = snapshot(row)
            duplicates.append(work.loc[[index]].copy())
            events.append({
                "operation": "duplicate_rows",
                "source_index": int(row["_source_index"]),
                "paper_id": str(row["paper_id"]),
                "before": before,
                "after": before,
                "new_index": len(work) + len(duplicates) - 1,
            })
        work = pd.concat([work, *duplicates], ignore_index=True)

    result = work.drop(columns="_source_index")
    counts = Counter(event["operation"] for event in events)
    write_json(Path(output_log_path), {
        "input_rows": len(df),
        "output_rows": len(result),
        "counts": {operation: counts[operation] for operation in operations},
        "events": events,
    })
    return result
