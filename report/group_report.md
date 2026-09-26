# Báo cáo nhóm Trike — Data Pipeline & Data Observability

- **Lớp/bài lab:** K4-L3B-DAY10
- **Ngày ghi nhận:** 2026-09-26
- **Repository:** [K4-L3B-DAY10-Trike-DataPipelineDataObservability](https://github.com/hoang9605/K4-L3B-DAY10-Trike-DataPipelineDataObservability)
- **Phạm vi báo cáo:** Phase 1, bộ tiêm lỗi và kết quả so sánh ba trạng thái Phase 2.

## 1. Tóm tắt

Nhóm xây dựng tuyến dữ liệu bài báo từ Crossref, giữ bản JSON gốc và bản ghi đã bóc tách, làm sạch dữ liệu, lập Chroma index, sinh bộ 10 câu hỏi chuẩn, đo baseline RAG và kiểm định chất lượng trước khi index. Tại thời điểm ghi nhận có 24 raw records và 24 bài sạch. Baseline đạt Retrieval Hit Rate 100% và mean Token F1 0,80. Great Expectations đạt 6/6 expectation, SLA freshness đạt với 0/24 bài cũ quá 180 ngày. Snapshot hiện không có `subject`, nên không cung cấp ground truth lĩnh vực thực tế; hai câu hỏi categories có Token F1 bằng 0. Các chỉ số này phản ánh đúng bộ dữ liệu và câu hỏi đang dùng, chưa chứng minh hiệu năng trên truy vấn mở.

Trong Phase 2, pipeline dùng cùng test set để đánh giá dữ liệu lỗi rồi phục hồi từ snapshot Crossref gốc. Hit Rate đo được là 100% → 50% → 100%, Token F1 là 0,8000 → 0,4207 → 0,8000. Quality gate phát hiện dữ liệu lỗi và đạt lại sau repair. Judge của hai trạng thái sau dùng heuristic trong lần chạy này, khác baseline dùng LLM, nên không so sánh trực tiếp các chỉ số judge.

## 2. Thành viên và đóng góp

| Thành viên | Phần việc đã xác nhận | Báo cáo |
| --- | --- | --- |
| Hải Hoàng — 02489 | Làm sạch `PaperRecord`; chạy Phase 1 pipeline; triển khai Data Corruption Suite | [Cá nhân](02489_HaiHoang.md) |
| Tuấn Đạt — 02623 | Ingest Crossref, raw preservation, offline fallback; benchmark test set | [Cá nhân](02623_TuanDat.md) |
| Hoàng Nam — 02853 | Great Expectations quality gate, freshness SLA; phục hồi từ raw snapshot và tích hợp đánh giá Phase 2 | [Cá nhân](02853_HoangNam.md) |

Thông tin phân công ngắn gọn cũng có trong [docs/TEAM.md](../docs/TEAM.md).

## 3. Luồng xử lý và khả năng tái lập

`Crossref API / snapshot → PaperRecord → DataFrame sạch → Quality gate → Chroma index → Test set → RAG evaluation → Phase 1 report`

- `src/ingestion/crossref.py` lưu phản hồi API vào [crossref_response.json](../data/raw/crossref_response.json) và bản ghi đã bóc tách vào [crossref_records.json](../data/raw/crossref_records.json). Nếu nguồn trực tuyến lỗi, pipeline có thể dùng snapshot gốc sẵn có; lần chạy không yêu cầu refresh dùng bản ghi raw đã lưu.
- `src/ingestion/cleaning.py` chuẩn hóa các trường, tính tuổi bài báo theo ngày chạy, ghép `text_for_embedding`, loại DOI trùng. Đầu ra là [papers_clean.csv](../data/clean/papers_clean.csv) và [papers_clean.json](../data/clean/papers_clean.json).
- `src/observability/quality.py` đánh giá GX và SLA trước khi tạo index. Pipeline dừng nếu quality gate không đạt.
- Pipeline dùng Chroma collection `papers-baseline`, embedding model `sentence-transformers/all-MiniLM-L6-v2`, tạo [test_set.json](../data/eval/test_set.json), ghi [baseline_metrics.json](../data/results/baseline_metrics.json), [baseline_answers.json](../data/results/baseline_answers.json) và [phase1_report.md](../data/reports/phase1_report.md).

Điểm bắt đầu chạy là `python script/run_phase1.py` trong môi trường đã cài dependencies và cấu hình của dự án. Dữ liệu gốc được giữ lại để tái chạy bước chuẩn hóa mà không phụ thuộc vào API trong lần chạy đó.

## 4. Số liệu Phase 1

| Chỉ số | Kết quả từ artifact |
| --- | ---: |
| Raw records / clean records | 24 / 24 |
| Bài có `categories` | 0 / 24 |
| Câu hỏi benchmark | 10 |
| Phân bố summary / authors / date / categories | 3 / 3 / 2 / 2 |
| Retrieval Hit Rate | 1,00 |
| Mean Token F1 | 0,80 |
| Judge accuracy / mean judge score | 0,80 / 4,2 trên 5 |
| GX expectations đạt | 6 / 6 |
| Bài cũ hơn 180 ngày | 0 / 24 |
| Freshness SLA | Đạt; giới hạn 25% |

Nguồn đối chiếu: [báo cáo baseline](../data/reports/phase1_report.md), [metrics JSON](../data/results/baseline_metrics.json), [quality JSON](../data/quality/baseline_quality_report.json) và [freshness JSON](../data/quality/freshness_report.json). Trong 10 câu hỏi, summary/authors/date có Token F1 1,00; categories có Token F1 0,00. RAGAS được ghi là chưa chạy trong metrics hiện tại.

## 5. Kiểm định chất lượng và giới hạn

Quality gate dùng Great Expectations 1.x Ephemeral Context. Bốn loại expectation bắt buộc gồm số dòng 5–5000, ba cột quan trọng không null, DOI duy nhất và summary dài tối thiểu 30 ký tự. Tổng cộng có sáu phép kiểm vì điều kiện không null áp dụng cho ba cột. Kiểm tra bổ sung chặn chuỗi rỗng, cột thiếu và tuổi dữ liệu không có giá trị. [Quality report](../data/quality/baseline_quality_report.json) ghi `success=true`.

Benchmark dùng câu hỏi chứa nguyên tiêu đề bài báo và `ground_truth_doc_ids` là DOI; điều này giúp kiểm tra truy hồi theo tiêu đề nhưng có thể làm Hit Rate cao hơn khi hỏi bằng cách diễn đạt khác. Snapshot Crossref không có `subject`, vì vậy câu hỏi categories hiện chỉ kiểm tra cách xử lý metadata thiếu. Kết quả baseline cần được diễn giải trong hai giới hạn đó.

## 6. Tiêm lỗi dữ liệu

Hoàng triển khai `src/ingestion/corruption.py` với sáu kịch bản lỗi và log theo bản ghi. [Corruption log](../data/results/corruption_log.json) ghi 24 dòng đầu vào, 22 dòng đầu ra và 20 sự kiện: bỏ 5 bài mới nhất; xóa summary, chèn noise, cắt tiêu đề, lùi ngày và nhân đôi dòng, mỗi dạng còn lại có 3 sự kiện. Hàm được kiểm tra trong [test Phase 2](../tests/test_phase2.py).

Nam phụ trách hàm repair từ raw snapshot, pipeline đánh giá trên cùng test set và báo cáo so sánh ba trạng thái. [Báo cáo Phase 2](../data/reports/corruption_report.md) ghi Hit Rate 100% / 50% / 100% và Token F1 0,8000 / 0,4207 / 0,8000 theo Baseline / Corrupted / Repaired. [Quality report bản lỗi](../data/quality/corrupted_quality_report.json) không đạt, [bản repaired](../data/quality/repaired_quality_report.json) đạt. Freshness bản lỗi vẫn đạt vì 3/22 bài quá 180 ngày chiếm 13,64%, dưới ngưỡng 25%. Metrics corrupted/repaired dùng heuristic judge 10/10 câu, trong khi baseline 0/10; chỉ số judge vì thế không so sánh trực tiếp.

## 7. Trạng thái bàn giao

Các artifact Phase 1, [corrupted metrics](../data/results/corrupted_metrics.json), [repaired metrics](../data/results/repaired_metrics.json), corruption log và báo cáo so sánh ba trạng thái đã có trong repository. Hoàng phụ trách bộ tiêm lỗi; Nam phụ trách orchestration, repair và báo cáo Phase 2. Ba thành viên cần tự rà soát và xác nhận nội dung báo cáo cá nhân trước khi nộp.
