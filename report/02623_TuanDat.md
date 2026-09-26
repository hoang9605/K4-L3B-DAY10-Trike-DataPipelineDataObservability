# Báo cáo cá nhân — 02623_TuanDat

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Tuấn Đạt |
| MSSV | 02623 |
| Khóa/Lớp | K4-L3B-DAY10 |
| Tên nhóm | Trike |
| Vai trò chính | Raw ingestion và benchmark test set |
| Repository | [K4-L3B-DAY10-Trike-DataPipelineDataObservability](https://github.com/hoang9605/K4-L3B-DAY10-Trike-DataPipelineDataObservability) |
| Ngày ghi nhận | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Crossref ingestion | src/ingestion/crossref.py: parse_crossref_payload, fetch_source_records | JSON Crossref API hoặc snapshot | data/raw/crossref_response.json; data/raw/crossref_records.json | Hoàn thành |
| Evaluation set | src/evaluation/testset.py: build_test_set | DataFrame sạch từ Hoàng | data/eval/test_set.json | Hoàn thành |

Raw records được Hoàng dùng để cleaning; DOI và nội dung sạch được dùng để tạo câu hỏi, rồi Nam dùng cùng test set khi đánh giá ba trạng thái.

### Việc hỗ trợ ngoài phạm vi chính

Giúp sửa luồng pipeline phase 1
Góp ý, cait thiện pipeline phase 2

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Bóc tách DOI, title, abstract, authors, subject và ngày; bỏ thẻ HTML/XML | [crossref.py](../src/ingestion/crossref.py) | [24 raw records](../data/raw/crossref_records.json) | Đếm phần tử JSON; đối chiếu [response gốc](../data/raw/crossref_response.json) |
| Giữ nguyên response API khi có kết nối; fallback về snapshot nếu API lỗi | [crossref.py](../src/ingestion/crossref.py) | Response và records lưu riêng | Xem nhánh fetch/fallback trong mã; artifact không chứng minh lần chạy cụ thể đã dùng nhánh nào |
| Tạo 10 câu hỏi có ground truth và DOI nguồn | [testset.py](../src/evaluation/testset.py) | [test_set.json](../data/eval/test_set.json): 3 summary, 3 authors, 2 date, 2 categories | Lệnh build_test_set và đếm question_type |

Output quan trọng nhất là response gốc và bản ghi bóc tách riêng biệt: khi parser thay đổi, nhóm có thể dựng lại dữ liệu mà không gọi Crossref thêm lần nữa.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Crossref trả về JSON lồng trong message.items, abstract có thể chứa markup và trường subject có thể thiếu. Pipeline cần schema PaperRecord ổn định cùng bản gốc làm điểm truy nguyên. Benchmark phải gắn mỗi câu hỏi với DOI để đánh giá truy hồi đúng tài liệu.

### Cách triển khai

Parser chuẩn hóa DOI, tiêu đề, tóm tắt, tác giả và ngày ISO; bỏ record thiếu DOI, tiêu đề, summary hoặc ngày hợp lệ. Hàm fetch thử lại giới hạn khi gặp 429/503; khi có response hợp lệ, lưu bytes gốc rồi ghi danh sách PaperRecord. Nếu không gọi được API, đọc snapshot gốc mà không sửa file đó. Test set chọn bài theo DOI, tránh cặp câu hỏi/DOI trùng và tạo 10 câu theo phân bố 3/3/2/2.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref message.items; DataFrame sạch có paper_id, title, summary, authors_joined, published, categories_joined |
| Output | Danh sách PaperRecord; hai raw artifacts; danh sách câu hỏi có id, question_type, ground_truth, ground_truth_doc_ids |
| Module phụ thuộc | core.config; core.utils; dữ liệu sạch từ ingestion.cleaning |
| Module sử dụng output | ingestion.cleaning; pipelines.phase1; evaluation.metrics; pipelines.corruption_flow |
| Điều kiện lỗi cần xử lý | 429/503 hoặc mất mạng; payload thiếu message.items; record thiếu trường bắt buộc; ít hơn 5 bài hợp lệ cho benchmark |

### Cách xác minh

Lệnh nghiệm thu đã dùng với môi trường Python 3.11 khả dụng:

    python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(len(ts))"

- **Kết quả mong đợi:** 10 câu hỏi có DOI nguồn và đủ bốn loại.
- **Kết quả thực tế:** 10 câu, phân bố summary/authors/date/categories = 3/3/2/2; raw records hiện có 24 bài.
- **Artifact/log:** [test_set.json](../data/eval/test_set.json), [crossref_records.json](../data/raw/crossref_records.json). Không suy đoán lượt tải trực tuyến từ sự tồn tại của snapshot.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần vừa chuẩn hóa metadata vừa giữ nguồn có thể tái xử lý.
- **Các phương án đã cân nhắc:** Chỉ lưu PaperRecord đã chuẩn hóa; hoặc lưu response gốc riêng rồi lưu PaperRecord riêng.
- **Phương án đã chọn:** Hai artifact tách biệt, response trực tuyến được ghi nguyên bytes.
- **Lý do:** Có thể kiểm tra sai lệch do parser và chạy lại khi API bị rate limit.
- **Bằng chứng:** [response gốc](../data/raw/crossref_response.json) và [24 records](../data/raw/crossref_records.json) đều hiện diện; hàm repair Phase 2 dùng lại response gốc.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** 0/24 bài trong snapshot có subject; categories_joined rỗng. Hai câu hỏi categories có Token F1 bằng 0 ở baseline và repaired.
- **Bước tái hiện:** Đọc subject trong [response gốc](../data/raw/crossref_response.json), đối chiếu [test set](../data/eval/test_set.json) và metrics theo question_type.
- **Nguyên nhân gốc xác định:** Metadata nguồn hiện dùng không cung cấp subject; không có bằng chứng parser đã làm mất trường này.
- **Cách xử lý trong phạm vi benchmark:** Câu hỏi categories dùng ground truth thông báo Crossref không liệt kê lĩnh vực để vẫn đủ bốn loại câu hỏi. Việc đánh giá kiến thức lĩnh vực thực tế chưa được giải quyết.
- **Cách xác minh:** 10 câu được tạo, nhưng [baseline metrics](../data/results/baseline_metrics.json) ghi categories Token F1 = 0.
- **Bước tiếp theo:** Chọn snapshot có subject, sinh lại test set và đo riêng Token F1 của categories; không sửa tay ground truth.

## 7. Hiểu biết về luồng end-to-end

1. Crossref response được lưu nguyên gốc, bóc thành PaperRecord, Hoàng làm sạch và ghép text_for_embedding, sau đó index Chroma được xây từ văn bản đó.
2. Test set chứa câu hỏi, câu trả lời chuẩn và ground_truth_doc_ids là DOI; evaluator so DOI truy hồi với DOI chuẩn rồi chấm câu trả lời.
3. GX kiểm tra số dòng, trường bắt buộc, tính duy nhất và độ dài summary; freshness đo tỷ lệ bài có age_days trên 180 và so với ngưỡng 25%.
4. Dùng cùng test_set.json cho baseline, corrupted và repaired giữ cố định câu hỏi/DOI, nên chênh lệch phản ánh thay đổi corpus thay vì thay bộ đề.
5. Repair thành công khi dữ liệu dựng lại từ raw snapshot vượt quality gate và Hit Rate/Token F1 trở về baseline; [báo cáo Phase 2](../data/reports/corruption_report.md) ghi kết quả đó.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét theo phần việc |
| --- | ---: | ---: | ---: | --- |
| retrieval_hit_rate | 100% | 50% | 100% | DOI mục tiêu mất khi bỏ bài mới; khôi phục từ raw lấy lại DOI |
| mean_token_f1 | 0,8000 | 0,4207 | 0,8000 | Chất lượng trả lời đi theo thay đổi dữ liệu |
| judge_accuracy | 80% | 40% | 80% | Baseline dùng LLM judge, hai trạng thái sau dùng heuristic |
| mean_judge_score | 4,20/5 | 2,60/5 | 4,20/5 | Không so sánh trực tiếp vì chế độ judge khác |
| Quality checks | Đạt, 24 dòng | Không đạt, 22 dòng | Đạt, 24 dòng | Summary ngắn và DOI trùng bị phát hiện |
| Freshness status | Đạt, 0/24 cũ | Đạt, 3/22 cũ | Đạt, 0/24 cũ | 13,64% vẫn dưới SLA 25% |

Nguồn: [baseline](../data/results/baseline_metrics.json), [corrupted](../data/results/corrupted_metrics.json), [repaired](../data/results/repaired_metrics.json) và [báo cáo chất lượng](../data/reports/corruption_report.md).

### Kết luận từ số liệu

1. Bỏ 5 bài mới nhất → 5 DOI mục tiêu trong test set không còn trong corpus, quality gate cũng thất bại vì các lỗi kèm theo → Hit Rate giảm còn 50%, Token F1 còn 0,4207. Đối chiếu corruption log với corrupted answers cho thấy cả 5 lượt trượt truy hồi trùng DOI bị bỏ; đây là tác động rõ nhất có bằng chứng theo từng câu.
2. Dựng lại từ response Crossref gốc → quality gate đạt, số dòng trở về 24 → Hit Rate 100% và Token F1 0,8000.

Điểm khác kỳ vọng: dù câu hỏi categories được giữ trong bộ đề, Token F1 của loại này vẫn bằng 0 sau repair. Nguyên nhân nằm ở subject thiếu từ nguồn, nên repair dữ liệu không thể tự tạo metadata chưa từng có.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw response và records chuẩn hóa phục vụ hai mục đích khác nhau: truy nguyên và xử lý.
2. Benchmark chỉ đáng tin khi ground truth thực sự có trong dữ liệu nguồn; câu hỏi categories hiện là ca kiểm tra metadata thiếu.
3. DOI giữ ổn định từ ingestion đến test set giúp chỉ ra chính xác các bài bị mất gây trượt retrieval.

### Nếu có thêm thời gian

Thu thập bộ Crossref có subject, tái tạo benchmark theo cùng schema và đo categories Token F1 trước/sau; đồng thời giữ một bộ câu hỏi không chứa nguyên tiêu đề để kiểm tra retrieval thực tế hơn.

## 10. Cam kết của thành viên

Phần này để Tuấn Đạt tự kiểm tra và xác nhận; các ô chưa được đánh dấu thay.

- [x] Nội dung phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi thành công cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa .env, API key, token hoặc secret.
- [x] Báo cáo này không sao chép nguyên văn báo cáo nhóm hoặc thành viên khác.

**Họ và tên:** Lê Tuấn Đạt

**Ngày xác nhận:** 2026-9-26
