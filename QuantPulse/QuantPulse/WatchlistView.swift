import SwiftUI

struct WatchlistView: View {
    @EnvironmentObject var webSocketManager: WebSocketManager
    @State private var gainPeriod: GainPeriod = .daily
    @State private var totalMoney: Double = 10000.0 // Example total balance
    @State private var isAddingStock = false
    @State private var newTicker = ""

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
                        } else {
                            // Handle case where there's no data yet
                            Text("Loading \(ticker)...")
                        }
                    }
                }
                .listStyle(PlainListStyle())
                
                // Add More Stocks Section
                ZStack {
                    // Background
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color.blue)
                        .frame(height: 50)
                        .padding(.horizontal)
                        .padding(.bottom, 10)
                    
                    if isAddingStock {
                        // TextField styled to blend with the button
                        TextField("Enter Ticker", text: $newTicker, onCommit: {
                            addNewTicker()
                        })
                        .foregroundColor(.white)
                        .padding(.horizontal)
                        .frame(height: 50)
                        .autocapitalization(.allCharacters)
                        .disableAutocorrection(true)
                    } else {
                        // Button Text
                        Text("Add More Stocks")
                            .foregroundColor(.white)
                            .onTapGesture {
                                isAddingStock = true
                            }
                    }
                }
                .contentShape(Rectangle()) // Makes the entire area tappable
                .onTapGesture {
                    if !isAddingStock {
                        isAddingStock = true
                    }
                }
            }
            .navigationBarHidden(true)
            .background(Color(.systemGroupedBackground).edgesIgnoringSafeArea(.all))
        }
    }
    
    // Helper Functions
    func addNewTicker() {
        let trimmedTicker = newTicker.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        guard !trimmedTicker.isEmpty else { return }
        if !webSocketManager.tickers.contains(trimmedTicker) {
            webSocketManager.tickers.append(trimmedTicker)
            webSocketManager.sendTickers()
        }
        newTicker = ""
        isAddingStock = false
        // Dismiss the keyboard
        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
    }
}
