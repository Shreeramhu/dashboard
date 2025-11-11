import os, ssl, asyncio, random, threading, traceback
from flask import Flask, Response, request
import paho.mqtt.client as mqtt
import websockets

# =========================
# CONFIGURATION
# =========================
IOT_ENDPOINT = "a1gvk11scaxlba-ats.iot.eu-north-1.amazonaws.com"
TOPIC = "text/sensor/data"
CA_PATH = os.getenv("CA_PATH", "./AmazonRootCA1.pem")
CERT_PATH = os.getenv("CERT_PATH", "./device-certificate.pem.crt")
KEY_PATH = os.getenv("KEY_PATH", "./private.pem.key")
PORT = int(os.getenv("PORT", 10000))
MODE = os.getenv("MODE", "test").lower()

app = Flask(__name__)
connected_ws = set()

# =========================
# HEALTH CHECK ENDPOINT
# =========================
@app.route("/")
def home():
    return "✅ Flask + WebSocket server running", 200

# =========================
# LOGGING
# =========================
def log(*args):
    print("[SERVER]", *args, flush=True)

# =========================
# MQTT → AWS IoT
# =========================
def random_client_id():
    return f"Client-{random.randint(1000,9999)}"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log("✅ MQTT connected to AWS IoT")
        client.subscribe(TOPIC)
    else:
        log("❌ MQTT connect failed, rc=", rc)

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
        log("MQTT ERROR:", e)
        traceback.print_exc()

# =========================
# WEBSOCKET IMPLEMENTATION
# =========================
async def broadcast(message):
    for ws in list(connected_ws):
        try:
            await ws.send(message)
        except:
            connected_ws.discard(ws)

async def ws_handler(websocket):
    connected_ws.add(websocket)
    log(f"🌐 WebSocket connected ({len(connected_ws)} clients)")
    try:
        if MODE == "test":
            while True:
                fake = {
                    "Moisture": random.randint(30, 90),
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
        log("❌ WebSocket disconnected")

# =========================
# RUN EVERYTHING
# =========================
async def run_ws(loop):
    """Run WebSocket server on a background task inside Flask."""
    async with websockets.serve(ws_handler, "0.0.0.0", PORT + 1):
        log(f"✅ WebSocket active internally on ws://0.0.0.0:{PORT+1}")
        await asyncio.Future()

def start_async():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    if MODE == "iot":
        threading.Thread(target=start_mqtt, args=(loop,), daemon=True).start()
    loop.run_until_complete(run_ws(loop))

if __name__ == "__main__":
    log(f"🚀 Starting Flask (PORT={PORT}) + WebSocket (PORT={PORT+1}) mode={MODE.upper()}")
    threading.Thread(target=start_async, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, use_reloader=False)
