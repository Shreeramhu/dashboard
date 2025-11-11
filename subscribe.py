# subscribe.py
import os, random, json, asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
import uvicorn

MODE = os.getenv("MODE", "test").lower()
PORT = int(os.getenv("PORT", 10000))

app = FastAPI(title="Viscosity WebSocket Server")

connected_clients = set()

@app.get("/")
async def home():
    return JSONResponse({"status": "✅ FastAPI WebSocket server running", "mode": MODE})

@app.get("/favicon.ico")
async def favicon():
    return JSONResponse({}, status_code=204)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    print(f"🌐 Client connected ({len(connected_clients)})")

    try:
        if MODE == "test":
            while True:
                fake_data = {
                    "Moisture": random.randint(30, 90),
                    "Viscosity": random.randint(150, 350),
                    "AirBubble": random.randint(0, 10)
                }
                await websocket.send_text(json.dumps(fake_data))
                await asyncio.sleep(2)
        else:
            while True:
                await asyncio.sleep(1)
    except Exception as e:
        print(f"❌ Client disconnected: {e}")
    finally:
        connected_clients.discard(websocket)

if __name__ == "__main__":
    print(f"[SERVER] 🚀 Starting FastAPI WebSocket server on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
