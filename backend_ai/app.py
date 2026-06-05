import time
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS
import paho.mqtt.client as mqtt

app = Flask(__name__)
CORS(app)

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
TOPIC_STATUS = "doan_its_vip/trangthai"
TOPIC_CONTROL = "doan_its_vip/dieukhien"

system_state = {
    "hardware_status": "Đang chờ kết nối với mạch...",
    "count_BN": 0,
    "count_DT": 0,
    "ai_decision": "Bình thường"
}

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Đã kết nối với broker EMQX thành công!")
    client.subscribe(TOPIC_STATUS)

def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    print(f"[MẠCH BÁO CÁO]: {payload}")
    system_state["hardware_status"] = payload

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def start_mqtt():
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_forever()

@app.route('/api/update_traffic', methods=['POST'])
def update_traffic():
    data = request.json
    count_BN = data.get('count_BN', 0)
    count_DT = data.get('count_DT', 0)
    
    system_state["count_BN"] = count_BN
    system_state["count_DT"] = count_DT

    hw_status = system_state["hardware_status"]

    # LOGIC 1: Vắng xe -> Cắt đèn xanh
    if count_BN == 0 and "Truc B-N: Xanh" in hw_status:
        mqtt_client.publish(TOPIC_CONTROL, "VANG_XE_BN")
        system_state["ai_decision"] = "Bắc-Nam vắng -> Cắt pha xanh Bắc-Nam!"
        print("[AI] Gửi lệnh VANG_XE_BN")
        
    elif count_DT == 0 and "Truc D-T: Xanh" in hw_status:
        mqtt_client.publish(TOPIC_CONTROL, "VANG_XE_DT")
        system_state["ai_decision"] = "Đông-Tây vắng -> Cắt pha xanh Đông-Tây!"
        print("[AI] Gửi lệnh VANG_XE_DT")

    # LOGIC 2: Ùn tắc -> Kéo dài đèn xanh (Mốc 15 xe)
    elif count_BN >= 15 and "Truc B-N: Xanh" in hw_status:
        mqtt_client.publish(TOPIC_CONTROL, "KEO_DAI_BN")
        system_state["ai_decision"] = "Bắc-Nam ùn tắc -> Tăng thời gian đèn!"
        print("[AI] Gửi lệnh KEO_DAI_BN")
        
    elif count_DT >= 15 and "Truc D-T: Xanh" in hw_status:
        mqtt_client.publish(TOPIC_CONTROL, "KEO_DAI_DT")
        system_state["ai_decision"] = "Đông-Tây ùn tắc -> Tăng thời gian đèn!"
        print("[AI] Gửi lệnh KEO_DAI_DT")
        
    else:
        system_state["ai_decision"] = "Điều phối bình thường"

    return jsonify({"status": "success"})

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_data():
    return jsonify(system_state)

@app.route('/api/emergency', methods=['POST'])
def trigger_emergency():
    mqtt_client.publish(TOPIC_CONTROL, "KHAN_CAP")
    system_state["ai_decision"] = "CẢNH BÁO: Kích hoạt xe ưu tiên!"
    return jsonify({"status": "Đã gửi lệnh khẩn cấp"})

if __name__ == '__main__':
    threading.Thread(target=start_mqtt, daemon=True).start()
    print("🚀 Server đang khởi động tại http://127.0.0.1:5000")
    app.run(debug=True, port=5000, use_reloader=False)