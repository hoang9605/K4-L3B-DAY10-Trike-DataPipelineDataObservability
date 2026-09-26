# Báo cáo Phase 2 — Baseline vs Corrupted vs Repaired

Ba trạng thái được đánh giá bằng cùng test set đã lưu ở data/eval/test_set.json.
Dữ liệu repaired được dựng lại từ data/raw/crossref_response.json, không từ dữ liệu corrupted.

## So sánh hiệu năng RAG

| Chỉ số | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Số câu hỏi | 10 | 10 | 10 |
| Retrieval Hit Rate | 100.00% | 50.00% | 100.00% |
| Mean Token F1 | 0.8000 | 0.4207 | 0.8000 |
| Judge accuracy | 80.00% | 40.00% | 80.00% |
| Mean judge score /5 | 4.20 | 2.60 | 4.20 |
| Heuristic judge | 0 | 10 | 10 |

## Tín hiệu chất lượng dữ liệu

| Chỉ số | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Quality gate | Xem báo cáo Phase 1 | Không đạt | Đạt |
| Số bản ghi | — | 22 | 24 |
| Freshness SLA | Xem báo cáo Phase 1 | Đạt | Đạt |
| Bài quá 180 ngày | — | 3/22 | 0/24 |
| Tỷ lệ bài cũ | — | 13.64% | 0.00% |

## Phân tích từ số liệu

Dữ liệu lỗi làm Hit Rate giảm 50.00 điểm phần trăm và Token F1 giảm 0.3793 so với baseline.
Sau phục hồi, Hit Rate và Token F1 trở về đúng mức baseline.
Quality gate báo lỗi ở bản corrupted nhưng bước đánh giá RAG vẫn chạy để đo ảnh hưởng; đây là cách quan sát nguy cơ silent failure nếu bỏ qua gate.

Các câu hỏi benchmark chứa nguyên tiêu đề bài báo, nên Hit Rate có lợi thế tra cứu chính xác.
Số lượt heuristic judge khác nhau giữa ba trạng thái (0/10/10), nên judge accuracy không thể so sánh trực tiếp; ưu tiên Hit Rate và Token F1.

## Artifact

- [Nhật ký tiêm lỗi](../results/corruption_log.json)
- [Baseline metrics](../results/baseline_metrics.json)
- [Corrupted metrics](../results/corrupted_metrics.json)
- [Repaired metrics](../results/repaired_metrics.json)
- [Corrupted quality](../quality/corrupted_quality_report.json)
- [Repaired quality](../quality/repaired_quality_report.json)
