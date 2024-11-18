from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import yfinance as yf
import asyncio
import json

app = FastAPI()

# In-memory storage for connected clients
clients = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        data = await websocket.receive_text()
        message = json.loads(data)
        tickers = message.get("tickers", [])
        period = message.get("period", "1mo")
        print(f"Received tickers: {tickers}")

        # Start sending updates
        while True:
            updates = {}
            for ticker in tickers:
                stock = yf.Ticker(ticker)
                hist = stock.history(period=period)
                # Convert DataFrame to JSON serializable format
                hist_json = hist.reset_index().to_dict(orient='records')
                updates[ticker] = hist_json

            # Send updates to the client
            await websocket.send_text(json.dumps({"type": "update", "data": updates}))
            await asyncio.sleep(60)  # Wait before next update (e.g., every 60 seconds)

    except WebSocketDisconnect:
        print("Client disconnected")
        clients.remove(websocket)
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close()
        clients.remove(websocket)
