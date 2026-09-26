from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ingestion.corruption import corrupt_clean_dataframe


class CorruptCleanDataframeTests(unittest.TestCase):
    def test_six_corruptions_are_logged_and_embedding_text_is_rebuilt(self) -> None:
        rows = []
        for index in range(10):
            published = date(2026, 9, 20) - timedelta(days=index)
            summary = f"Summary for paper {index} with enough detail to remain meaningful."
            rows.append({
                "paper_id": f"10.1234/paper-{index}",
                "title": f"Research paper number {index}",
                "summary": summary,
                "authors_joined": "Author One",
                "categories_joined": "Computer Science",
                "published": published.isoformat(),
                "age_days": 6 + index,
                "summary_chars": len(summary),
                "text_for_embedding": (
                    f"Title: Research paper number {index}\n"
                    "Authors: Author One\n"
                    f"Published: {published.isoformat()}\n"
                    "Categories: Computer Science\n"
                    f"Summary: {summary}"
                ),
            })
        clean_df = pd.DataFrame(rows)
        original = clean_df.copy(deep=True)

        with TemporaryDirectory() as directory:
            log_path = Path(directory) / "corruption_log.json"
            corrupted = corrupt_clean_dataframe(clean_df, log_path)
            log = json.loads(log_path.read_text(encoding="utf-8"))

        pd.testing.assert_frame_equal(clean_df, original)
        self.assertEqual(len(corrupted), 9)
        self.assertFalse(corrupted["paper_id"].isin(("10.1234/paper-0", "10.1234/paper-1")).any())
        self.assertEqual(corrupted["paper_id"].duplicated().sum(), 1)

        expected_operations = {
            "drop_latest_records": 2,
            "blank_summary": 1,
            "inject_noise": 1,
            "truncate_title": 1,
            "stale_date": 1,
            "duplicate_rows": 1,
        }
        self.assertEqual(log["counts"], expected_operations)
        self.assertEqual(len(log["events"]), 7)
        for event in log["events"]:
            self.assertIn("paper_id", event)
            self.assertIn("source_index", event)
            self.assertIn("before", event)
            self.assertIn("after", event)

        self.assertEqual((corrupted["summary"] == "").sum(), 1)
        self.assertEqual(corrupted["summary"].str.contains("CORRUPTED NOISE").sum(), 1)
        self.assertEqual(corrupted["title"].str.len().lt(8).sum(), 1)
        stale_event = next(event for event in log["events"] if event["operation"] == "stale_date")
        stale_row = corrupted.loc[corrupted["paper_id"] == stale_event["paper_id"]].iloc[0]
        self.assertEqual(stale_row["age_days"], stale_event["before"]["age_days"] + 365)
        self.assertEqual(
            (date.fromisoformat(stale_event["before"]["published"]) - date.fromisoformat(stale_row["published"])).days,
            365,
        )
        for row in corrupted.to_dict(orient="records"):
            self.assertEqual(row["summary_chars"], len(row["summary"]))
            self.assertEqual(
                row["text_for_embedding"],
                "\n".join((
                    f"Title: {row['title']}",
                    f"Authors: {row['authors_joined']}",
                    f"Published: {row['published']}",
                    f"Categories: {row['categories_joined']}",
                    f"Summary: {row['summary']}",
                )),
            )


if __name__ == "__main__":
    unittest.main()
