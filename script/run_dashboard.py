"""Serve the local observability dashboard from saved pipeline artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "dashboard" / "index.html"
STAGES = {
    "baseline": {
        "quality": ROOT / "data/quality/baseline_quality_report.json",
        "freshness": ROOT / "data/quality/freshness_report.json",
        "metrics": ROOT / "data/results/baseline_metrics.json",
        "papers": ROOT / "data/clean/papers_clean.json",
    },
    "corrupted": {
        "quality": ROOT / "data/quality/corrupted_quality_report.json",
        "freshness": ROOT / "data/quality/corrupted_freshness_report.json",
        "metrics": ROOT / "data/results/corrupted_metrics.json",
        "papers": ROOT / "data/clean/papers_clean_corrupted.json",
    },
    "repaired": {
        "quality": ROOT / "data/quality/repaired_quality_report.json",
        "freshness": ROOT / "data/quality/repaired_freshness_report.json",
        "metrics": ROOT / "data/results/repaired_metrics.json",
        "papers": ROOT / "data/clean/papers_clean_repaired.json",
    },
}
AGE_LABELS = ("0–30", "31–90", "91–180", "181–365", ">365", "Tương lai", "Thiếu")
DRIFT_DELTA = 0.10


def _read_artifact(path: Path, warnings: list[str], modified: list[float]):
    try:
        content = path.read_text(encoding="utf-8")
        modified.append(path.stat().st_mtime)
        return json.loads(content)
    except FileNotFoundError:
        warnings.append(f"Chưa có artifact: {path.relative_to(ROOT)}")
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"Không đọc được {path.relative_to(ROOT)}: {type(exc).__name__}")
    return None


def _age_distribution(papers) -> dict[str, int] | None:
    if not isinstance(papers, list):
        return None
    counts = dict.fromkeys(AGE_LABELS, 0)
    for paper in papers:
        try:
            age = int(paper["age_days"])
        except (TypeError, ValueError, KeyError):
            counts["Thiếu"] += 1
            continue
        if age < 0:
            counts["Tương lai"] += 1
        elif age <= 30:
            counts["0–30"] += 1
        elif age <= 90:
            counts["31–90"] += 1
        elif age <= 180:
            counts["91–180"] += 1
        elif age <= 365:
            counts["181–365"] += 1
        else:
            counts[">365"] += 1
    return counts


def dashboard_state() -> dict:
    warnings: list[str] = []
    modified: list[float] = []
    stages = {}
    for name, files in STAGES.items():
        quality = _read_artifact(files["quality"], warnings, modified)
        freshness = _read_artifact(files["freshness"], warnings, modified)
        metrics = _read_artifact(files["metrics"], warnings, modified)
        papers = _read_artifact(files["papers"], warnings, modified)
        stages[name] = {
            "quality": {
                "success": quality.get("success"),
                "row_count": quality.get("row_count"),
                "short_summary_rows": quality.get("short_summary_rows", 0),
                "expectations": [
                    {
                        "type": item.get("type"),
                        "column": item.get("column"),
                        "success": item.get("success"),
                    }
                    for item in quality.get("expectations", [])
                ],
            } if isinstance(quality, dict) else None,
            "freshness": {
                "is_fresh": freshness.get("is_fresh"),
                "stale_rows": freshness.get("stale_rows"),
                "total_rows": freshness.get("total_rows"),
                "stale_ratio": freshness.get("stale_ratio"),
                "threshold_days": freshness.get("threshold_days"),
                "max_stale_ratio": freshness.get("max_stale_ratio"),
            } if isinstance(freshness, dict) else None,
            "metrics": {
                key: metrics.get(key)
                for key in (
                    "retrieval_hit_rate", "mean_token_f1",
                    "judge_accuracy", "fallback_judge_count",
                )
            } if isinstance(metrics, dict) else None,
            "paper_count": len(papers) if isinstance(papers, list) else None,
            "age_distribution": _age_distribution(papers),
        }

    alerts = []
    baseline_freshness = stages["baseline"]["freshness"]
    baseline_stale = baseline_freshness.get("stale_ratio") if baseline_freshness else None
    for name, stage in stages.items():
        quality = stage["quality"]
        freshness = stage["freshness"]
        if quality and quality["success"] is False:
            alerts.append({
                "stage": name, "kind": "quality",
                "message": f"{name}: Quality Gate không đạt.",
            })
        if freshness and freshness["is_fresh"] is False:
            alerts.append({
                "stage": name, "kind": "freshness",
                "message": f"{name}: tỷ lệ bài cũ vượt ngưỡng Freshness SLA.",
            })
        stale = freshness.get("stale_ratio") if freshness else None
        if (
            name != "baseline" and isinstance(stale, (int, float))
            and isinstance(baseline_stale, (int, float))
            and stale - baseline_stale >= DRIFT_DELTA
        ):
            alerts.append({
                "stage": name, "kind": "drift",
                "message": (
                    f"{name}: tỷ lệ bài trên 180 ngày tăng "
                    f"{(stale - baseline_stale) * 100:.1f} điểm phần trăm so với baseline."
                ),
            })
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "artifacts_updated_at": (
            datetime.fromtimestamp(max(modified), timezone.utc).isoformat(timespec="seconds")
            if modified else None
        ),
        "refresh_seconds": 5,
        "drift_delta_threshold": DRIFT_DELTA,
        "stages": stages,
        "alerts": alerts,
        "warnings": warnings,
    }


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        route = urlsplit(self.path).path
        if route in {"/", "/index.html"}:
            body = PAGE.read_bytes()
            content_type = "text/html; charset=utf-8"
        elif route == "/api/state":
            body = json.dumps(dashboard_state(), ensure_ascii=False).encode("utf-8")
            content_type = "application/json; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local pipeline observability dashboard")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), DashboardHandler)
    print(f"Dashboard: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
