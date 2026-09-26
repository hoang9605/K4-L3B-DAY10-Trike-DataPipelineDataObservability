from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.repair import repair_from_raw_snapshot
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def run_corruption_flow_pipeline(settings: Settings) -> dict[str, Any]:
    """Compare corrupted and raw-snapshot-repaired RAG against the saved baseline."""
    paths = settings.paths
    for required_path in (
        paths.clean_json, paths.baseline_metrics, paths.eval_testset, paths.raw_api_response
    ):
        if not required_path.is_file():
            raise FileNotFoundError(f"Phase 2 requires the saved Phase 1 artifact: {required_path}")

    clean_df = pd.DataFrame(read_json(paths.clean_json))
    baseline_metrics = read_json(paths.baseline_metrics)
    test_set = read_json(paths.eval_testset)
    if clean_df.empty or len(test_set) != baseline_metrics["samples"]:
        raise ValueError("Saved clean data and baseline evaluation set are inconsistent")

    first = clean_df.iloc[0]
    baseline_run_day = date.fromisoformat(str(first["published"])[:10]) + timedelta(
        days=int(first["age_days"])
    )
    baseline_run_date = datetime.combine(baseline_run_day, time.min, UTC)

    corrupted_df = corrupt_clean_dataframe(clean_df, paths.corruption_log)
    write_csv(corrupted_df, paths.corrupted_clean_csv)
    write_json(paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, paths.quality_dir / "corrupted_freshness_report.json"
    )
    # Evaluate the failing gate intentionally to measure the impact it would have hidden.
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, paths.corrupted_embeddings_json
    )
    corrupted_evaluation = evaluate_pipeline(
        settings, corrupted_index, paths.eval_testset,
        paths.corrupted_metrics, paths.corrupted_answers,
    )

    repaired_df = repair_from_raw_snapshot(settings, baseline_run_date)
    if set(repaired_df["paper_id"]) != set(clean_df["paper_id"]):
        raise RuntimeError("Raw snapshot contains different paper IDs than the Phase 1 baseline")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, paths.quality_dir / "repaired_freshness_report.json"
    )
    if not repaired_quality["success"]:
        raise RuntimeError(
            "Repaired data failed the quality gate; see data/quality/repaired_quality_report.json"
        )
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, paths.repaired_embeddings_json
    )
    repaired_evaluation = evaluate_pipeline(
        settings, repaired_index, paths.eval_testset,
        paths.repaired_metrics, paths.repaired_answers,
    )

    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_evaluation.summary,
        repaired_evaluation.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    return {
        "baseline_metrics": baseline_metrics,
        "corrupted_metrics": corrupted_evaluation.summary,
        "repaired_metrics": repaired_evaluation.summary,
        "corrupted_quality": corrupted_quality,
        "repaired_quality": repaired_quality,
        "corrupted_freshness": corrupted_freshness,
        "repaired_freshness": repaired_freshness,
        "report_path": str(paths.comparison_report),
    }


def main() -> None:
    result = run_corruption_flow_pipeline(load_settings())
    baseline = result["baseline_metrics"]
    corrupted = result["corrupted_metrics"]
    repaired = result["repaired_metrics"]
    print("| Metric | Baseline | Corrupted | Repaired |")
    print("| --- | ---: | ---: | ---: |")
    for label, key, fmt in (
        ("Retrieval Hit Rate", "retrieval_hit_rate", ".2%"),
        ("Mean Token F1", "mean_token_f1", ".4f"),
        ("Judge accuracy", "judge_accuracy", ".2%"),
        ("Mean judge score /5", "mean_judge_score", ".2f"),
    ):
        print("| " + label + " | " + " | ".join(
            format(state[key], fmt) for state in (baseline, corrupted, repaired)
        ) + " |")
    print(f"Report: {result['report_path']}")
