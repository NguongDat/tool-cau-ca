# HƯỚNG DẪN SỬ DỤNG TOOL AUTO BẬC THẦY CÂU CÁ (ROBLOX)

Tool được thiết kế tự động hoàn toàn bằng công nghệ thị giác máy tính (**Computer Vision - OpenCV + WinOCR**) kết hợp điều khiển phím ảo phần cứng (**PyDirectInput**) tối ưu riêng cho game **Bậc Thầy Câu Cá** trên Roblox.

---

## 1. CÁCH KHỞI ĐỘNG TOOL

1. Vào thư mục `d:\toolcauca`
2. Nhấp đúp chuột vào file: **`Chay_Tool.bat`** (hoặc mở terminal gõ `python main.py`).
3. Giao diện trực quan hiện đại sẽ xuất hiện.

---

## 2. PHÍM TẮT TOÀN CỤC (HOTKEYS)

* **Phím F6:** Bật / Tắt Auto (Bấm F6 để bắt đầu câu, bấm F6 lần nữa để dừng lại ngay lập tức, không cần dùng F7).

---

## 3. CÁC TÍNH NĂNG VÀ CÁCH THIẾT LẬP

### Tab 1: ⚡ Ưu Tiên Kỹ Năng & Combo Liên Hoàn (Skill DPS)
* **Xả chiêu liên hoàn không ngắt quãng (Dùng skill xong dùng skill khác luôn):**
  * Bot tự động kích hoạt toàn bộ chuỗi chiêu sẵn sàng theo thứ tự ưu tiên (ví dụ `[Z]` $\rightarrow$ `[C]` $\rightarrow$ `[X]` $\rightarrow$ `[V]`) ngay lập tức mà không có bất kỳ khoảng dừng hay vòng lặp chờ thừa thãi nào.
  * Độ trễ chuyển giữa 2 chiêu liên tiếp chỉ là **25ms** (gần như tức thì).
* **Thời gian hồi chiêu (Cooldown):**
  * Đã tối ưu về mức **1.5s - 2.5s** (có thể chỉnh theo ý muốn). Ngay khi chiêu hồi xong, bot sẽ tung chiêu tiếp theo ngay lập tức.
  * Toàn bộ hồi chiêu được tự động reset 100% về 0 ngay khi cá vừa cắn câu để xả trọn vẹn combo tức thì.
* **Tự động giữ thanh trượt cá (Spam Click chống trượt cá):**
  * Trong lúc các chiêu đang hồi, bot tự động spam click chuột trái dứt khoát cấp phần cứng để liên tục ghìm thanh trượt cá, ngăn chặn hoàn toàn việc thanh trượt tăng cao làm sổng cá.

### Tab 2: 🎣 Cài Đặt Câu & Cơ Chế Sát Thương 10x / Luck Boost
* **Thanh Luck Boost (Đạt nóc màu xanh lá cây):**
  * Khi quăng cần, bot tự động giữ chuột trái và dùng thị giác máy tính quét thanh **LUCK BOOST**.
  * Bot theo dõi vạch sáng dâng lên từ đáy cho đến khi chạm/lấp đầy **nóc bo tròn màu xanh lá cây** trên đỉnh thanh mới nhả chuột. Giúp quăng cần đạt mức độ may mắn (Luck Boost) tối đa 100%.
* **Thanh Gây Dame Đầu Tiên (Bắt chuẩn mốc x10 DAMAGE):**
  * Khi cá cắn câu, thanh đo lực sát thương đầu tiên xuất hiện (dải màu gradient từ xanh dương -> tím -> đỏ có chữ **x10 DAMAGE** trên đỉnh).
  * Bot tự động theo dõi icon con cá màu trắng di chuyển. Ngay khi con cá chạm vào vùng đỏ **x10 DAMAGE**, bot click chuột trái ngay lập tức để giật cần và gây lượng sát thương khởi đầu cực đại (x10 Dame).
* **Thời gian chờ cá cắn câu tối đa:** Mặc định là `15` giây (đảm bảo bot đợi cá cắn câu trọn vẹn, không bị thu cần sớm khi cá tiếp cận chậm).
* **Tự động bắt nhịp QTE [A], [W], [D], [S] & mũi tên PULL:**
  * Tự động quét siêu tốc (> 100 FPS, độ trễ < 3ms) để nhận diện chính xác 100% phím QTE (A, W, D, S) và mũi tên PULL ở khu vực giao chiến trung tâm.
  * **Cơ chế phản xạ QTE chính xác 100%:** Tự động gõ phím dứt khoát theo đúng nhịp minigame Roblox (kích hoạt chuẩn xác sự kiện InputBegan/InputEnded), lặp nhịp mượt mà chống triệt để tình trạng miss phím A, W, D, S.
  * Tự động tạm dừng spam click và xả skill ngay khi phát hiện QTE để tránh bị game hủy nhịp hoặc tính miss.
* **Đứng yên tại chỗ & quăng cần liên tục:** Nhân vật đứng yên tại chỗ không di chuyển khi câu và sau khi câu xong. Ngay khi cá vừa được kéo lên, bot lập tức giữ chuột quăng cần tiếp theo mà không có độ trễ thừa hay click thừa.

### Tab 3: 📊 Thống Kê & Số Cá
* **Đếm số lượng cá:** Hiển thị tổng số lượng cá đã câu được theo thời gian thực. Có nút **Reset Về 0** để đặt lại bộ đếm bất cứ lúc nào.
* **Tập trung câu cá 100%:** Đã loại bỏ hoàn toàn cơ chế di chuyển tìm NPC bán cá, đảm bảo nhân vật luôn đứng yên 100% tại điểm câu, không lo bị rơi xuống nước hay kẹt địa hình.

---

## 4. LỜI KHUYÊN ĐỂ AFK HIỆU QUẢ NHẤT
* Cầm sẵn cần câu trên tay nhân vật, hướng trỏ chuột ra phía mặt nước.
* Bấm **F6** để bắt đầu câu tự động. Khi muốn dừng, chỉ cần bấm lại **F6**.
