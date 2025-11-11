import os
import ssl
import asyncio
import threading
import random
import traceback
import paho.mqtt.client as mqtt
import websockets

# ===============================
# CONFIGURATION
# ===============================
IOT_ENDPOINT = "a1gvk11scaxlba-ats.iot.eu-north-1.amazonaws.com"
TOPIC = "text/sensor/data"

CA_PATH = os.getenv("CA_PATH", "./AmazonRootCA1.pem")
CERT_PATH = os.getenv("CERT_PATH", "./device-certificate.pem.crt")
KEY_PATH = os.getenv("KEY_PATH", "./private.pem.key")

WS_PORT = int(os.getenv("PORT", 8765))
MODE = os.getenv("MODE", "iot").lower()  # 'iot' or 'test'

connected_ws = set()

def log(*args):
    print("[PROXY]", *args, flush=True)

def random_client_id():
    return f"Proxy-{random.randint(1000, 9999)}"

# ===============================
# TEST MODE (Hello from Render)
# ===============================
async def test_handler(websocket, path):
    """Simple test handler for Render deployment check."""
    log("Client connected (test mode)")
    try:
        while True:
            await websocket.send("Hello from Render!")  # Replace with real data later
            await asyncio.sleep(2)
    except websockets.exceptions.ConnectionClosed:
        log("Client disconnected")

async def start_test_server():
    """Start test WebSocket server."""
    async with websockets.serve(test_handler, "0.0.0.0", WS_PORT):
        log(f"✅ Test WebSocket running on ws://0.0.0.0:{WS_PORT}")
        await asyncio.Future()  # Keep running

# ===============================
# IOT MODE (AWS IoT → WebSocket)
# ===============================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log("✅ MQTT connected to AWS IoT!")
        client.subscribe(TOPIC)
        log(f"📡 Subscribed to topic: {TOPIC}")
    else:
        log(f"❌ MQTT connection failed. rc={rc}")

def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8", errors="ignore")
    loop = userdata["loop"]
    asyncio.run_coroutine_threadsafe(broadcast(payload), loop)

async def broadcast(message):
    for ws in list(connected_ws):
        try:
            await ws.send(message)
        except Exception:
            connected_ws.discard(ws)

async def ws_handler(websocket):
    connected_ws.add(websocket)
    log(f"🌐 WebSocket connected ({len(connected_ws)} total)")
    try:
        async for _ in websocket:
            pass
    except Exception:
        pass
    finally:
        connected_ws.discard(websocket)
        log("❌ WebSocket disconnected")

def start_mqtt(loop):
    """MQTT client runs in a background thread."""
    try:
        client = mqtt.Client(client_id=random_client_id(), userdata={"loop": loop})
        client.on_connect = on_connect
        client.on_message = on_message
        client.tls_set(CA_PATH, certfile=CERT_PATH, keyfile=KEY_PATH, tls_version=ssl.PROTOCOL_TLSv1_2)
        client.connect(IOT_ENDPOINT, port=8883)
        client.loop_forever()
    except Exception as e:
        log("❌ MQTT Error:", e)
        traceback.print_exc()

async def start_iot_server(loop):
    """Start WebSocket server for IoT mode."""
    ws_server = await websockets.serve(ws_handler, "0.0.0.0", WS_PORT)
    log(f"✅ IoT WebSocket running on ws://0.0.0.0:{WS_PORT}")
    await ws_server.wait_closed()

# ===============================
# MAIN ENTRY POINT
# ===============================
def main():
    log(f"🚀 Starting subscribe.py in MODE={MODE.upper()}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if MODE == "test":
        # Test mode: no MQTT, only "Hello from Render!"
        loop.run_until_complete(start_test_server())
    else:
        # IoT mode: AWS IoT + WebSocket bridge
        mqtt_thread = threading.Thread(target=start_mqtt, args=(loop,), daemon=True)
        mqtt_thread.start()
        log("📡 MQTT thread started")
        loop.run_until_complete(start_iot_server(loop))
        loop.run_forever()

if __name__ == "__main__":
    main()
