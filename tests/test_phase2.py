from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from core.config import load_settings
from core.utils import write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import parse_crossref_payload
from ingestion.repair import repair_from_raw_snapshot
from observability.reporting import generate_corruption_report
from pipelines.corruption_flow import run_corruption_flow_pipeline


class RepairFromRawSnapshotTests(unittest.TestCase):
    def test_repair_rebuilds_clean_data_without_changing_raw_snapshot(self) -> None:
        payload = {"message": {"items": [
            {
                "DOI": f"10.1234/paper-{index}",
                "title": [f"Research paper {index}"],
                "abstract": f"<jats:p>Abstract for paper {index} with enough content for the quality gate.</jats:p>",
                "author": [{"given": "Ada", "family": "Lovelace"}],
                "published": {"date-parts": [[2026, 9, 15]]},
            }
            for index in range(6)
        ]}}
        with TemporaryDirectory() as directory:
            root = Path(directory)
            raw_path = root / "raw" / "crossref_response.json"
            raw_path.parent.mkdir(parents=True)
            raw_path.write_text(json.dumps(payload), encoding="utf-8")
            original_bytes = raw_path.read_bytes()
            settings = SimpleNamespace(paths=SimpleNamespace(
                raw_api_response=raw_path,
                repaired_clean_csv=root / "clean" / "papers_clean_repaired.csv",
                repaired_clean_json=root / "clean" / "papers_clean_repaired.json",
            ))
            run_date = datetime(2026, 9, 26, tzinfo=UTC)

            first = repair_from_raw_snapshot(settings, run_date)
            second = repair_from_raw_snapshot(settings, run_date)

            pd.testing.assert_frame_equal(first, second)
            self.assertEqual(len(first), 6)
            self.assertEqual(first["age_days"].unique().tolist(), [11])
            self.assertTrue(first["summary"].str.contains("<jats:p>", regex=False).eq(False).all())
            self.assertEqual(raw_path.read_bytes(), original_bytes)
            self.assertTrue(settings.paths.repaired_clean_csv.is_file())
            saved = json.loads(settings.paths.repaired_clean_json.read_text(encoding="utf-8"))
            self.assertEqual(len(saved), 6)


class GenerateCorruptionReportTests(unittest.TestCase):
    def test_report_compares_three_measured_states(self) -> None:
        def metrics(hit: float, f1: float, judge: float, score: float, fallback: int = 0) -> dict:
            return {
                "samples": 10,
                "retrieval_hit_rate": hit,
                "mean_token_f1": f1,
                "judge_accuracy": judge,
                "mean_judge_score": score,
                "fallback_judge_count": fallback,
            }

        with TemporaryDirectory() as directory:
            report_path = Path(directory) / "corruption_report.md"
            generate_corruption_report(
                report_path,
                metrics(1.0, 0.8, 0.8, 4.2),
                metrics(0.4, 0.3, 0.3, 2.1, 10),
                metrics(1.0, 0.8, 0.8, 4.2, 10),
                {"success": False, "gx_success": False, "row_count": 22},
                {"success": True, "gx_success": True, "row_count": 24},
                {"is_fresh": False, "stale_ratio": 0.3, "stale_rows": 7, "total_rows": 22},
                {"is_fresh": True, "stale_ratio": 0.0, "stale_rows": 0, "total_rows": 24},
            )
            text = report_path.read_text(encoding="utf-8")

        self.assertIn("| Chỉ số | Baseline | Corrupted | Repaired |", text)
        self.assertIn("| Retrieval Hit Rate | 100.00% | 40.00% | 100.00% |", text)
        self.assertIn("| Mean Token F1 | 0.8000 | 0.3000 | 0.8000 |", text)
        self.assertIn("| Quality gate |", text)
        self.assertIn("| Freshness SLA |", text)
        self.assertIn("60.00 điểm phần trăm", text)
        self.assertIn("judge accuracy không thể so sánh trực tiếp", text)


class CorruptionFlowPipelineTests(unittest.TestCase):
    def test_pipeline_uses_same_test_set_and_repairs_from_raw(self) -> None:
        payload = {"message": {"items": [
            {
                "DOI": f"10.1234/paper-{index}",
                "title": [f"Research paper {index}"],
                "abstract": f"<jats:p>Abstract for paper {index} with enough content for the quality gate.</jats:p>",
                "author": [{"given": "Ada", "family": "Lovelace"}],
                "published": {"date-parts": [[2026, 9, 15 - index]]},
            }
            for index in range(10)
        ]}}
        with TemporaryDirectory() as directory:
            settings = load_settings(Path(directory))
            settings.paths.raw_api_response.parent.mkdir(parents=True)
            raw_bytes = json.dumps(payload).encode("utf-8")
            settings.paths.raw_api_response.write_bytes(raw_bytes)
            baseline = build_clean_dataframe(
                parse_crossref_payload(payload), datetime(2026, 9, 26, tzinfo=UTC)
            )
            write_json(settings.paths.clean_json, baseline.to_dict(orient="records"))
            write_json(settings.paths.eval_testset, [{
                "id": "eval_001",
                "question_type": "summary",
                "question": "What is the summary of the paper 'Research paper 0'?",
                "ground_truth": "Abstract for paper 0.",
                "ground_truth_doc_ids": ["10.1234/paper-0"],
            }])
            baseline_metrics = {
                "samples": 1, "retrieval_hit_rate": 1.0, "mean_token_f1": 0.8,
                "judge_accuracy": 1.0, "mean_judge_score": 5.0, "fallback_judge_count": 0,
            }
            write_json(settings.paths.baseline_metrics, baseline_metrics)
            test_set_paths = []

            def fake_evaluate(_settings, index, test_set_path, metrics_path, answers_path):
                test_set_paths.append(test_set_path)
                score = 0.2 if index.row_count < len(baseline) else 0.8
                summary = {
                    "samples": 1, "retrieval_hit_rate": score,
                    "mean_token_f1": score, "judge_accuracy": score,
                    "mean_judge_score": score * 5, "fallback_judge_count": 0,
                }
                write_json(metrics_path, summary)
                write_json(answers_path, [])
                return SimpleNamespace(summary=summary)

            with patch(
                "pipelines.corruption_flow.LocalEmbeddingIndex.build",
                side_effect=lambda df, _settings, _path: SimpleNamespace(row_count=len(df)),
            ), patch("pipelines.corruption_flow.evaluate_pipeline", side_effect=fake_evaluate):
                result = run_corruption_flow_pipeline(settings)

            self.assertEqual(test_set_paths, [settings.paths.eval_testset] * 2)
            self.assertEqual(settings.paths.raw_api_response.read_bytes(), raw_bytes)
            corruption_log = json.loads(settings.paths.corruption_log.read_text(encoding="utf-8"))
            self.assertEqual(set(corruption_log["counts"]), {
                "drop_latest_records", "blank_summary", "inject_noise",
                "truncate_title", "stale_date", "duplicate_rows",
            })
            self.assertTrue(all(count > 0 for count in corruption_log["counts"].values()))
            self.assertTrue(settings.paths.comparison_report.is_file())
            self.assertTrue(settings.paths.corrupted_metrics.is_file())
            self.assertTrue(settings.paths.repaired_metrics.is_file())
            self.assertFalse(result["corrupted_quality"]["success"])
            self.assertTrue(result["repaired_quality"]["success"])
            self.assertEqual(
                set(pd.read_json(settings.paths.repaired_clean_json)["paper_id"]),
                set(baseline["paper_id"]),
            )
