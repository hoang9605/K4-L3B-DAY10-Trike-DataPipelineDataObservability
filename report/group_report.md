# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4-L3B-DAY10 |
| Tên nhóm | Trike |
| Repository | [K4-L3B-DAY10-Trike-DataPipelineDataObservability](https://github.com/hoang9605/K4-L3B-DAY10-Trike-DataPipelineDataObservability) |
| Ngày hoàn thành | 2026-09-26 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Hải Hoàng | 02489 | Cleaning, baseline orchestration, corruption suite | [cleaning.py](../src/ingestion/cleaning.py), [phase1.py](../src/pipelines/phase1.py), [corruption.py](../src/ingestion/corruption.py), [báo cáo cá nhân](02489_HaiHoang.md) |
| 2 | Tuấn Đạt | 02623 | Crossref ingestion, evaluation set | [crossref.py](../src/ingestion/crossref.py), [testset.py](../src/evaluation/testset.py), [báo cáo cá nhân](02623_TuanDat.md) |
| 3 | Hoàng Nam | 02853 | GX/freshness, repair, Phase 2 orchestration/reporting | [quality.py](../src/observability/quality.py), [repair.py](../src/ingestion/repair.py), [corruption_flow.py](../src/pipelines/corruption_flow.py), [reporting.py](../src/observability/reporting.py), [báo cáo cá nhân](02853_HoangNam.md) |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành tuyến thu thập metadata Crossref, lưu phản hồi gốc và 24 PaperRecord, làm sạch thành 24 bài có DOI duy nhất, tạo Chroma index và bộ 10 câu hỏi. Baseline xuất CSV/JSON sạch, embedding manifest, metrics, quality/freshness report và báo cáo Phase 1. Great Expectations đạt 6/6 phép kiểm; 0/24 bài quá 180 ngày. Baseline đạt Hit Rate 100% và Token F1 0,8000.

Nhóm tiếp tục tiêm sáu loại lỗi, ghi 20 sự kiện và đánh giá lại bằng chính test set đó. Tác động rõ nhất là bỏ 5 bài mới nhất: cả 5 DOI bị bỏ đều xuất hiện trong 5 lượt retrieval miss. Bản corrupted còn 22 dòng, quality gate không đạt, Hit Rate giảm còn 50% và Token F1 còn 0,4207. Nam dựng lại dữ liệu từ raw response được giữ nguyên; bản repaired có 24 DOI, quality gate đạt, Hit Rate và Token F1 trở về mức baseline.

Giới hạn quan trọng là snapshot không có subject cho 24/24 bài, nên hai câu hỏi categories vẫn có Token F1 bằng 0. Benchmark chứa nguyên tiêu đề bài báo, làm Hit Rate dễ hơn truy vấn tự do. Baseline dùng LLM judge, còn hai lượt Phase 2 dùng heuristic judge, vì vậy không so sánh trực tiếp các chỉ số judge.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

    Crossref API / offline snapshot
        -> raw response + raw PaperRecord
        -> cleaning -> clean CSV/JSON -> GX/freshness gate
        -> MiniLM embedding -> ChromaDB baseline index
        -> test set -> baseline evaluation
        -> sáu corruption scenarios -> corrupted index/evaluation/quality
        -> repair từ raw response -> repaired index/evaluation/quality
        -> comparison report

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref / snapshot | Fetch, retry 429/503, parse, giữ raw | [raw response](../data/raw/crossref_response.json), [raw records](../data/raw/crossref_records.json) | Đạt |
| Cleaning | PaperRecord | Text/ngày ISO, age_days, DOI unique | [clean JSON](../data/clean/papers_clean.json), [CSV](../data/clean/papers_clean.csv) | Hoàng |
| Embedding/index | text_for_embedding | MiniLM tại máy, Chroma cosine collection | [embedding manifest](../data/embeddings/papers_embeddings.json), data/chroma/ | Hoàng ở baseline; Nam ở Phase 2 |
| Evaluation | Clean dataset và test set | Ground truth DOI, Hit Rate, Token F1, judge | [test set](../data/eval/test_set.json), [metrics](../data/results/baseline_metrics.json) | Đạt tạo test set; Hoàng/Nam tích hợp từng pha |
| Observability | Clean/corrupted/repaired DataFrame | GX 1.x và freshness SLA | [quality artifacts](../data/quality/) | Nam |
| Corruption/repair | Clean DataFrame; raw response | Sáu lỗi; phục hồi từ bản gốc | [corruption log](../data/results/corruption_log.json), [repaired JSON](../data/clean/papers_clean_repaired.json) | Hoàng tiêm lỗi; Nam repair |
| Orchestration | Settings và artifact từ các khối | Thứ tự chạy, tái index, so sánh | [Phase 1](../data/reports/phase1_report.md), [Phase 2](../data/reports/corruption_report.md) | Hoàng Phase 1; Nam Phase 2 |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị ghi nhận |
| --- | --- |
| LLM_PROVIDER | gemini theo load_settings hiện tại |
| LLM_MODEL | gemini-3.6-flash theo load_settings hiện tại; metrics không lưu tên model của từng lượt chạy |
| Embedding model/runtime | sentence-transformers/all-MiniLM-L6-v2; SentenceTransformer tại máy |
| Số lượng Crossref records | 24 |
| Retrieval top_k | 4 |
| Freshness threshold | 180 ngày; tối đa 25% bài cũ |
| Random seed | Không dùng; chọn corruption theo thứ tự cố định |

Không đưa API key hoặc nội dung .env vào báo cáo. Phụ thuộc Python được khai báo trong [pyproject.toml](../pyproject.toml); lượt ghi nhận không có nhật ký lệnh cài đặt để xác nhận một phương thức cài cụ thể. Trong môi trường Python 3.11 đã cài dependencies, có thể dùng lệnh cài tái lập:

    python -m pip install -e .

### Lệnh chạy

    python script/run_phase1.py
    python script/run_corruption_flow.py

Các điểm vào đã được chạy bằng bản Python 3.11 khả dụng. Launcher python mặc định ở máy ghi nhận trỏ đến Python 3.12 không còn tồn tại, nên cần chọn đúng interpreter trước khi dùng hai lệnh trên. Phase 1 dùng raw records snapshot; không khẳng định đã gọi Crossref API trong lần baseline.

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm ghi nhận gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công | 2026-09-26 10:56 theo mtime metrics trên máy | [baseline metrics](../data/results/baseline_metrics.json), [Phase 1 report](../data/reports/phase1_report.md) |
| Corruption flow | Thành công | 2026-09-26 11:47 theo mtime metrics trên máy | [corrupted metrics](../data/results/corrupted_metrics.json), [repaired metrics](../data/results/repaired_metrics.json), [comparison report](../data/reports/corruption_report.md) |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API /works và snapshot offline |
| Query/filter cấu hình | query: agentic retrieval augmented generation large language model; filter hiện tại: from-pub-date:2026-03-30,has-abstract:true |
| Thời điểm dữ liệu | Raw response có mtime 2026-09-26 09:51 trên máy; không đủ bằng chứng xác định thời điểm API thực trả |
| Số record nhận và bóc tách | 24 items / 24 PaperRecord trong artifact |
| Retry/backoff | Tối đa ba lượt, đợi 1–2 giây với 429/503; dùng snapshot có sẵn nếu nguồn không khả dụng |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| paper_id | string DOI | Có | Danh tính bài và ground-truth doc ID | Bỏ record thiếu; lower-case và deduplicate khi clean |
| title | string | Có | Tiêu đề và tín hiệu retrieval | Bỏ record thiếu; giải mã markup/khoảng trắng |
| summary | string | Có | Abstract/nguồn trả lời | Bỏ record thiếu; loại HTML/XML; GX yêu cầu ≥30 ký tự |
| authors | list[string] | Không | Tác giả Crossref | Dùng danh sách rỗng nếu thiếu; tạo authors_joined |
| categories | list[string] | Không | subject Crossref | Dùng danh sách rỗng nếu thiếu; tạo categories_joined |
| published | ISO date string | Có | Ngày xuất bản | Chọn các trường ngày Crossref theo thứ tự; bỏ record không parse được |
| age_days | integer | Có sau cleaning | Tuổi bài theo run_date | Tính từ published; thiếu làm freshness fail |
| text_for_embedding | string | Có sau cleaning | Nội dung nạp vector | Ghép Title, Authors, Published, Categories, Summary |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
| --- | --- | ---: | --- |
| Bóc markup abstract khi ingest/clean | Validity | 24/24 abstracts gốc chứa thẻ; clean không còn thẻ | So [response](../data/raw/crossref_response.json) với [clean JSON](../data/clean/papers_clean.json) |
| Bỏ record thiếu DOI/title/summary/ngày | Completeness | 0 bị bỏ trong snapshot này | 24 raw → 24 clean |
| Khử DOI trùng | Uniqueness | 0 trùng trong snapshot sạch | 24 DOI duy nhất; [baseline quality](../data/quality/baseline_quality_report.json) đạt |
| Chuẩn hóa ngày và tính age_days | Validity/Freshness | 24 dòng được gán tuổi | [clean JSON](../data/clean/papers_clean.json), [freshness](../data/quality/freshness_report.json) |

Document ID gốc là DOI paper_id; Chroma tạo record_id từ DOI và vị trí dòng. text_for_embedding gồm năm dòng có nhãn Title, Authors, Published, Categories, Summary. age_days bằng ngày chạy trừ published theo ngày lịch.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 10 |
| question_type | summary 3, authors 3, date 2, categories 2 |
| Ground-truth document ID | DOI paper_id trong ground_truth_doc_ids |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Vector store/collection | Chroma cosine; papers-baseline, papers-corrupted, papers-repaired |
| Retrieval top_k | 4 |
| LLM provider/model | Cấu hình hiện tại gemini / gemini-3.6-flash; judge Phase 2 fallback heuristic 10/10 câu mỗi trạng thái |
| Test set dùng chung | [data/eval/test_set.json](../data/eval/test_set.json) |

Cùng test set giữ cố định câu hỏi, ground truth và DOI mục tiêu. Nếu tạo lại bộ đề sau corruption, sự khác biệt Hit Rate/F1 có thể do đổi bài đánh giá thay vì đổi corpus.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | [data/raw/](../data/raw/) | Có | 24 records; snapshot gốc giữ riêng |
| Cleaned dataset | [data/clean/](../data/clean/) | Có | 24 clean records |
| Embedding manifest/index | [manifest](../data/embeddings/papers_embeddings.json), data/chroma/ | Có | papers-baseline, SentenceTransformer |
| Evaluation set | [test_set.json](../data/eval/test_set.json) | Có | 10 câu |
| Baseline metrics | [baseline_metrics.json](../data/results/baseline_metrics.json) | Có | 10 samples |
| Quality/freshness | [data/quality/](../data/quality/) | Có | GX 6/6; stale 0/24 |
| Baseline report | [phase1_report.md](../data/reports/phase1_report.md) | Có | Bảng số liệu chi tiết |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| retrieval_hit_rate | 100% | 10/10 câu truy hồi có DOI mục tiêu; câu hỏi chứa nguyên tiêu đề |
| mean_token_f1 | 0,8000 | Ba loại summary/authors/date đạt 1; categories đạt 0 |
| judge_accuracy | 80% | Baseline judge không dùng heuristic; không đối chiếu trực tiếp với Phase 2 |
| mean_judge_score | 4,20/5 | Điểm judge trung bình của baseline |
| Ragas | Không chạy | Metrics ghi RUN_RAGAS=1 mới kích hoạt |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| Table row count | Volume | 5–5000 | Pass, 24 | [quality JSON](../data/quality/baseline_quality_report.json) |
| Not null paper_id | Completeness | 0 null | Pass | Cùng artifact |
| Not null title | Completeness | 0 null | Pass | Cùng artifact |
| Not null text_for_embedding | Completeness | 0 null | Pass | Cùng artifact |
| Unique paper_id | Uniqueness | 0 trùng | Pass | Cùng artifact |
| Summary length | Validity | ≥30 ký tự | Pass | Cùng artifact |

Hàm quality còn chặn chuỗi chỉ chứa khoảng trắng, thiếu cột và summary quá ngắn bên ngoài phép not-null.

### Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | DataFrame sạch; [freshness_report.json](../data/quality/freshness_report.json) |
| Timestamp published mới nhất | 2026-09-15 |
| Timestamp published cũ nhất | 2026-04-01 |
| Ngưỡng freshness | age_days >180 là bài cũ; tỷ lệ cho phép tối đa 25% |
| Trạng thái baseline | Fresh, 0/24 bài cũ |
| Lý do | Stale ratio 0%, không thiếu age_days |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| --- | --- | ---: | --- | --- | --- |
| Drop latest | Bỏ 20% bài mới nhất | 5 | Có thể không bị GX phát hiện nếu row count còn hợp lệ | Trùng đúng 5/10 retrieval miss; Hit Rate tổng còn 50% | Dựng lại từ raw |
| Blank summary | Xóa tóm tắt | 3 | Summary length fail | GX summary length fail; ảnh hưởng F1 riêng chưa tách | Dựng lại từ raw |
| Inject noise | Chèn ký tự rác | 3 | GX hiện chưa có expectation ngữ nghĩa | Tác động metric riêng chưa tách | Dựng lại từ raw |
| Truncate title | Cắt xuống dưới 8 ký tự | 3 | GX hiện chưa kiểm tra title length | Tác động metric riêng chưa tách | Dựng lại từ raw |
| Stale date | Lùi published 365 ngày | 3 | Tăng số bài cũ | 3/22 cũ nhưng SLA vẫn đạt (13,64%) | Dựng lại từ raw |
| Duplicate rows | Nhân đôi dòng | 3 | Unique DOI fail | GX unique paper_id fail | Dựng lại từ raw |

- **Corruption log:** [data/results/corruption_log.json](../data/results/corruption_log.json) hiện có; 20 sự kiện đủ sáu loại, mỗi sự kiện có DOI, source_index và giá trị trước/sau.
- **Repair:** [repair.py](../src/ingestion/repair.py) đọc lại response Crossref gốc, parse và clean bằng run_date của baseline. Pipeline kiểm tra tập DOI repaired khớp baseline và GX đạt trước khi index/đánh giá, tránh chỉ che lỗi trên DataFrame corrupted. Bản lỗi và bản repaired được lưu riêng để đối chiếu.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| retrieval_hit_rate | 100% | 50% | 100% | -50 điểm % | +50 điểm % | 5 DOI mục tiêu bị bỏ, rồi được phục hồi |
| mean_token_f1 | 0,8000 | 0,4207 | 0,8000 | -0,3793 | +0,3793 | Về đúng mức baseline |
| judge_accuracy | 80% | 40% | 80% | -40 điểm % | +40 điểm % | Chế độ judge khác, không kết luận nhân quả từ chỉ số này |
| mean_judge_score | 4,20/5 | 2,60/5 | 4,20/5 | -1,60 | +1,60 | Baseline LLM judge; Phase 2 heuristic |
| Quality checks | Đạt | Không đạt | Đạt | Fail unique/summary | Pass 6/6 | Gate phát hiện lỗi và trở lại |
| Freshness status | Đạt 0/24 | Đạt 3/22 | Đạt 0/24 | +13,64 điểm % stale | -13,64 điểm % stale | Chưa vượt SLA 25% |

1. Bỏ 5 bài mới nhất cùng các lỗi khác → GX fail unique DOI và summary length; riêng 5 DOI bị bỏ trùng 5 retrieval miss → Hit Rate giảm 100% xuống 50% và Token F1 còn 0,4207.
2. Dựng lại từ raw response → 24 DOI khớp baseline, GX pass và stale về 0/24 → Hit Rate 100%, Token F1 0,8000.

Không gán suy giảm riêng cho noise/truncate vì sáu lỗi được tiêm đồng thời. Judge fallback count là 0/10/10 theo ba trạng thái, nên chỉ số judge không so sánh trực tiếp. [Comparison report](../data/reports/corruption_report.md) ghi số liệu gốc.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Trước khi triển khai Phase 2, import repair_from_raw_snapshot báo “ModuleNotFoundError: No module named 'ingestion.repair'”; pipeline và reporting còn NotImplementedError.
- **Nguyên nhân:** Starter chỉ có stub orchestration/report, chưa có module repair để nối với snapshot gốc.
- **Cách xử lý:** Nam thêm repair.py, hoàn thiện corruption_flow.py và generate_corruption_report; dùng cùng test set và giữ artifact từng trạng thái.
- **Cách xác minh:** Ba bài kiểm tra trong [test_phase2.py](../tests/test_phase2.py) đạt; script Phase 2 exit code 0 và tạo [corruption_report.md](../data/reports/corruption_report.md).

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| 0/24 bài có subject | Categories Token F1 = 0 ở cả baseline và repaired | Dùng nguồn Crossref có subject, sinh lại test set và đo riêng loại categories |
| Câu hỏi chứa nguyên tiêu đề | Exact-title lookup có thể làm Hit Rate cao hơn truy vấn tự do | Thêm bộ paraphrase không chứa title; đo Hit Rate/F1 trên bộ đó |
| LLM judge fallback khác nhau giữa các pha | Judge accuracy/score không so sánh trực tiếp | Chạy lại ba trạng thái cùng một chế độ judge và lưu nguyên nhân fallback |
| Sáu lỗi được tiêm đồng thời | Không tách được delta F1 cho từng lỗi | Chạy từng scenario trên cùng test set, báo cáo delta riêng |
| Thời điểm API live không được lưu trong artifact | Không chứng minh chính xác lần tải response | Ghi thời gian và source_mode vào metadata ingest ở lần thu thập sau, giữ nguyên response gốc |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository đã đối chiếu với [docs/TEAM.md](../docs/TEAM.md).
- [x] Phân công khớp các module và artifact đã được nhóm xác nhận.
- [x] Các thành viên tự chạy lại lệnh trên môi trường nộp cuối cùng.
- [x] Baseline, corrupted và repaired dùng cùng [evaluation set](../data/eval/test_set.json).
- [x] Bảng metrics đối chiếu các file trong data/results/.
- [x] Kết luận quality/freshness đối chiếu các file trong data/quality/.
- [x] Các đường dẫn báo cáo và artifact trong repository đã được đối chiếu.
- [x] Mỗi thành viên tự xác nhận mục cam kết trong báo cáo cá nhân.
- [x] Nhóm tự kiểm tra lần cuối rằng source, report, log và ảnh nộp không chứa .env, API key, token hoặc secret.
