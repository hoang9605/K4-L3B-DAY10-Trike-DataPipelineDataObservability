from __future__ import annotations

from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the source, benchmark, quality, and freshness results."""
    source_rows = "\n".join(f"| {key} | {value} |" for key, value in source_summary.items())
    expectation_rows = "\n".join(
        f"| {item['type']} | {item['column'] or '—'} | {'Đạt' if item['success'] else 'Không đạt'} |"
        for item in quality["expectations"]
    )
    type_rows = "\n".join(
        f"| {name} | {values['samples']} | {values['retrieval_hit_rate']:.2%} | {values['mean_token_f1']:.4f} |"
        for name, values in metrics.get("question_type_metrics", {}).items()
    )
    lines = [
        "# Báo cáo Phase 1 — Baseline",
        "",
        "## Dữ liệu đầu vào",
        "",
        "| Mục | Giá trị |",
        "| --- | --- |",
        source_rows,
        "",
        "## Chỉ số đánh giá RAG",
        "",
        "| Chỉ số | Giá trị |",
        "| --- | ---: |",
        f"| Số câu hỏi | {metrics['samples']} |",
        f"| Retrieval Hit Rate | {metrics['retrieval_hit_rate']:.2%} |",
        f"| Mean Token F1 | {metrics['mean_token_f1']:.4f} |",
        f"| Judge accuracy | {metrics['judge_accuracy']:.2%} |",
        f"| Mean judge score | {metrics['mean_judge_score']:.2f}/5 |",
        f"| Số câu dùng heuristic judge | {metrics.get('fallback_judge_count', 0)} |",
        "",
        "| Loại câu hỏi | Số câu | Hit Rate | Token F1 |",
        "| --- | ---: | ---: | ---: |",
        type_rows,
        "",
        "## Kiểm định chất lượng GX 1.x",
        "",
        f"**Kết quả gate:** {'Đạt' if quality['success'] else 'Không đạt'} ({quality['row_count']} bản ghi).",
        "",
        "| Expectation | Cột | Kết quả |",
        "| --- | --- | --- |",
        expectation_rows,
        "",
        "## Độ tươi dữ liệu",
        "",
        "| Chỉ số | Giá trị |",
        "| --- | ---: |",
        f"| Ngưỡng tuổi | {freshness['threshold_days']} ngày |",
        f"| Bài báo quá hạn | {freshness['stale_rows']}/{freshness['total_rows']} |",
        f"| Tỷ lệ quá hạn | {freshness['stale_ratio']:.2%} |",
        f"| Ngưỡng cảnh báo | {freshness['max_stale_ratio']:.0%} |",
        f"| Freshness SLA | {'Đạt' if freshness['is_fresh'] else 'Cảnh báo'} |",
        f"| Mới nhất | {freshness['latest_published'] or 'Không có'} |",
        f"| Cũ nhất | {freshness['oldest_published'] or 'Không có'} |",
        "",
    ]
    if metrics.get("fallback_judge_count"):
        lines.extend((
            "Judge dùng heuristic khi nhà cung cấp LLM không khả dụng; Retrieval Hit Rate và Token F1 vẫn được tính từ câu trả lời truy xuất.",
            "",
        ))
    category_stats = metrics.get("question_type_metrics", {}).get("categories")
    if source_summary.get("Papers with categories") == 0 and category_stats:
        lines.extend((
            f"Crossref không cung cấp subject cho các bài trong snapshot này. {category_stats['samples']} câu hỏi categories kiểm tra khả năng xử lý metadata thiếu; Token F1 của nhóm là {category_stats['mean_token_f1']:.4f}.",
            "",
        ))
    lines.extend((
        "Các câu hỏi benchmark chứa đúng tiêu đề bài báo; bước QA ưu tiên tra cứu tiêu đề chính xác trước khi tính Hit Rate.",
        "",
    ))
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write measured RAG, quality, and freshness comparisons for three states."""
    states = (baseline_metrics, corrupted_metrics, repaired_metrics)

    def row(label: str, key: str, fmt: str) -> str:
        return "| " + label + " | " + " | ".join(
            format(state[key], fmt) for state in states
        ) + " |"

    def gate_status(quality: dict[str, Any]) -> str:
        return "Đạt" if quality["success"] else "Không đạt"

    def freshness_status(freshness: dict[str, Any]) -> str:
        return "Đạt" if freshness["is_fresh"] else "Cảnh báo"

    hit_loss = baseline_metrics["retrieval_hit_rate"] - corrupted_metrics["retrieval_hit_rate"]
    f1_loss = baseline_metrics["mean_token_f1"] - corrupted_metrics["mean_token_f1"]
    hit_gap = repaired_metrics["retrieval_hit_rate"] - baseline_metrics["retrieval_hit_rate"]
    f1_gap = repaired_metrics["mean_token_f1"] - baseline_metrics["mean_token_f1"]
    if hit_loss > 0 or f1_loss > 0:
        impact = (
            f"Dữ liệu lỗi làm Hit Rate giảm {hit_loss * 100:.2f} điểm phần trăm và "
            f"Token F1 giảm {f1_loss:.4f} so với baseline."
        )
    else:
        impact = "Bộ câu hỏi hiện tại chưa cho thấy suy giảm Hit Rate hoặc Token F1 sau tiêm lỗi."
    if abs(hit_gap) < 1e-9 and abs(f1_gap) < 1e-9:
        recovery = "Sau phục hồi, Hit Rate và Token F1 trở về đúng mức baseline."
    else:
        recovery = (
            f"Sau phục hồi, chênh lệch so với baseline là {hit_gap * 100:+.2f} điểm phần trăm "
            f"Hit Rate và {f1_gap:+.4f} Token F1."
        )
    fallback_counts = [state.get("fallback_judge_count", 0) for state in states]
    judge_note = (
        "Số lượt heuristic judge khác nhau giữa ba trạng thái "
        f"({fallback_counts[0]}/{fallback_counts[1]}/{fallback_counts[2]}), "
        "nên judge accuracy không thể so sánh trực tiếp; ưu tiên Hit Rate và Token F1."
        if len(set(fallback_counts)) > 1 else
        "Cả ba trạng thái dùng cùng chế độ judge."
    )

    lines = [
        "# Báo cáo Phase 2 — Baseline vs Corrupted vs Repaired",
        "",
        "Ba trạng thái được đánh giá bằng cùng test set đã lưu ở data/eval/test_set.json.",
        "Dữ liệu repaired được dựng lại từ data/raw/crossref_response.json, không từ dữ liệu corrupted.",
        "",
        "## So sánh hiệu năng RAG",
        "",
        "| Chỉ số | Baseline | Corrupted | Repaired |",
        "| --- | ---: | ---: | ---: |",
        row("Số câu hỏi", "samples", "d"),
        row("Retrieval Hit Rate", "retrieval_hit_rate", ".2%"),
        row("Mean Token F1", "mean_token_f1", ".4f"),
        row("Judge accuracy", "judge_accuracy", ".2%"),
        row("Mean judge score /5", "mean_judge_score", ".2f"),
        row("Heuristic judge", "fallback_judge_count", "d"),
        "",
        "## Tín hiệu chất lượng dữ liệu",
        "",
        "| Chỉ số | Baseline | Corrupted | Repaired |",
        "| --- | --- | --- | --- |",
        f"| Quality gate | Xem báo cáo Phase 1 | {gate_status(corrupted_quality)} | {gate_status(repaired_quality)} |",
        f"| Số bản ghi | — | {corrupted_quality['row_count']} | {repaired_quality['row_count']} |",
        f"| Freshness SLA | Xem báo cáo Phase 1 | {freshness_status(corrupted_freshness)} | {freshness_status(repaired_freshness)} |",
        f"| Bài quá 180 ngày | — | {corrupted_freshness['stale_rows']}/{corrupted_freshness['total_rows']} | {repaired_freshness['stale_rows']}/{repaired_freshness['total_rows']} |",
        f"| Tỷ lệ bài cũ | — | {corrupted_freshness['stale_ratio']:.2%} | {repaired_freshness['stale_ratio']:.2%} |",
        "",
        "## Phân tích từ số liệu",
        "",
        impact,
        recovery,
        (
            "Quality gate báo lỗi ở bản corrupted nhưng bước đánh giá RAG vẫn chạy để đo ảnh hưởng; "
            "đây là cách quan sát nguy cơ silent failure nếu bỏ qua gate."
            if not corrupted_quality["success"] else
            "Quality gate vẫn đạt ở bản corrupted; các lỗi này chưa được bộ expectation hiện tại phát hiện đầy đủ."
        ),
        "",
        "Các câu hỏi benchmark chứa nguyên tiêu đề bài báo, nên Hit Rate có lợi thế tra cứu chính xác.",
        judge_note,
        "",
        "## Artifact",
        "",
        "- [Nhật ký tiêm lỗi](../results/corruption_log.json)",
        "- [Baseline metrics](../results/baseline_metrics.json)",
        "- [Corrupted metrics](../results/corrupted_metrics.json)",
        "- [Repaired metrics](../results/repaired_metrics.json)",
        "- [Corrupted quality](../quality/corrupted_quality_report.json)",
        "- [Repaired quality](../quality/repaired_quality_report.json)",
        "",
    ]
    write_text(report_path, "\n".join(lines))
