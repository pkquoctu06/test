import traci
import requests
import time
import paho.mqtt.client as mqtt
import threading

# ===== CẤU HÌNH KẾT NỐI =====
SERVER_URL = "http://127.0.0.1:5000/api/update_traffic"
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
TOPIC_STATUS = "doan_its_vip/trangthai"

# Biến toàn cục lưu pha đèn hiện tại (-1 là chế độ khẩn cấp toàn bộ Đỏ)
current_phase = 0 
is_emergency = False

# ===== 1. LẮNG NGHE MẠCH ESP32 QUA MQTT =====
def on_connect(client, userdata, flags, rc):
    print("[MQTT] Đã kết nối! Đang nghe trạng thái từ mạch ESP32...")
    client.subscribe(TOPIC_STATUS)

def on_message(client, userdata, msg):
    global current_phase, is_emergency
    payload = msg.payload.decode("utf-8")
    
    # Phân tích phản hồi từ mạch để đổi pha đèn SUMO
    if "KHAN_CAP" in payload or "XE UU TIEN" in payload or "ALL RED" in payload:
        is_emergency = True
    else:
        is_emergency = False
        if "Truc B-N: Xanh" in payload:
            current_phase = 0
        elif "Truc B-N: Vang" in payload:
            current_phase = 1
        elif "Truc D-T: Xanh" in payload:
            current_phase = 2
        elif "Truc D-T: Vang" in payload:
            current_phase = 3

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def start_mqtt():
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_forever()

threading.Thread(target=start_mqtt, daemon=True).start()

# ===== 2. KHỞI ĐỘNG SUMO & ĐỒNG BỘ =====
print("🚀 Đang khởi động mô hình Giao thông thông minh...")
traci.start(["sumo-gui", "-c", "nga_tu.sumocfg"])

last_send_time = time.time()

while traci.simulation.getMinExpectedNumber() > 0:
    # Cập nhật màu đèn của SUMO
    # Cập nhật màu đèn của SUMO
    try:
        if is_emergency:
            # Ép đèn đỏ toàn bộ (tạo ra program tạm thời 1 pha)
            traci.trafficlight.setRedYellowGreenState("J1", "rrrrrrrrrrrr")
        else:
            # KHÔI PHỤC LẠI CHƯƠNG TRÌNH ĐÈN GỐC TRƯỚC KHI CHUYỂN PHA
            traci.trafficlight.setProgram("J1", "0")
            
            # Gán pha đèn (0, 1, 2, 3) giống hệt mạch Arduino
            traci.trafficlight.setPhase("J1", current_phase)
    except Exception as e:
        print(f"Lỗi đổi đèn: {e}")

    traci.simulationStep()
    current_time = time.time()
    
    # Mỗi 3 giây đếm xe và gửi lên Server
    if current_time - last_send_time > 3:
        # Tổng xe Trục Bắc-Nam (Lấy đường E0 đâm xuống + đường -E1 đâm lên)
        xe_bn = traci.edge.getLastStepVehicleNumber("E0") + traci.edge.getLastStepVehicleNumber("-E1")
        
        # Tổng xe Trục Đông-Tây (Lấy đường -E2 đâm sang + đường -E3 đâm sang)
        xe_dt = traci.edge.getLastStepVehicleNumber("-E2") + traci.edge.getLastStepVehicleNumber("-E3")
        
        payload = {
            "intersection_id": "J01",
            "count_BN": xe_bn,
            "count_DT": xe_dt
        }
        
        try:
            requests.post(SERVER_URL, json=payload, timeout=2)
            print(f"📊 Đã gửi Server -> Bắc-Nam: {xe_bn} xe | Đông-Tây: {xe_dt} xe")
        except Exception:
            pass
            
        last_send_time = current_time

    time.sleep(0.1)

traci.close()