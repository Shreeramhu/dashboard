import os
import ssl
import threading
import asyncio
import random
import traceback
from flask import Flask
import websockets
import paho.mqtt.client as mqtt

# ================================
# CONFIGURATION
# ================================
IOT_ENDPOINT = "a1gvk11scaxlba-ats.iot.eu-north-1.amazonaws.com"
TOPIC = "text/sensor/data"

# Environment variables for certificate paths
CA_PATH = os.getenv("CA_PATH", "./AmazonRootCA1.pem")
CERT_PATH = os.getenv("CERT_PATH", "./device-certificate.pem.crt")
KEY_PATH = os.getenv("KEY_PATH", "./private.pem.key")

# Render’s default PORT (for Flask health check)
HTTP_PORT = int(os.getenv("PORT", 10000))
# WebSocket will use a separate internal port
WS_PORT = HTTP_PORT + 1

# MODE: "test" = fake data, "iot" = real AWS IoT data
MODE = os.getenv("MODE", "test").lower()

connected_ws = set()

# ================================
# LOGGING
# ================================
def log(*args):
    print("[SERVER]", *args, flush=True)

# ================================
# FLASK APP (Health Check)
# ================================
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Flask & WebSocket Server Active", 200

# ================================
# MQTT HANDLERS (IoT Mode)
# ================================
def random_client_id():
    return f"Client-{random.randint(1000, 9999)}"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log("✅ Connected to AWS IoT")
        client.subscribe(TOPIC)
        log(f"📡 Subscribed to topic: {TOPIC}")
    else:
        log("❌ Failed to connect to AWS IoT. RC =", rc)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8", errors="ignore")
        loop = userdata["loop"]
        asyncio.run_coroutine_threadsafe(broadcast(payload), loop)
    except Exception as e:
        log("Error processing MQTT message:", e)

def start_mqtt(loop):
    try:
        client = mqtt.Client(client_id=random_client_id(), userdata={"loop": loop})
        client.on_connect = on_connect
        client.on_message = on_message

        client.tls_set(
            CA_PATH,
            certfile=CERT_PATH,
            keyfile=KEY_PATH,
            tls_version=ssl.PROTOCOL_TLSv1_2,
        )

        log("🔐 Connecting to AWS IoT...")
        client.connect(IOT_ENDPOINT, 8883)
        client.loop_forever()
    except Exception as e:
        log("❌ MQTT Error:", e)
        traceback.print_exc()

# ================================
# WEBSOCKET HANDLERS
# ================================
async def broadcast(message):
    """Send a message to all connected WebSocket clients."""
    for ws in list(connected_ws):
        try:
            await ws.send(message)
        except Exception:
            connected_ws.discard(ws)

async def ws_handler(websocket):
    """Handles each WebSocket client."""
    connected_ws.add(websocket)
    log(f"🌐 WebSocket connected ({len(connected_ws)} clients)")
    try:
        while True:
            await asyncio.sleep(5)
    except Exception:
        pass
    finally:
        connected_ws.discard(websocket)
        log(f"❌ WebSocket disconnected ({len(connected_ws)} remaining)")

# ================================
# TEST MODE HANDLER
# ================================
async def ws_test_handler(websocket):
    """Sends fake data for testing without AWS IoT."""
    connected_ws.add(websocket)
    log("🧪 Test client connected")
    try:
        while True:
            data = {
                "Moisture": random.uniform(20, 80),
                "Viscosity": random.uniform(100, 300),
                "AirBubble": random.uniform(0, 10)
            }
            await websocket.send(str(data))
            await asyncio.sleep(2)
    except websockets.exceptions.ConnectionClosed:
        log("🧪 Test client disconnected")
    finally:
        connected_ws.discard(websocket)

# ================================
# ASYNC SERVER STARTER
# ================================
async def start_ws(loop):
    """Start WebSocket server on Render internal port."""
    handler = ws_test_handler if MODE == "test" else ws_handler
    async with websockets.serve(handler, "0.0.0.0", WS_PORT):
        log(f"✅ WebSocket running on ws://0.0.0.0:{WS_PORT} (MODE={MODE.upper()})")
        await asyncio.Future()

def run_ws():
    """Run WebSocket in separate thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    if MODE == "iot":
        mqtt_thread = threading.Thread(target=start_mqtt, args=(loop,), daemon=True)
        mqtt_thread.start()
        log("🚀 MQTT Thread started (IoT mode)")
    loop.run_until_complete(start_ws(loop))

# ================================
# MAIN ENTRY POINT
# ================================
if __name__ == "__main__":
    log(f"🚀 Starting Flask (HTTP:{HTTP_PORT}) + WebSocket (WS:{WS_PORT}) in {MODE.upper()} mode")

    # Run WebSocket on a separate thread
    threading.Thread(target=run_ws, daemon=True).start()

    # Start Flask (for Render health checks)
    app.run(host="0.0.0.0", port=HTTP_PORT)
