1 . Mở Terminal tại thư mục dự án và chạy lệnh cài đặt thư viện: 
```bash
pip install -r requirements.txt
2 . Thiết Lập Mạch Khởi Động ESP32 (Wokwi)
  - Truy cập vào trang mô phỏng mạch https://wokwi.com/projects/464901992023857153 bằng wokwi
  - Bấm chạy mạch để kết nối mạng ảo và MQTT Broker.
**Quy Trình Khởi Chạy Hệ Thống Test**
Để hệ thống đồng bộ mượt mà, bạn cần khởi chạy các cấu phần theo đúng thứ tự sau:
Bước 1: Khởi động Server Trung Tâm (app.py)
Chạy lệnh sau tại terminal:
python app.py
Màn hình sẽ hiển thị thông báo kết nối thành công tới MQTT Broker broker.emqx.io và mở cổng REST API tại địa chỉ http://127.0.0.1:5000.

Bước 2: Bật Web Dashboard Giám Sát (index.html)
Bạn chỉ cần click đúp chuột vào file index.html để mở trực tiếp trên trình duyệt web (Chrome, Edge, Firefox...). Lúc này bạn sẽ thấy trạng thái mạch chuyển từ "Đang kết nối..." thành thông tin đèn hiện tại của ESP32 (Ví dụ: Truc B-N: Xanh | Truc D-T: Do).

Bước 3: Kích hoạt Camera AI Edge (ai_detector.py)
Đảm bảo bạn đã để file video tên traffic.mp4 cùng cấp thư mục với code. Chạy lệnh:
python ai_detector.py
Mô hình YOLOv8 sẽ được tải, hai khung hình chữ nhật đại diện cho ROI Bắc-Nam và Đông-Tây sẽ hiện lên kèm số lượng phương tiện thực tế nhảy liên tục.
