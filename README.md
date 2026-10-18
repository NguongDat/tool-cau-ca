# 🎣 Tool Auto Bậc Thầy Câu Cá (Roblox Fishing Master)

Tool tự động câu cá chuyên nghiệp, siêu tốc và ổn định dành cho tựa game **Bậc Thầy Câu Cá (Fishing Master)** trên Roblox, kết hợp công nghệ **Thị giác máy tính (Computer Vision - OpenCV)** và **Phím ảo phần cứng cấp độ Driver (PyDirectInput + user32)**.

---

## 🌟 Tính Năng Nổi Bật

### 1. 🍀 Tự Động Quăng Cần & Đạt Nóc Luck Boost
- Tự động giữ chuột trái và dùng OpenCV quét thanh **LUCK BOOST**.
- Canh chính xác thời điểm dải sáng chạm nóc bo tròn **màu xanh lá cây** mới nhả chuột, giúp quăng cần đạt tỉ lệ may mắn cao nhất (100% Luck Boost).

### 2. 💥 Bắt Chuẩn Mốc x10 DAMAGE Khi Cá Cắn Câu
- Khi cá cắn câu, thanh sát thương xuất hiện (dải màu cyan $\rightarrow$ tím $\rightarrow$ đỏ mốc **x10 DAMAGE**).
- Bot theo dõi chính xác icon con cá trượt lên đỉnh, chạm vùng đỏ **x10 DAMAGE** là click giật cần ngay lập tức để gây lượng sát thương khởi đầu cực đại.

### 3. ⚡ Xả Combo Skill Siêu Tốc Không Độ Trễ (`Z -> C -> X -> V`)
- Cơ chế xả liên hoàn: Dùng xong skill này là xả ngay skill kế tiếp chỉ sau **25ms** (không có vòng lặp ngắt quãng hay delay thừa).
- Tối ưu hồi chiêu xuống **1.5s - 2.5s**, tự động reset hồi chiêu về 0 ngay khi vừa cắn câu để tung trọn bộ combo từ frame đầu tiên.
- **Ghìm thanh trượt cá liên tục**: Tự động spam click chuột trái dứt khoát cấp phần cứng để ghìm thanh trượt cá trong lúc chờ skill hồi, ngăn chặn triệt để tình trạng thanh cá tăng cao làm trượt/sổng cá.

### 4. 🎯 Phản Xạ QTE [A], [W], [D], [S] & Mũi Tên Chuẩn 100%
- Nhận diện ký tự phím QTE siêu tốc (> 100 FPS), kích hoạt chính xác sự kiện phím cho Roblox, chống miss nhịp QTE.
- Tự động tạm dừng spam click khi có QTE để tránh bị game hủy nhịp.

### 5. 🛑 Nhân Vật Đứng Yên Tuyệt Đối
- Đứng yên 100% tại chỗ khi câu và sau khi kéo cá lên, lập tức quăng cần mới.
- Loại bỏ hoàn toàn di chuyển thừa thãi, không lo rơi xuống nước hay kẹt địa hình.

---

## 🎮 Phím Tắt & Điều Khiển

* **Phím F6:** Bật / Tắt Auto (Bấm F6 để bắt đầu, bấm F6 lần nữa để dừng lại ngay lập tức).

---

## 🚀 Cách Chạy Tool

1. Nhấp đúp chuột vào file: **`Chay_Tool.bat`** (hoặc mở terminal gõ `python main.py`).
2. Cầm sẵn cần câu trên tay nhân vật, hướng góc nhìn ra mặt nước.
3. Bấm **F6** để bắt đầu auto!
