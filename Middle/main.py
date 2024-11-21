# main.py

import asyncio
import json
from typing import List, Dict

import yfinance as yf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google.cloud import pubsub_v1
from pydantic import BaseModel

# Initialize FastAPI
app = FastAPI()

PROJECT_ID = "sven-smeagol-66"  
TASK_TOPIC = "stock-calculation-tasks"
RESULT_SUBSCRIPTION = "fastapi-result-subscription"

publisher = pubsub_v1.PublisherClient()
task_topic_path = publisher.topic_path(PROJECT_ID, TASK_TOPIC)

subscriber = pubsub_v1.SubscriberClient()
result_subscription_path = subscriber.subscription_path(PROJECT_ID, RESULT_SUBSCRIPTION)


class StockHistory(BaseModel):
    Date: str
    Open: float
    High: float
    Low: float
    Close: float
    Volume: int
    SMA: List[float] = []
    RSI: List[float] = []


class UpdateMessage(BaseModel):
    type: str
    data: Dict[str, List[StockHistory]]  # Ticker: [StockHistory]


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print("WebSocket connection established.")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print("WebSocket connection closed.")

    async def send_data(self, data: Dict[str, List[StockHistory]]):
        for connection in self.active_connections:
            await connection.send_json({"type": "update", "data": data})


manager = ConnectionManager()


async def publish_calculation_task(ticker: str, prices: List[float], period: int):
    task = {
        "ticker": ticker,
        "prices": prices,
        "period": period
    }
    data = json.dumps(task).encode("utf-8")
    future = publisher.publish(task_topic_path, data)
    message_id = future.result()
    print(f"Published task for {ticker} with message ID: {message_id}")


async def subscribe_to_results():
    def callback(message):
        try:
            result = json.loads(message.data.decode("utf-8"))
            update = {}
            for ticker, indicators in result["data"].items():
                stock_histories = []
                for item in indicators:
                    stock_history = StockHistory(
                        Date=item["Date"],
                        Open=item["Open"],
                        High=item["High"],
                        Low=item["Low"],
                        Close=item["Close"],
                        Volume=item["Volume"],
                        SMA=item.get("SMA", []),
                        RSI=item.get("RSI", [])
                    )
                    stock_histories.append(stock_history)
                update[ticker] = stock_histories
            asyncio.create_task(manager.send_data(update))
            print(f"Received and sent update for tickers: {list(update.keys())}")
            message.ack()
        except Exception as e:
            print(f"Error processing message: {e}")
            message.nack()

    streaming_pull_future = subscriber.subscribe(result_subscription_path, callback=callback)
    print(f"Listening for messages on {result_subscription_path}..\n")

    try:
        await streaming_pull_future
    except asyncio.CancelledError:
        streaming_pull_future.cancel()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(subscribe_to_results())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            tickers = message.get("tickers", [])
            period = message.get("period", "1mo")
            period_mapping = {
                "1d": 1,
                "1mo": 30,
                "3mo": 90,
                "6mo": 180,
                "1y": 365
            }
            period_days = period_mapping.get(period, 30)  # Default to 30 days

            print(f"Received tickers: {tickers} with period: {period}")

            for ticker in tickers:
                stock = yf.Ticker(ticker)
                hist = stock.history(period=period)
                if hist.empty:
                    print(f"No data found for ticker: {ticker}")
                    continue
                # Extract closing prices
                prices = hist['Close'].tolist()
                await publish_calculation_task(ticker, prices, period_days)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)
