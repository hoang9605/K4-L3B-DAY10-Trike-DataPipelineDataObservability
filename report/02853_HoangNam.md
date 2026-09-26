# Báo cáo cá nhân — 02853_HoangNam

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Hoàng Nam |
| MSSV | 02853 |
| Khóa/Lớp | K4-L3B-DAY10 |
| Tên nhóm | Trike |
| Vai trò chính | Quality/freshness và orchestration, repair, reporting Phase 2 |
| Repository | [K4-L3B-DAY10-Trike-DataPipelineDataObservability](https://github.com/hoang9605/K4-L3B-DAY10-Trike-DataPipelineDataObservability) |
| Ngày ghi nhận | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| GX quality gate và freshness | src/observability/quality.py: run_data_quality_checks, evaluate_freshness_sla | DataFrame sạch/lỗi/repaired, Settings, stage | data/quality/*_quality_report.json; freshness reports | Hoàn thành |
| Repair từ raw snapshot | src/ingestion/repair.py: repair_from_raw_snapshot | data/raw/crossref_response.json; run_date | data/clean/papers_clean_repaired.csv và .json | Hoàn thành |
| Phase 2 orchestration | src/pipelines/corruption_flow.py: run_corruption_flow_pipeline | Clean dataset, baseline metrics, test set, snapshot | Corrupted/repaired index, answers, metrics | Hoàn thành |
| Báo cáo đối chiếu | src/observability/reporting.py: generate_corruption_report | Metrics, quality, freshness của ba trạng thái | data/reports/corruption_report.md | Hoàn thành |

Bộ tiêm sáu dạng lỗi do Hoàng sở hữu; Phase 2 của Nam nhận DataFrame lỗi và log từ bộ đó. Raw snapshot và evaluation set lần lượt do Đạt bàn giao.

### Việc hỗ trợ ngoài phạm vi chính

Hỗ trợ fix lỗi của Đạt và Hoàng

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Dựng GX 1.x Ephemeral Context, chạy bốn loại expectation | [quality.py](../src/observability/quality.py) | [Baseline quality](../data/quality/baseline_quality_report.json): 6/6 đạt; corrupted fail; repaired pass | Đọc ba quality reports |
| Theo dõi tỷ lệ bài cũ >180 ngày | [quality.py](../src/observability/quality.py) | [Freshness baseline](../data/quality/freshness_report.json): 0/24; [corrupted](../data/quality/corrupted_freshness_report.json): 3/22 | Đối chiếu stale_ratio và ngưỡng 25% |
| Phục hồi bằng raw snapshot, tái index và đánh giá | [repair.py](../src/ingestion/repair.py), [corruption_flow.py](../src/pipelines/corruption_flow.py) | [24 bản repaired](../data/clean/papers_clean_repaired.json); [repaired metrics](../data/results/repaired_metrics.json) | Chạy script/run_corruption_flow.py; so DOI và metrics |
| Xuất so sánh ba trạng thái | [reporting.py](../src/observability/reporting.py) | [corruption_report.md](../data/reports/corruption_report.md) | So bảng với ba metrics JSON |

Output quan trọng là quality gate đổi từ không đạt trên dữ liệu lỗi sang đạt sau repair, còn Hit Rate/Token F1 quay về mức baseline.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Dữ liệu sai có thể vẫn vào index và tạo câu trả lời, nên cần tín hiệu chất lượng độc lập với metrics RAG. Khi đã tiêm lỗi, repair phải lấy từ snapshot đáng tin cậy; việc sửa trên DataFrame lỗi có thể giữ lại thiếu sót mà không nhìn thấy.

### Cách triển khai

Hàm quality tạo GX Ephemeral Context, pandas asset và whole-dataframe batch; chạy row count 5–5000, not-null cho paper_id/title/text_for_embedding, unique DOI và summary tối thiểu 30 ký tự. Hàm bổ sung kiểm tra chuỗi trắng, cột thiếu, tuổi thiếu; freshness false nếu quá 25% bài cũ trên 180 ngày. Phase 2 lưu bản corrupted, chạy quality/freshness và đánh giá RAG dù gate fail để quan sát tác động. Repair đọc lại Crossref response gốc, parse và clean, kiểm tra tập DOI khớp baseline, yêu cầu quality pass, rồi build Chroma collection repaired và đánh giá bằng cùng test set.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | DataFrame có paper_id, title, summary, text_for_embedding, age_days; raw response JSON; baseline metrics; test_set.json |
| Output | Dict quality có success/gx_success/is_fresh và expectation results; repaired CSV/JSON; corrupted/repaired metrics; report Markdown |
| Module phụ thuộc | ingestion.crossref/cleaning của Đạt và Hoàng; corruption.py của Hoàng; retrieval.index; evaluation.metrics |
| Module sử dụng output | Phase 1 gate, Phase 2 report và quyết định có tiếp tục index repaired hay không |
| Điều kiện lỗi cần xử lý | Cột thiếu, null/rỗng, DOI trùng, summary ngắn, quá ngưỡng stale, snapshot thiếu, DOI raw khác baseline |

### Cách xác minh

Các điểm vào đã được chạy bằng Python 3.11 khả dụng; lệnh tái hiện trong môi trường cài đúng là:

    python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); print(run_data_quality_checks(df, s, 'test')['success'])"
    python script/run_corruption_flow.py

- **Kết quả mong đợi:** Quality baseline True; corrupted fail, repaired pass; bảng ba trạng thái và artifacts repaired xuất hiện.
- **Kết quả thực tế:** Lệnh quality in True; Phase 2 in Hit Rate 100% → 50% → 100% và Token F1 0,8000 → 0,4207 → 0,8000; ba bài kiểm tra Phase 2 trên dữ liệu mẫu đạt.
- **Artifact/log:** [quality reports](../data/quality/), [corruption report](../data/reports/corruption_report.md), [test Phase 2](../tests/test_phase2.py).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần phục hồi dữ liệu lỗi và chứng minh kết quả không chỉ do che các dòng hỏng.
- **Các phương án đã cân nhắc:** Chỉnh trực tiếp DataFrame corrupted; hoặc tái tạo từ raw Crossref response được giữ nguyên.
- **Phương án đã chọn:** Dựng repaired DataFrame từ raw snapshot, lưu artifact riêng và so tập DOI với baseline.
- **Lý do:** Tránh mang lỗi tiềm ẩn sang bản repaired, giữ corrupted để đối chiếu và làm bước sửa có thể chạy lại.
- **Bằng chứng:** [Repaired JSON](../data/clean/papers_clean_repaired.json) có 24 DOI khớp baseline; [repaired quality](../data/quality/repaired_quality_report.json) đạt; Hit Rate và Token F1 trở lại mức ban đầu.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Bài kiểm tra Phase 2 ban đầu báo “ModuleNotFoundError: No module named 'ingestion.repair'”.
- **Bước tái hiện:** Nạp repair_from_raw_snapshot trong test_phase2.py trước khi triển khai module.
- **Nguyên nhân gốc:** Repository chưa có ingestion/repair.py; corruption_flow.py và generate_corruption_report cũng còn NotImplementedError.
- **Cách xử lý:** Thêm repair.py, hoàn thiện orchestration và hàm xuất báo cáo; giữ nguyên chữ ký các hàm hiện có.
- **Cách xác minh sau khi sửa:** Ba bài kiểm tra Phase 2 đạt; script sinh [corruption_report.md](../data/reports/corruption_report.md), corrupted/repaired metrics và repaired clean JSON.
- **Điều học được:** Một pipeline chỉ chạy end-to-end khi đủ contract giữa repair, evaluation và reporting; cần kiểm tra artifact sau mỗi bước.

## 7. Hiểu biết về luồng end-to-end

1. Đạt lấy và giữ Crossref response; Hoàng clean thành DataFrame với text_for_embedding; MiniLM tạo vector và Chroma lưu index.
2. Bộ test của Đạt giữ DOI chuẩn trong ground_truth_doc_ids; evaluator so DOI truy hồi để tính Hit Rate và so câu trả lời để tính Token F1.
3. GX xem số dòng, cột bắt buộc, tính duy nhất và độ dài; freshness dùng age_days và SLA tỷ lệ stale, nên một bản có 3 bài cũ vẫn có thể đạt.
4. Cùng test_set.json cho ba trạng thái giữ cố định câu hỏi và DOI mục tiêu, tránh gán nhầm biến động metric cho việc đổi bộ đề.
5. Repair được công nhận khi dữ liệu lấy lại từ raw snapshot có DOI đúng, quality gate đạt và metrics trên cùng bộ đề phục hồi; report ghi cả ba bằng chứng.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét theo phần việc |
| --- | ---: | ---: | ---: | --- |
| retrieval_hit_rate | 100% | 50% | 100% | 5 DOI bị bỏ trùng 5 retrieval miss |
| mean_token_f1 | 0,8000 | 0,4207 | 0,8000 | Phục hồi theo cùng test set |
| judge_accuracy | 80% | 40% | 80% | Không so sánh trực tiếp: baseline dùng LLM, sau đó heuristic |
| mean_judge_score | 4,20/5 | 2,60/5 | 4,20/5 | Heuristic judge count 0/10/10 |
| Quality checks | Đạt, 24 dòng | Không đạt, 22 dòng | Đạt, 24 dòng | Unique DOI và summary length fail khi corrupted |
| Freshness status | Đạt, 0/24 cũ | Đạt, 3/22 cũ | Đạt, 0/24 cũ | 13,64% < 25% nên corrupted vẫn fresh |

Nguồn: [comparison report](../data/reports/corruption_report.md), [corrupted quality](../data/quality/corrupted_quality_report.json), [repaired quality](../data/quality/repaired_quality_report.json).

### Kết luận từ số liệu

1. Hoàng bỏ 5 bài mới nhất và tiêm lỗi khác → GX phát hiện DOI trùng/summary quá ngắn, trong khi freshness còn đạt → 5/10 DOI mục tiêu trượt retrieval và Token F1 giảm 0,3793. Drop latest là lỗi có bằng chứng ảnh hưởng retrieval rõ nhất khi đối chiếu log với answers.
2. Nam tái tạo 24 bản ghi từ raw response → GX pass, stale 0/24 → Hit Rate từ 50% lên 100%, Token F1 từ 0,4207 lên 0,8000.

Điểm khác kỳ vọng: lùi ngày 365 ngày cho 3 dòng chưa làm freshness fail, do SLA dựa trên tỷ lệ 3/22. Ngoài ra judge chuyển sang heuristic trong lần Phase 2, nên không dùng judge accuracy làm bằng chứng duy nhất cho phục hồi.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Lưu raw snapshot giúp repair có nguồn độc lập với dữ liệu đã hỏng.
2. Quality gate và freshness là hai tín hiệu khác nhau; một tín hiệu đạt không phủ định cảnh báo của tín hiệu kia.
3. Retrieval/Token F1 có thể suy giảm dù pipeline vẫn tạo câu trả lời, nên phải đọc quality report cùng metrics.

### Nếu có thêm thời gian

Thêm kiểm tra tỷ lệ categories có giá trị và log chi tiết nguyên nhân judge fallback; chạy lại ba trạng thái với cùng chế độ judge, sau đó đối chiếu các metrics và số cảnh báo.

## 10. Cam kết của thành viên

Phần này để Hoàng Nam tự kiểm tra và xác nhận; các ô chưa được đánh dấu thay.

- [x] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi thành công cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa .env, API key, token hoặc secret.
- [x] Báo cáo này không sao chép nguyên văn báo cáo nhóm hoặc thành viên khác.

**Họ và tên:** Hoàng Văn Nam

**Ngày xác nhận:** 2026-9-26
