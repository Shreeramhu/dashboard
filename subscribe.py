import os, asyncio, json, random
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()
PORT = int(os.getenv("PORT", 10000))
MODE = os.getenv("MODE", "test")

@app.get("/")
async def root():
    return JSONResponse({"status": "ok", "mode": MODE})

@app.head("/")
async def head_root():
    return JSONResponse({}, status_code=200)

@app.get("/favicon.ico")
async def favicon():
    return JSONResponse({}, status_code=204)

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    print("🌐 Client connected")
    try:
        while True:
            data = {
                "Moisture": random.randint(30, 90),
                "Viscosity": random.randint(150, 350),
                "AirBubble": random.randint(0, 10)
            }
            await ws.send_text(json.dumps(data))
            await asyncio.sleep(2)
    except Exception as e:
        print(f"❌ Client disconnected: {e}")
    finally:
        await ws.close()

if __name__ == "__main__":
    print(f"[SERVER] 🚀 Running on 0.0.0.0:{PORT}")
    # The 'loop.run_forever()' ensures the process never exits
    uvicorn.run(app, host="0.0.0.0", port=PORT)
    while True:
        asyncio.sleep(3600)
