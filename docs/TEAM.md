# Nhóm Trike — K4-L3B-DAY10

Repository: [K4-L3B-DAY10-Trike-DataPipelineDataObservability](https://github.com/hoang9605/K4-L3B-DAY10-Trike-DataPipelineDataObservability)

## Thành viên và phân công đã xác nhận

| MSSV | Thành viên | Phần việc đã xác nhận | Báo cáo cá nhân |
| --- | --- | --- | --- |
| 02489 | Hải Hoàng | Làm sạch dữ liệu; tích hợp baseline pipeline; tiêm sáu dạng lỗi dữ liệu | [02489_HaiHoang.md](../report/02489_HaiHoang.md) |
| 02623 | Tuấn Đạt | Thu thập và lưu raw data Crossref; tạo benchmark test set | [02623_TuanDat.md](../report/02623_TuanDat.md) |
| 02853 | Hoàng Nam | Great Expectations quality gate; freshness; Phase 2 repair, đánh giá và báo cáo ba trạng thái | [02853_HoangNam.md](../report/02853_HoangNam.md) |

## Phạm vi đã có bằng chứng

- **Đạt:** `src/ingestion/crossref.py` chuẩn hóa payload Crossref thành `PaperRecord`, lưu nguyên bytes JSON API khi lấy trực tuyến, ghi danh sách records, và dùng snapshot khi API không khả dụng; `src/evaluation/testset.py` sinh 10 câu hỏi thuộc bốn loại.
- **Hoàng:** `src/ingestion/cleaning.py` chuẩn hóa văn bản/ngày tháng, tính `age_days`, tạo `text_for_embedding`, khử DOI trùng; `src/pipelines/phase1.py` nối các bước baseline; `src/ingestion/corruption.py` tiêm sáu dạng lỗi và ghi log theo dòng.
- **Nam:** `src/observability/quality.py` chạy Great Expectations 1.x và freshness SLA; `src/ingestion/repair.py` phục hồi từ snapshot Crossref; `src/pipelines/corruption_flow.py` đánh giá corrupted/repaired trên cùng test set; `src/observability/reporting.py` xuất bảng so sánh ba trạng thái.

Kết quả và giới hạn được ghi trong [báo cáo nhóm](../report/group_report.md). Phase 1 có 24 bản ghi sạch, 10 câu hỏi benchmark, Hit Rate 100%, Token F1 0,8 và quality gate đạt. Hai câu hỏi về lĩnh vực không có metadata `subject` trong snapshot hiện dùng. [Corruption log](../data/results/corruption_log.json) ghi 20 sự kiện; [báo cáo Phase 2](../data/reports/corruption_report.md) ghi Hit Rate 100% → 50% → 100% cho baseline, corrupted và repaired.
