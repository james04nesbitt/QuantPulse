import SwiftUI

struct StockDetailView: View {
    let ticker: String
    let stockHistory: [StockHistory]
    @EnvironmentObject var webSocketManager: WebSocketManager
    @Environment(\.presentationMode) var presentationMode

    var body: some View {
        VStack {
            Text(ticker)
                .font(.largeTitle)
                .padding()
            Text("Detailed information will go here.")
                .font(.body)
                .padding()
            
            // Remove Stock Button
            Button(action: {
                removeTicker()
            }) {
                Text("Remove from Watchlist")
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.red)
                    .foregroundColor(.white)
                    .cornerRadius(12)
                    .padding()
            }
            Spacer()
        }
        .navigationTitle(ticker)
    }
    
    // Helper Function
    func removeTicker() {
        if let index = webSocketManager.tickers.firstIndex(of: ticker) {
            webSocketManager.tickers.remove(at: index)
            webSocketManager.sendTickers()
            presentationMode.wrappedValue.dismiss()
        }
    }
}
