import os, random, json, asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Viscosity WebSocket Server")

MODE = os.getenv("MODE", "test").lower()
PORT = int(os.getenv("PORT", 10000))
connected_clients = set()

@app.get("/")
async def home():
    return JSONResponse({"status": "✅ FastAPI running", "mode": MODE})

@app.get("/favicon.ico")
async def favicon():
    return JSONResponse({}, status_code=204)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    print(f"🌐 Client connected ({len(connected_clients)})")
    try:
        while True:
            fake = {
                "Moisture": random.randint(30, 90),
                "Viscosity": random.randint(150, 350),
                "AirBubble": random.randint(0, 10),
            }
            await websocket.send_text(json.dumps(fake))
            await asyncio.sleep(2)
    except:
        connected_clients.discard(websocket)
        print("❌ Client disconnected")

if __name__ == "__main__":
    print(f"[SERVER] 🚀 Running on 0.0.0.0:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
