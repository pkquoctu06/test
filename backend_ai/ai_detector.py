import cv2
import time
import requests
import os
from ultralytics import YOLO

SERVER_URL = "http://127.0.0.1:5000/api/update_traffic"
INTERSECTION_ID = "J01"

# ===== CẤU HÌNH =====
STOP_LINE_Y = 350      # Điều chỉnh theo video
LIGHT_STATE = "RED"    # Demo, sau này lấy từ MQTT

vehicle_positions = {}
violated_ids = set()

print("Đang tải mô hình YOLOv8...")
model = YOLO("yolov8n.pt")

# Dùng file video nếu có, không thì dùng webcam
video_file = "traffic.mp4" if os.path.exists("traffic.mp4") else 0
cap = cv2.VideoCapture(video_file)

if not cap.isOpened():
    print("Không thể mở video hoặc camera!")
    exit()

# ROI đếm xe
ROI_BN = [250, 50, 450, 700]   # Bắc - Nam
ROI_DT = [50, 300, 650, 500]   # Đông - Tây

last_send_time = time.time()

while cap.isOpened():

    success, frame = cap.read()

    if not success:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue

    # Tracking
    results = model.track(
        frame,
        conf=0.15,
        persist=True,
        verbose=False
    )

    annotated_frame = results[0].plot(
        labels=False,
        conf=False
    )

    # ===== VẠCH DỪNG =====
    cv2.line(
        annotated_frame,
        (0, STOP_LINE_Y),
        (frame.shape[1], STOP_LINE_Y),
        (0, 0, 255),
        3
    )

    cv2.putText(
        annotated_frame,
        "STOP LINE",
        (20, STOP_LINE_Y - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 255),
        2
    )

    # ===== ROI =====
    cv2.rectangle(
        annotated_frame,
        (ROI_BN[0], ROI_BN[1]),
        (ROI_BN[2], ROI_BN[3]),
        (255, 0, 0),
        2
    )

    cv2.putText(
        annotated_frame,
        "TRUC BAC-NAM",
        (ROI_BN[0], ROI_BN[1] - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 0, 0),
        2
    )

    cv2.rectangle(
        annotated_frame,
        (ROI_DT[0], ROI_DT[1]),
        (ROI_DT[2], ROI_DT[3]),
        (0, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        "TRUC DONG-TAY",
        (ROI_DT[0], ROI_DT[1] - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 255),
        2
    )

    count_BN = 0
    count_DT = 0

    # ===== XỬ LÝ XE =====
    for box in results[0].boxes:

        if box.id is None:
            continue

        track_id = int(box.id.item())

        x1, y1, x2, y2 = box.xyxy[0]

        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)

        # ===== PHÁT HIỆN VƯỢT ĐÈN ĐỎ =====
        old_y = vehicle_positions.get(track_id)

        if old_y is not None:

            crossed_line = (
                old_y < STOP_LINE_Y
                and cy >= STOP_LINE_Y
            )

            if (
                LIGHT_STATE == "RED"
                and crossed_line
                and track_id not in violated_ids
            ):

                violated_ids.add(track_id)

                print(
                    f"🚨 XE {track_id} VƯỢT ĐÈN ĐỎ"
                )

                filename = (
                    f"violation_{track_id}_{int(time.time())}.jpg"
                )

                cv2.imwrite(filename, frame)

        vehicle_positions[track_id] = cy

        # ===== ĐẾM XE =====
        if (
            ROI_BN[0] < cx < ROI_BN[2]
            and ROI_BN[1] < cy < ROI_BN[3]
        ):
            count_BN += 1

            cv2.circle(
                annotated_frame,
                (cx, cy),
                6,
                (0, 0, 255),
                -1
            )

        elif (
            ROI_DT[0] < cx < ROI_DT[2]
            and ROI_DT[1] < cy < ROI_DT[3]
        ):
            count_DT += 1

            cv2.circle(
                annotated_frame,
                (cx, cy),
                6,
                (0, 255, 0),
                -1
            )

    # ===== THÔNG TIN HIỂN THỊ =====
    cv2.putText(
        annotated_frame,
        f"B-N: {count_BN} | D-T: {count_DT}",
        (20, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"Violations: {len(violated_ids)}",
        (20, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 0, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"LIGHT: {LIGHT_STATE}",
        (20, 150),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 255),
        2
    )

    cv2.imshow(
        "AI Traffic Camera",
        annotated_frame
    )

    # ===== GỬI DỮ LIỆU SERVER =====
    current_time = time.time()

    if current_time - last_send_time > 3:

        payload = {
            "intersection_id": INTERSECTION_ID,
            "count_BN": count_BN,
            "count_DT": count_DT
        }

        try:
            requests.post(
                SERVER_URL,
                json=payload,
                timeout=2
            )
        except Exception:
            pass

        last_send_time = current_time

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()