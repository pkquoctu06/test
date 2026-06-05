import cv2
import time
import requests
import os
from ultralytics import YOLO

SERVER_URL = "http://127.0.0.1:5000/api/update_traffic"
INTERSECTION_ID = "J01"

print("Đang tải mô hình YOLOv8...")
model = YOLO('yolov8n.pt') 

video_file = 'traffic.mp4' if os.path.exists('traffic.mp4') else 0
cap = cv2.VideoCapture(video_file) 

# Tọa độ 2 trục đường (X1, Y1, X2, Y2) - Bạn có thể tinh chỉnh lại cho khớp video
ROI_BN = [250, 50, 450, 700]  # Trục dọc (Bắc - Nam)
ROI_DT = [50, 300, 650, 500]  # Trục ngang (Đông - Tây)

last_send_time = time.time()

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue

    results = model(frame, conf=0.15, verbose=False)
    
    # Tắt chữ (labels) và tắt số % (conf) để màn hình sạch sẽ
    annotated_frame = results[0].plot(labels=False, conf=False)
    
    # Vẽ 2 vùng ROI
    cv2.rectangle(annotated_frame, (ROI_BN[0], ROI_BN[1]), (ROI_BN[2], ROI_BN[3]), (255, 0, 0), 2)
    cv2.putText(annotated_frame, "TRUC BAC-NAM", (ROI_BN[0], ROI_BN[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
    
    cv2.rectangle(annotated_frame, (ROI_DT[0], ROI_DT[1]), (ROI_DT[2], ROI_DT[3]), (0, 255, 255), 2)
    cv2.putText(annotated_frame, "TRUC DONG-TAY", (ROI_DT[0], ROI_DT[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    
    count_BN = 0
    count_DT = 0
    
    for box in results[0].boxes:
        x1, y1, x2, y2 = box.xyxy[0]
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        
        # Kiểm tra xe thuộc trục nào
        if ROI_BN[0] < cx < ROI_BN[2] and ROI_BN[1] < cy < ROI_BN[3]:
            count_BN += 1
            cv2.circle(annotated_frame, (cx, cy), 6, (0, 0, 255), -1)
        elif ROI_DT[0] < cx < ROI_DT[2] and ROI_DT[1] < cy < ROI_DT[3]:
            count_DT += 1
            cv2.circle(annotated_frame, (cx, cy), 6, (0, 255, 0), -1)

    # Hiển thị số lượng lên cam
    cv2.putText(annotated_frame, f"B-N: {count_BN} | D-T: {count_DT}", (20, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.imshow("AI Traffic Camera", annotated_frame)

    current_time = time.time()
    if current_time - last_send_time > 3: 
        payload = {
            "intersection_id": INTERSECTION_ID, 
            "count_BN": count_BN,
            "count_DT": count_DT
        }
        try:
            requests.post(SERVER_URL, json=payload)
        except Exception:
            pass 
        last_send_time = current_time

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()