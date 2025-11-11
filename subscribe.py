import os
import ssl
import asyncio
import threading
import random
import traceback
from flask import Flask, Response
from websockets.server import serve
import paho.mqtt.client as mqtt

# ============================
# CONFIGURATION
# ============================
IOT_ENDPOINT = "a1gvk11scaxlba-ats.iot.eu-north-1.amazonaws.com"
TOPIC = "text/sensor/data"

CA_PATH = os.getenv("CA_PATH", "./AmazonRootCA1.pem")
CERT_PATH = os.getenv("CERT_PATH", "./device-certificate.pem.crt")
KEY_PATH = os.getenv("KEY_PATH", "./private.pem.key")
MODE = os.getenv("MODE", "test").lower()
PORT = int(os.getenv("PORT", 10000))

connected_ws = set()

# ============================
# FLASK APP (Health + WebSocket)
# ============================
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Flask + WebSocket Server is running.", 200

# ============================
# LOGGING
# ============================
def log(*args):
    print("[SERVER]", *args, flush=True)

# ============================
# MQTT (AWS IoT)
# ============================
def random_client_id():
    return f"Client-{random.randint(1000,9999)}"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log("✅ Connected to AWS IoT")
        client.subscribe(TOPIC)
    else:
        log("❌ MQTT connect failed:", rc)

def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8", errors="ignore")
    loop = userdata["loop"]
    asyncio.run_coroutine_threadsafe(broadcast(payload), loop)

def start_mqtt(loop):
    try:
        client = mqtt.Client(client_id=random_client_id(), userdata={"loop": loop})
        client.on_connect = on_connect
        client.on_message = on_message
        client.tls_set(CA_PATH, certfile=CERT_PATH, keyfile=KEY_PATH, tls_version=ssl.PROTOCOL_TLSv1_2)
        log("🔐 Connecting to AWS IoT...")
        client.connect(IOT_ENDPOINT, 8883)
        client.loop_forever()
    except Exception as e:
        log("MQTT Error:", e)
        traceback.print_exc()

# ============================
# WEBSOCKET HANDLER
# ============================
async def broadcast(message):
    for ws in list(connected_ws):
        try:
            await ws.send(message)
        except:
            connected_ws.discard(ws)

async def ws_handler(websocket):
    connected_ws.add(websocket)
    log(f"🌐 WebSocket client connected ({len(connected_ws)})")
    try:
        if MODE == "test":
            while True:
                fake = {
                    "Moisture": random.randint(20, 90),
                    "Viscosity": random.randint(150, 350),
                    "AirBubble": random.randint(0, 10)
                }
                await websocket.send(str(fake))
                await asyncio.sleep(2)
        else:
            async for _ in websocket:
                pass
    except:
        pass
    finally:
        connected_ws.discard(websocket)
        log("❌ WebSocket client disconnected")

# ============================
# COMBINED SERVER
# ============================
async def run_websocket_in_flask():
    """Attach WebSocket handler to Flask port (Render only exposes one)."""
    async with serve(ws_handler, "0.0.0.0", PORT):
        log(f"✅ WebSocket running on ws://0.0.0.0:{PORT}")
        await asyncio.Future()  # keep running forever

def start_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if MODE == "iot":
        mqtt_thread = threading.Thread(target=start_mqtt, args=(loop,), daemon=True)
        mqtt_thread.start()
        log("🚀 MQTT Thread started")

    loop.run_until_complete(run_websocket_in_flask())

# ============================
# MAIN
# ============================
if __name__ == "__main__":
    log(f"🚀 Starting unified Flask+WebSocket server (PORT={PORT}, MODE={MODE.upper()})")
    # Run Flask in a background thread (for HTTP health checks)
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=PORT, use_reloader=False), daemon=True).start()
    # Run WebSocket (same port)
    asyncio.run(run_websocket_in_flask())
