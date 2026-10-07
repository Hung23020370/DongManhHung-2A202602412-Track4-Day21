# Báo cáo Day 6: LiDAR–camera projection QA — độ nhạy của overlay với lệch yaw theo khoảng cách

> Thay **mọi** ô có chữ ĐIỀN nằm trong ngoặc vuông bằng nội dung của bạn, xoá luôn cả dấu ngoặc vuông. Lệnh `python tools/check_submission.py` sẽ báo FAIL nếu còn sót bất kỳ chỗ nào.

- **Họ tên:** Đồng Mạnh Hùng
- **MSSV:** 2A202602412 (phải trùng với MSSV trong tên repo `<HoVaTen>-<MSSV>-Track4-Day21`)
- **Lớp:**  AI20K-T4
- **Link repo:** https://github.com/Hung23020370/DongManhHung-2A202602412-Track4-Day21
- **Topic:** A — LiDAR-camera projection QA
- **Dataset:** data/kitti_mini (thí nghiệm chính), data/synthetic (kiểm tra tay hàm chiếu ở CP2)
- **Các frame đã dùng:** kitti_mini: cả 20 frame (000001, 000004, 000007, 000008, 000009, 000010, 000011, 000012, 000015, 000016, 000019, 000021, 000023, 000025, 000031, 000032, 000043, 000048, 000049, 000061) cho thí nghiệm sweep; ảnh overlay demo ở 000025, 000007, 000011. synthetic: 000000

> Hãy viết ngắn: mỗi mục từ 3 đến 8 dòng, ưu tiên số liệu và hình ảnh.

## 1. Claim

Một câu khẳng định kỹ thuật có thể kiểm chứng. Ví dụ: *"Lệch yaw 1° làm 12% điểm LiDAR rơi ra khỏi vật thể ở 30 m, phát hiện được bằng edge-alignment score với ngưỡng X."*

**Claim (nháp, CP1):** Trên 33 xe `Car` không bị che và không bị cắt (`truncated = 0`, `occluded = 0`) của `data/kitti_mini`, khi LiDAR lệch yaw 1° so với calibration gốc, hơn 10% điểm LiDAR của xe (điểm nằm trong 3D box GT) chiếu ra ngoài 2D box GT nếu xe cách ≥ 30 m, và tỉ lệ này lớn hơn ít nhất 2 lần so với xe cách < 15 m.

Lý do dự đoán: lệch 1° dịch điểm trên ảnh khoảng f·θ ≈ 12.6 px (f ≈ 720 px), gần như không đổi theo khoảng cách, trong khi bề rộng xe trên ảnh co lại theo 1/d; vì vậy tỉ lệ điểm rơi ra ngoài tăng gần tuyến tính theo d (xấp xỉ d·sin 1° / bề rộng xe).

Sẽ đo: % điểm của xe nằm ngoài 2D box, theo yaw 0°, 0.5°, 1°, 2°, 3° và theo nhóm khoảng cách (< 15 m, 15–30 m, ≥ 30 m). Claim có thể được sửa ở các checkpoint sau.

## 2. Evidence

Bảng hoặc plot số liệu, kèm ảnh/video demo. Ghi rõ đường dẫn file trong `results/`.

| Cấu hình / mức perturb | Metric 1 | Metric 2 | Ghi chú |
|---|---|---|---|
| [ĐIỀN] | | | |

![demo](../results/figures/[ĐIỀN].png)

## 3. Failure case

Nêu khi nào hệ thống hoặc phương pháp fail, vì sao fail, và liên hệ tới lớp nào trong 6 lớp debug: I/O, Geometry, Time, Preprocess, Model, Metric.

![failure](../results/figures/fail_[ĐIỀN].png)

[ĐIỀN]

## 4. Khuyến nghị nếu triển khai thật

Use-case cụ thể (ADAS / robot / drone), trade-off và bước tiếp theo.

[ĐIỀN]

## 5. Cách chạy lại

Các lệnh tái tạo lại toàn bộ kết quả từ repo sạch.

```bash
# CP2: test tay + ảnh overlay 3 khoảng cách (gần/vừa/xa)
python -m src.cp2_demo
# Overlay đầy đủ từng frame bằng CLI của starter
python -m starter.projection --data-root data/kitti_mini --frame 000025
python -m starter.projection --data-root data/kitti_mini --frame 000011
python -m starter.projection --data-root data/kitti_mini --frame 000007
```

## 6. Khai báo sử dụng AI

Ghi rõ đã dùng công cụ AI nào, dùng vào việc gì, và bạn đã tự kiểm chứng kết quả đó bằng cách nào. Nếu không dùng AI, ghi "Không sử dụng". Xem quy định ở `RULES.md` mục 2.

| Công cụ | Dùng cho việc gì | Bạn đã kiểm chứng thế nào |
|---|---|---|
| [ĐIỀN] | | |