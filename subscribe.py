# subscribe.py
import os, random, json, asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
import uvicorn

# =======================
# CONFIGURATION
# =======================
MODE = os.getenv("MODE", "test").lower()  # "test" or "iot"
PORT = int(os.getenv("PORT", 10000))

app = FastAPI(title="Viscosity WebSocket Server")

# Keep track of connected clients
connected_clients = set()

# =======================
# HTTP ROUTE (Health Check)
# =======================
@app.get("/")
async def home():
    return JSONResponse(
        {
            "status": "✅ FastAPI WebSocket server running",
            "mode": MODE,
            "clients_connected": len(connected_clients),
        }
    )

# =======================
# WEBSOCKET ROUTE
# =======================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    print(f"🌐 Client connected ({len(connected_clients)})")

    try:
        if MODE == "test":
            # Send random simulated data every 2 seconds
            while True:
                fake_data = {
                    "Moisture": random.randint(30, 90),
                    "Viscosity": random.randint(150, 350),
                    "AirBubble": random.randint(0, 10),
                }
                await websocket.send_text(json.dumps(fake_data))
                await asyncio.sleep(2)
        else:
            # Placeholder for AWS IoT integration
            # You can replace this section with MQTT logic
            while True:
                await asyncio.sleep(1)

    except Exception as e:
        print(f"❌ Client disconnected: {e}")

    finally:
        connected_clients.discard(websocket)
        print(f"🧹 Client removed. Active clients: {len(connected_clients)}")

# =======================
# MAIN ENTRY POINT
# =======================
if __name__ == "__main__":
    print(f"[SERVER] 🚀 Starting FastAPI WebSocket server on port {PORT} (MODE={MODE.upper()})")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
