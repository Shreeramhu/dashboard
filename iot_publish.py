import pandas as pd
import time
import json
import ssl
import paho.mqtt.client as mqtt

# ===== AWS IoT Core Config =====
ENDPOINT = "a1gvk11scaxlba-ats.iot.eu-north-1.amazonaws.com"
PORT = 8883
THING_NAME = "text_ind"
TOPIC = "text/sensor/data"  # your topic

CA_PATH = r"C:\Users\SSE\team\AmazonRootCA1 (3).pem"
CERT_PATH = r"C:\Users\SSE\team\device-certificate.pem.crt"
KEY_PATH = r"C:\Users\SSE\team\private.pem.key"

# ===== Read CSV =====
df = pd.read_csv(r"C:\Users\SSE\team\sensor_data_shuffled1.csv", encoding="utf-8-sig")

# ===== MQTT Client =====
client = mqtt.Client(client_id=THING_NAME)
client.tls_set(
    ca_certs=CA_PATH,
    certfile=CERT_PATH,
    keyfile=KEY_PATH,
    tls_version=ssl.PROTOCOL_TLSv1_2
)
client.connect(ENDPOINT, PORT, keepalive=60)
client.loop_start()

# ===== Publish row-by-row =====
for _, row in df.iterrows():
    message = {

        "Moisture": float(row["Moisture"]),
        "MoistureValue": float(row["MoistureValue"]),
        "AirBubble": float(row["Air Bubble"]),
        "AirBubbleValue": float(row["AirBubbleValue"]),
        "Viscosity": float(row["Viscosity"]),
        "ViscosityValue": float(row["ViscosityValue"]),
        "Valve": str(row["Valve"]), 
        "Communication": str(row["Communication"]), 
        

        "PowerSurge": str(row["PowerSurge"]),
        "Description": str(row["Description"]),
        "Alert": str(row["Alert"]),
        "SystemResult": str(row["SystemResult"])
        
    }


    message = json.dumps(message)

    # QoS 1 ensures at-least-once delivery
    client.publish(TOPIC, message, qos=1)
    print(f"Published: {message}")
    time.sleep(2)  # simulate live streaming

client.loop_stop()
client.disconnect()
