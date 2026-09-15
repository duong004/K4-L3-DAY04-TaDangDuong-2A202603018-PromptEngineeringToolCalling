# TEAM — Day04, K4-L3B

**Bài làm cá nhân.**

## Thông tin bài nộp

- Tên nhóm: 03018
- Người đại diện / MSSV: Tạ Đăng Dương 2A202603018
- Tên repo: `K4-L3-DAY04-TaDangDuong-2A202603018-PromptEngineeringToolCalling`
- URL repo, nhánh nộp, commit chốt: [tại đây](https://github.com/duong004/K4-L3-DAY04-TaDangDuong-2A202603018-PromptEngineeringToolCalling), nhánh `main`, commit `HEAD`
- Deadline áp dụng và link thông báo đổi hạn nếu có: 12:00 ngày 16/09/2026

## Thành viên

| Họ và tên | MSSV | GitHub | Vai trò và công việc | File/commit/PR |
|---|---|---|---|---|
| Tạ Đăng Dương | 2A202603018 | duong004 | Toàn bộ các phần việc: Tối ưu prompt, chuẩn hóa tool declaration, xây dựng bộ eval nhóm, viết giao diện Streamlit UI, chạy đối chiếu v0–v3, phân tích an toàn và báo cáo kỹ thuật | `artifacts/system_prompt.md`, `artifacts/tools.yaml`, `data/eval_group.json`, `app_ui.py`, `artifacts/version_log.csv`, `artifacts/REPORT.md`, `transcripts/` |

## Nhận xét chung

- Kết quả và bằng chứng: Hoàn thành 4 phiên bản v0–v3 trên bộ test chuẩn 30 câu (`eval_base.json`), cải thiện độ chính xác từ 66.67% (v0) lên 100% (v2, v3); bộ 10 ca nhóm tự xây dựng (`eval_group.json`) đạt 10/10 PASS; hoàn thành kiểm thử an toàn trên bộ 12 ca adversarial; hoàn thiện giao diện Streamlit UI có ghi nhận tool call, kết quả và phiên bản artifact.
- Thay đổi hiệu quả nhất: Thiết lập ranh giới bắt buộc dừng lại xác nhận bằng `clarify(response_type="yes_no")` trước khi ghi dữ liệu (`create_ticket`), kết hợp chỉ dẫn gọi song song (parallel tool calls) cho từng thực thể riêng biệt trong `system_prompt.md`.
- Giới hạn còn lại: Trong các kịch bản tấn công adversarial phức tạp (smuggling hoặc role spoofing), mô hình đôi khi vẫn bị phân vân giữa việc từ chối thẳng hay gọi clarify để hỏi lại, dẫn đến lệch boundary kỳ vọng dù không có dữ liệu nhạy cảm nào bị ghi ra ngoài.
- Cách phân công và tích hợp: Tự chủ động thực hiện toàn diện theo chu trình khép kín: phân tích trace lỗi từ run JSON -> đặt giả thuyết -> can thiệp prompt/tool -> đánh giá tự động -> ghi nhận transcript qua UI.

## INDIVIDUAL

### Tạ Đăng Dương — 2A202603018

- Phần việc và file/commit/PR:
  - Phân tích lỗi và hoàn thiện 4 vòng lặp artifacts: `starter_v0/artifacts/system_prompt.md`, `starter_v0/artifacts/tools.yaml`, `starter_v0/artifacts/version_log.csv`.
  - Tự thiết kế và kiểm thử 10 kịch bản đánh giá mở rộng (5 single-turn, 5 multi-turn): `starter_v0/data/eval_group.json`.
  - Xây dựng giao diện Streamlit trực quan có hiển thị input/output của tool, bộ lọc lỗi và trích xuất transcript: `starter_v0/app_ui.py`, `starter_v0/transcripts/`.
  - Viết toàn bộ tài liệu kỹ thuật và tự đánh giá: `starter_v0/artifacts/REPORT.md`, `TEAM.md`.
- Quyết định, khó khăn và cách xử lý:
  - Khó khăn: Ban đầu Gemini Free Tier bị lỗi HTTP 429 Rate Limit (do hạn mức RPM thấp).
  - Quyết định xử lý: Thêm cơ chế tự động thử lại (Adaptive Retry with backoff) trong adapter `gemini_provider.py` để chạy liền mạch mà không vi phạm nguyên tắc đánh giá.
  - Tối ưu prompt: Tách bạch rõ ranh giới giữa tác vụ đọc (chẩn đoán, tra cứu) và tác vụ ghi (tạo ticket), đồng thời chỉ dẫn rõ không được gộp nhiều mã máy vào một lệnh gọi đơn lẻ.
- Điều đã học:
  - Hiểu sâu về cơ chế Function Calling/Tool Calling trong các LLM hiện đại: mô hình không tự thực thi code mà sinh cấu trúc JSON để ứng dụng gọi hàm.
  - Nắm vững kỹ thuật Prompt Engineering thực chiến: dùng cấu trúc ranh giới rõ ràng (Action Boundaries, Clarification Boundaries) để kiểm soát hành vi mô hình tin cậy hơn so với việc chỉ mô tả chung chung.
  - Kỹ năng đánh giá dựa trên bằng chứng (Evidence-based evaluation) qua log JSON thay vì chỉ đánh giá cảm tính qua vài câu chat đơn lẻ.
- AI/công cụ đã dùng và cách kiểm tra: Sử dụng Gemini model để hỗ trợ rà soát cú pháp schema JSON, tự kiểm chứng độc lập lại từng trường hợp bằng terminal run và đối chiếu trực tiếp với kết quả trong `runs/*.json`.
- Thời điểm đã tự nộp URL repo trên VLearn: 2026-09-15 21:00 UTC+07:00