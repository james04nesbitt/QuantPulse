# main.py

import asyncio
import json
from typing import List, Dict

import yfinance as yf
import tensorflow as tf
import numpy as np
import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google.cloud import pubsub_v1
from pydantic import BaseModel

# Initialize FastAPI
app = FastAPI()

# Initialize Pub/Sub Lite Publisher and Subscriber
PROJECT_ID = "sven-smeagol-66"  # Your GCP Project ID

publisher = pubsub_v1.PublisherClient(
    client_options={"api_endpoint": "us-central1-pubsublite.googleapis.com:443"}
)
subscriber = pubsub_v1.SubscriberClient(
    client_options={"api_endpoint": "us-central1-pubsublite.googleapis.com:443"}
)

# Define topics and subscriptions
CALC_TASK_TOPIC = "stock-calculation-tasks"
CALC_RESULT_SUBSCRIPTION = "fastapi-result-subscription"

calc_task_topic_path = publisher.topic_path(PROJECT_ID, CALC_TASK_TOPIC)
calc_result_subscription_path = subscriber.subscription_path(PROJECT_ID, CALC_RESULT_SUBSCRIPTION)

# Load the ML model
model = tf.keras.models.load_model("model.h5")  # Ensure model.h5 is in the /fastapi directory

class StockHistory(BaseModel):
    Date: str
    Open: float
    High: float
    Low: float
    Close: float
    Volume: int
    SMA: List[float] = []
    RSI: List[float] = []
    Prediction: List[float] = []
    OptionChain: Dict = {}
    SelectedOptions: Dict = {}

class UpdateMessage(BaseModel):
    type: str
    data: Dict[str, List[StockHistory]]  # Ticker: [StockHistory]

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.data_store: Dict[str, Dict] = {}  # To store calculations, predictions, and options

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print("WebSocket connection established.")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print("WebSocket connection closed.")

    async def send_data(self, data: Dict):
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
    future = publisher.publish(calc_task_topic_path, data=data)
    message_id = future.result()
    print(f"Published calculation task for {ticker} with message ID: {message_id}")

def calculate_sma(prices: List[float], period: int) -> List[float]:
    sma = pd.Series(prices).rolling(window=period).mean().tolist()
    return sma

def calculate_rsi(prices: List[float], period: int) -> List[float]:
    delta = pd.Series(prices).diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    average_gain = gain.rolling(window=period).mean()
    average_loss = loss.rolling(window=period).mean()
    rs = average_gain / average_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.tolist()

def run_lstm_model(prices: List[float], period: int) -> List[float]:
    # Preprocess data
    df = pd.DataFrame(prices, columns=["Close"])
    df['Close'] = (df['Close'] - df['Close'].mean()) / df['Close'].std()
    data = df.values
    X = []
    for i in range(len(data) - period):
        X.append(data[i:i+period])
    X = np.array(X)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))
    # Make predictions
    predictions = model.predict(X)
    return predictions.flatten().tolist()

def get_option_chain(ticker: str) -> Dict:
    stock = yf.Ticker(ticker)
    option_dates = stock.options
    if not option_dates:
        return {}
    # Get the nearest expiration date
    nearest_expiry = option_dates[0]
    option_chain = stock.option_chain(nearest_expiry)
    calls = option_chain.calls.to_dict(orient='records')
    puts = option_chain.puts.to_dict(orient='records')
    return {"calls": calls, "puts": puts}

def select_options(ticker: str, prediction: float, option_chain: Dict) -> Dict:
    current_price = prediction  # Simplified; use the latest actual price in practice
    calls = option_chain.get('calls', [])
    puts = option_chain.get('puts', [])
    # Select calls with strike > current_price
    selected_calls = [call for call in calls if call['strike'] > current_price]
    # Select puts with strike < current_price
    selected_puts = [put for put in puts if put['strike'] < current_price]
    # Sort and select top options based on volume
    selected_calls = sorted(selected_calls, key=lambda x: x.get('volume', 0), reverse=True)[:5]
    selected_puts = sorted(selected_puts, key=lambda x: x.get('volume', 0), reverse=True)[:5]
    return {"selected_calls": selected_calls, "selected_puts": selected_puts}

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(subscribe_to_calculation_results())

async def subscribe_to_calculation_results():
    def callback(message):
        try:
            result = json.loads(message.data.decode("utf-8"))
            ticker = result["ticker"]
            sma = result.get("SMA", [])
            rsi = result.get("RSI", [])
            # Update the data store
            if ticker not in manager.data_store:
                manager.data_store[ticker] = {}
            manager.data_store[ticker]["SMA"] = sma
            manager.data_store[ticker]["RSI"] = rsi
            # Check if we have other data to send
            if all(k in manager.data_store[ticker] for k in ["prices", "Prediction", "OptionChain", "SelectedOptions"]):
                asyncio.create_task(send_update(ticker))
            message.ack()
        except Exception as e:
            print(f"Error processing calculation result message: {e}")
            message.nack()

    streaming_pull_future = subscriber.subscribe(calc_result_subscription_path, callback=callback)
    print(f"Listening for calculation results on {calc_result_subscription_path}..\n")

    try:
        streaming_pull_future.result()
    except Exception as e:
        print(f"Error in subscriber: {e}")
        streaming_pull_future.cancel()

async def send_update(ticker: str):
    data = manager.data_store.get(ticker, {})
    update = {
        ticker: [{
            "SMA": data.get("SMA", []),
            "RSI": data.get("RSI", []),
            "Prediction": data.get("Prediction", []),
            "OptionChain": data.get("OptionChain", {}),
            "SelectedOptions": data.get("SelectedOptions", {})
        }]
    }
    await manager.send_data(update)
    print(f"Sent update for {ticker}")

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
                dates = hist.index.strftime('%Y-%m-%d').tolist()
                # Store prices in data store
                if ticker not in manager.data_store:
                    manager.data_store[ticker] = {}
                manager.data_store[ticker]["prices"] = prices
                # Publish calculation task
                await publish_calculation_task(ticker, prices, period_days)
                # Calculate SMA and RSI directly (optional)
                sma = calculate_sma(prices, period_days)
                rsi = calculate_rsi(prices, period_days)
                manager.data_store[ticker]["SMA"] = sma
                manager.data_store[ticker]["RSI"] = rsi
                # Run LSTM model
                prediction = run_lstm_model(prices, period_days)
                manager.data_store[ticker]["Prediction"] = prediction
                # Get option chain
                option_chain = get_option_chain(ticker)
                manager.data_store[ticker]["OptionChain"] = option_chain
                # Select options
                latest_prediction = prediction[-1] if prediction else prices[-1]
                selected_options = select_options(ticker, latest_prediction, option_chain)
                manager.data_store[ticker]["SelectedOptions"] = selected_options
                # Send update
                await send_update(ticker)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)
