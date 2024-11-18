import SwiftUI

struct StockDetailView: View {
    let ticker: String
    let stockHistory: [StockHistory]
    
    var body: some View {
        VStack {
            Text(ticker)
                .font(.largeTitle)
                .padding()
            Text("Detailed information will go here.")
                .font(.body)
                .padding()
            Spacer()
        }
        .navigationTitle(ticker)
    }
}
