import Foundation

class WebSocketManager: ObservableObject {
    private var webSocketTask: URLSessionWebSocketTask?
    @Published var stockData: [String: [StockHistory]] = [:]
    var tickers: [String] = []
    var period: String = "1mo"
    
    init() {
    }
    
    func connect() {
        guard let url = URL(string: "ws://localhost:8000/ws") else { return }
        webSocketTask = URLSession.shared.webSocketTask(with: url)
        webSocketTask?.resume()
        
        sendTickers()
        receiveMessages()
    }
    
    func disconnect() {
        webSocketTask?.cancel(with: .normalClosure, reason: nil)
    }
    
    func sendTickers() {
        // Clear data for removed tickers
        DispatchQueue.main.async {
            self.stockData = self.stockData.filter { self.tickers.contains($0.key) }
        }
        
        let message: [String: Any] = ["tickers": tickers, "period": period]
        if let data = try? JSONSerialization.data(withJSONObject: message, options: []) {
            let text = String(data: data, encoding: .utf8) ?? ""
            webSocketTask?.send(.string(text)) { error in
                if let error = error {
                    print("WebSocket sending error: \(error)")
                }
            }
        }
    }
    
    func receiveMessages() {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .failure(let error):
                print("WebSocket receiving error: \(error)")
            case .success(let message):
                switch message {
                case .string(let text):
                    self?.handleMessage(text)
                case .data(let data):
                    if let text = String(data: data, encoding: .utf8) {
                        self?.handleMessage(text)
                    }
                @unknown default:
                    print("Unknown message format received")
                }
                // Continue to receive messages
                self?.receiveMessages()
            }
        }
    }
    
    func handleMessage(_ text: String) {
        if let data = text.data(using: .utf8) {
            do {
                let update = try JSONDecoder().decode(UpdateMessage.self, from: data)
                DispatchQueue.main.async {
                    // Merge the new data with existing stockData
                    for (ticker, histories) in update.data {
                        self.stockData[ticker] = histories
                    }
                }
            } catch {
                print("Decoding error: \(error)")
            }
        }
    }
}
