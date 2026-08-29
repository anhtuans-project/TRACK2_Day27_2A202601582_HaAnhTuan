# Báo cáo Sửa lỗi & Cải thiện Hệ thống Observability

Tài liệu này tổng hợp các thay đổi đã thực hiện để khắc phục các trường hợp kiểm tra bị lỗi (Failed Cases) trong hệ thống phát hiện bất thường, theo dõi SLO và đo lường RAG.

## 1. Phát hiện Bất thường (Anomaly Detection)
**Các case bị lỗi:** `H07`, `H09` (Hard)

### Vấn đề & Nguyên nhân
- **Nhạy cảm quá mức với dữ liệu mùa vụ (Seasonality):** Khi sử dụng các phân đoạn nhỏ (ví dụ: chỉ so sánh thứ Hai tuần này với các thứ Hai trước), phương sai thấp khiến các biến động nhỏ cũng bị gắn nhãn là bất thường.
- **Xử lý sai baseline phẳng (Zero Variance):** Trong phương pháp MAD, khi `MAD = 0`, hệ thống không có cơ chế dự phòng hiệu quả để tính điểm cho các giá trị khác với median.
- **Bỏ sót xu hướng (Trend):** Các giá trị tăng/giảm tuyến tính bị gắn nhãn là bất thường vì so sánh với trung bình toàn cục.
- **Sự kiện đã biết (Known Events):** Các đợt tăng trưởng dự kiến (ví dụ: khuyến mãi) vẫn bị báo động dù là hành vi bình thường.

### Giải pháp
- **Global Cross-check:** Khi một giá trị bị coi là bất thường trong phân đoạn mùa vụ (`same_segment_history`), hệ thống sẽ kiểm tra lại với toàn bộ lịch sử (`full_history`). Nếu giá trị đó bình thường so với tổng thể, kết quả sẽ bị ghi đè thành `is_anomaly = False`.
- **Robust MAD Detector:** Cải tiến `mad_detector` để khi `MAD = 0`, hệ thống tự động chuyển sang dùng độ lệch chuẩn (`std`) để tính điểm thay vì trả về `inf` một cách máy móc.
- **Strict Suppression:** Triển khai cơ chế suppress tuyệt đối cho `known_event`. Bất kỳ giá trị nào rơi vào sự kiện đã biết sẽ không bao giờ bị đánh dấu là bất thường, dù điểm thống kê cao đến đâu.
- **Ưu tiên MAD:** Trong chế độ `auto`, hệ thống ưu tiên sử dụng MAD thay cho Z-score khi có đủ dữ liệu ($\ge 5$ mẫu) để tăng cường khả năng chống nhiễu.

---

## 2. Theo dõi SLO (SLO Burn Rate)
**Case bị lỗi:** `H13` (Hard)

### Vấn đề & Nguyên nhân
- **Thiếu nhận diện "Slow Burn":** Hệ thống cũ chỉ tập trung vào các cú sốc lớn (Fast Burn) mà bỏ qua các trường hợp tiêu tốn ngân sách lỗi (error budget) một cách từ từ nhưng bền bỉ, dẫn đến việc không phát ra cảnh báo kịp thời trước khi vi phạm SLO.

### Giải pháp
- **Multi-window Burn Rate (Google SRE Standard):** Triển khai chính sách cửa sổ đa tầng:
    - **Fast Burn (Critical):** Kích hoạt khi cả cửa sổ ngắn (ví dụ: 1h) và cửa sổ dài (ví dụ: 6h) đều có burn rate cực cao ($\ge 14.4$).
    - **Slow Burn (Warning):** Kích hoạt khi cả hai cửa sổ đều có burn rate ở mức trung bình nhưng duy trì ($\ge 2.0$).
- **Phân cấp mức độ nghiêm trọng:** Tách biệt `severity: critical` cho Fast Burn và `severity: warning` cho Slow Burn để đội vận hành có phản ứng phù hợp.

---

## 3. Chỉ số RAG (RAG Metrics)
**Case bị lỗi:** `H18` (Expert)

### Vấn đề & Nguyên nhân
- **Nhạy cảm với Outliers:** Việc sử dụng giá trị trung bình (`mean`) của các vector norm hiện tại khiến hệ thống dễ bị đánh lừa bởi một vài mẫu dữ liệu cực đoan, dẫn đến báo động sai về sự dịch chuyển phân phối (distribution shift) của embedding.

### Giải pháp
- **Median-based Drift Detection:** Thay thế `mean` bằng `median` khi tính toán đại diện cho batch dữ liệu hiện tại.
- **Robust Baseline Comparison:** Sử dụng `median` của batch hiện tại để so sánh với baseline thông qua `mad_detector`, giúp việc phát hiện drift trở nên ổn định hơn và không bị ảnh hưởng bởi các vector nhiễu.

## Tổng kết kết quả
| Category | Case | Trạng thái ban đầu | Trạng thái sau sửa | Giải pháp chính |
| :--- | :--- | :--- | :--- | :--- |
| Anomaly | H07, H09 | FAIL | **PASS** | Global Cross-check & Robust MAD |
| SLO | H13 | FAIL | **PASS** | Fast/Slow Burn Policy |
| RAG | H18 | FAIL | **PASS** | Median-based Shift Detection |
