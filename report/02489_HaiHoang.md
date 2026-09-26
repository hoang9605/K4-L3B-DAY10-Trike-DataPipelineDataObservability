# Báo cáo cá nhân — 02489_HaiHoang

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Hải Hoàng |
| MSSV | 02489 |
| Khóa/Lớp | K4-L3B-DAY10 |
| Tên nhóm | Trike |
| Vai trò chính | Cleaning, baseline orchestration và Data Corruption Suite |
| Repository | [K4-L3B-DAY10-Trike-DataPipelineDataObservability](https://github.com/hoang9605/K4-L3B-DAY10-Trike-DataPipelineDataObservability) |
| Ngày ghi nhận | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Cleaning và data modeling | src/ingestion/cleaning.py: build_clean_dataframe | PaperRecord từ Đạt; run_date | data/clean/papers_clean.csv và .json | Hoàn thành |
| Baseline orchestration | src/pipelines/phase1.py: run_phase1_pipeline | Raw records, settings | Chroma baseline, metrics, quality và phase1_report.md | Hoàn thành |
| Data Corruption Suite | src/ingestion/corruption.py: corrupt_clean_dataframe | DataFrame sạch | DataFrame lỗi; data/results/corruption_log.json | Hoàn thành |

Clean schema được Đạt dùng để xây benchmark, Nam dùng để chạy quality gate và phục hồi/đánh giá Phase 2. Hoàng sở hữu phần tạo dữ liệu lỗi; phần repair và báo cáo so sánh Phase 2 do Nam phụ trách.

### Việc hỗ trợ ngoài phạm vi chính

Việc ghép output của Đạt và Nam vào Phase 1 nằm trong deliverable orchestration đã phân công; Giúp đánh giá eval2; Hỗ trợ làm báo cáo

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Chuẩn hóa text/ngày, tính tuổi và bỏ DOI trùng | [cleaning.py](../src/ingestion/cleaning.py) | [24 dòng sạch](../data/clean/papers_clean.csv), 24 DOI duy nhất | So raw/clean và cột age_days, text_for_embedding |
| Nối ingest → quality → Chroma → test set → evaluation → report | [phase1.py](../src/pipelines/phase1.py) | [Baseline report](../data/reports/phase1_report.md), [metrics](../data/results/baseline_metrics.json) | Chạy script/run_phase1.py; đọc artifact |
| Tiêm sáu lỗi có thể lặp lại và log trước/sau | [corruption.py](../src/ingestion/corruption.py) | [Corruption log](../data/results/corruption_log.json): 20 sự kiện, 24 → 22 dòng | Đọc counts và đối chiếu [dữ liệu lỗi](../data/clean/papers_clean_corrupted.json) |

Output cốt lõi của cleaning là text_for_embedding gồm Title, Authors, Published, Categories và Summary. Output cốt lõi của corruption là log theo DOI, source_index và ảnh chụp dòng trước/sau biến đổi.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Metadata Crossref chứa markup, ngày tháng và khoảng trắng không đồng nhất. Chroma cần văn bản ổn định theo DOI; các bước sau cần age_days. Để kiểm tra chất lượng pipeline, bộ dữ liệu lỗi phải có đủ sáu tình huống và giữ nhật ký tái lập được.

### Cách triển khai

Cleaning giải mã HTML, bỏ thẻ còn sót, chuẩn hóa trường văn bản, đổi published sang ISO, tính age_days từ run_date, ghép văn bản embedding và giữ bản đầu khi DOI trùng. Baseline pipeline lưu CSV/JSON sạch, chạy quality/freshness gate trước khi index và đánh giá. Corruption chọn 20% bài mới nhất để bỏ; trên phần còn lại lần lượt xóa summary, chèn noise, rút title dưới 8 ký tự, lùi published 365 ngày và nhân đôi. Hàm cập nhật summary_chars, age_days, text_for_embedding sau biến đổi.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Danh sách PaperRecord và run_date; Phase 1 nhận Settings; corruption nhận DataFrame sạch |
| Output | DataFrame có paper_id, published, age_days, text_for_embedding; clean CSV/JSON; baseline artifacts; corruption log |
| Module phụ thuộc | ingestion.crossref của Đạt; observability.quality của Nam; retrieval.index; evaluation.testset/metrics |
| Module sử dụng output | Chroma index, evaluation.metrics, pipeline Phase 2 của Nam |
| Điều kiện lỗi cần xử lý | Record thiếu DOI/title/summary/ngày; DOI trùng; gate không đạt; corruption làm trống summary hoặc nhân đôi DOI |

### Cách xác minh

Điểm vào đã được chạy bằng bản Python 3.11 khả dụng; với môi trường Python cài đúng, lệnh tái hiện là:

    python script/run_phase1.py
    python -c "from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); c=corrupt_clean_dataframe(df, s.paths.corruption_log); print(len(c))"

- **Kết quả mong đợi:** Có clean CSV/JSON, baseline metrics/report và corruption log đủ sáu loại.
- **Kết quả thực tế:** 24 clean records; baseline Hit Rate 100%, Token F1 0,8000; corruption trả 22 dòng và log 20 sự kiện.
- **Artifact/log:** [clean JSON](../data/clean/papers_clean.json), [phase1 report](../data/reports/phase1_report.md), [corruption log](../data/results/corruption_log.json).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Dữ liệu lỗi có thể làm index và metric sai lệch mà pipeline vẫn chạy.
- **Các phương án đã cân nhắc:** Index trước rồi kiểm tra; hoặc kiểm tra quality/freshness trước khi tạo baseline index.
- **Phương án đã chọn:** Baseline chạy gate trước index và dừng nếu không đạt. Phase 2 chủ ý đánh giá bản corrupted dù gate thất bại để đo silent failure.
- **Lý do:** Baseline được bảo vệ, còn thí nghiệm vẫn đo được hậu quả của việc bỏ qua cảnh báo.
- **Bằng chứng:** [Baseline quality](../data/quality/baseline_quality_report.json) đạt; [corrupted quality](../data/quality/corrupted_quality_report.json) không đạt nhưng [corrupted metrics](../data/results/corrupted_metrics.json) vẫn được ghi để so sánh.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi:** Lệnh python mặc định trên máy báo “No Python at ...Python312/python.exe”.
- **Bước tái hiện:** Gọi python --version trong terminal dùng để chạy bài lab.
- **Nguyên nhân gốc xác định:** Launcher của môi trường trỏ đến bản Python 3.12 không còn ở đường dẫn đó; lỗi xảy ra trước khi mã pipeline chạy.
- **Cách xử lý:** Chạy các lệnh nghiệm thu bằng bản Python 3.11 sẵn có, nạp đường dẫn src khi cần.
- **Cách xác minh sau khi sửa:** Script Phase 1 sinh [báo cáo baseline](../data/reports/phase1_report.md); lệnh corruption in 22 dòng và sinh [log](../data/results/corruption_log.json).
- **Điều học được:** Khi lệnh không khởi động được interpreter, phải kiểm tra môi trường trước khi quy lỗi cho ingestion hoặc cleaning.

## 7. Hiểu biết về luồng end-to-end

1. Đạt giữ Crossref response và tạo PaperRecord; cleaning biến records thành DataFrame sạch, text_for_embedding được MiniLM mã hóa và nạp vào Chroma.
2. Test set của Đạt ghi ground_truth_doc_ids là DOI; evaluator tính Hit Rate theo DOI truy hồi và Token F1 theo câu trả lời.
3. GX đo completeness, uniqueness, độ dài và số dòng; freshness xét age_days > 180 và tỷ lệ bài cũ tối đa 25%.
4. Giữ nguyên test_set.json khi đổi corpus giúp phân biệt tác động của corruption/repair với tác động do đổi câu hỏi.
5. Repair của Nam được xem là đạt khi DOI và dữ liệu sạch được dựng lại từ raw snapshot, quality gate đạt và Hit Rate/Token F1 về mức baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét theo phần việc |
| --- | ---: | ---: | ---: | --- |
| retrieval_hit_rate | 100% | 50% | 100% | 5 bài mới nhất bị bỏ là đúng 5 DOI truy hồi trượt |
| mean_token_f1 | 0,8000 | 0,4207 | 0,8000 | Corruption làm giảm chất lượng câu trả lời |
| judge_accuracy | 80% | 40% | 80% | Chế độ judge khác nhau, không so sánh trực tiếp |
| mean_judge_score | 4,20/5 | 2,60/5 | 4,20/5 | Baseline LLM judge; hai trạng thái sau heuristic |
| Quality checks | Đạt, 24 dòng | Không đạt, 22 dòng | Đạt, 24 dòng | Trùng DOI và summary ngắn bị phát hiện |
| Freshness status | Đạt, 0/24 cũ | Đạt, 3/22 cũ | Đạt, 0/24 cũ | 13,64% vẫn dưới ngưỡng 25% |

Nguồn: [ba bộ metrics](../data/reports/corruption_report.md), [corruption log](../data/results/corruption_log.json) và [quality artifacts](../data/quality/corrupted_quality_report.json).

### Kết luận từ số liệu

1. Bỏ 5 bài mới nhất và tiêm các lỗi còn lại → GX báo trùng DOI/summary ngắn; 5 DOI mục tiêu bị bỏ trùng với cả 5 lượt retrieval miss → Hit Rate giảm 50 điểm phần trăm, Token F1 giảm 0,3793. Trong các lỗi, drop latest có bằng chứng riêng rõ nhất về tác động tới retrieval.
2. Nam dựng lại từ raw snapshot → quality gate đạt, 24 DOI trở lại → Hit Rate 100%, Token F1 0,8000.

Kết quả khác kỳ vọng đơn giản “lùi ngày là sẽ stale”: 3/22 bài cũ hơn 180 ngày vẫn chỉ là 13,64%, nên Freshness SLA còn đạt. Đây là tỷ lệ được đo từ [freshness report](../data/quality/corrupted_freshness_report.json), không phải lỗi của hàm tính tuổi.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Một clean schema ổn định nối ingest, embedding, benchmark và quality gate.
2. Gate phát hiện lỗi cấu trúc trước index; freshness SLA cần đọc tỷ lệ chứ không chỉ đếm bài cũ.
3. Bỏ DOI mà benchmark cần tạo suy giảm retrieval đo được; log theo DOI cho phép chứng minh quan hệ đó.

### Nếu có thêm thời gian

Thử riêng từng corruption scenario trên cùng test set rồi đo delta Hit Rate/Token F1 cho từng loại. Cách này tách ảnh hưởng của drop latest khỏi các lỗi xảy ra đồng thời.

## 10. Cam kết của thành viên

Phần này để Hải Hoàng tự kiểm tra và xác nhận; các ô chưa được đánh dấu thay.

- [x] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi thành công cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa .env, API key, token hoặc secret.
- [x] Báo cáo này không sao chép nguyên văn báo cáo nhóm hoặc thành viên khác.

**Họ và tên:** Nguyễn Hải Hoàng  

**Ngày xác nhận:** 2026-9-26
