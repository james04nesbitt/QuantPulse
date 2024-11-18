import SwiftUI

struct WatchlistView: View {
    @EnvironmentObject var webSocketManager: WebSocketManager
    @State private var gainPeriod: GainPeriod = .daily
    @State private var totalMoney: Double = 10000.0 // Example total balance
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Total Balance
                Text("Total Balance")
                    .font(.headline)
                    .padding(.top)
                Text("$\(totalMoney, specifier: "%.2f")")
                    .font(.system(size: 34, weight: .bold))
                    .padding(.bottom)
                
                // Gain Period Picker
                Picker("Gain Period", selection: $gainPeriod) {
                    ForEach(GainPeriod.allCases, id: \.self) { period in
                        Text(period.rawValue).tag(period)
                    }
                }
                .pickerStyle(SegmentedPickerStyle())
                .padding(.horizontal)
                
                // Watchlist
                List {
                    ForEach(webSocketManager.tickers, id: \.self) { ticker in
                        if let stockHistories = webSocketManager.stockData[ticker],
                           let latestData = stockHistories.last {
                            NavigationLink(destination: StockDetailView(ticker: ticker, stockHistory: stockHistories)) {
                                StockRowView(ticker: ticker, latestData: latestData, gainPeriod: gainPeriod)
                            }
                            .listRowBackground(Color.clear)
                        }
                    }
                }
                .listStyle(PlainListStyle())
                
                // Add More Stocks Button
                Button(action: {
                    // Present an alert or modal to add a new ticker
                    // For example purposes, we'll add a hardcoded ticker
                    let newTicker = "MSFT"
                    if !webSocketManager.tickers.contains(newTicker) {
                        webSocketManager.tickers.append(newTicker)
                        webSocketManager.sendTickers()
                    }
                }) {
                    Text("Add More Stocks")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(12)
                        .padding(.horizontal)
                        .padding(.bottom, 10)
                }
            }
            .navigationBarHidden(true)
            .background(Color(.systemGroupedBackground).edgesIgnoringSafeArea(.all))
        }
    }
}
