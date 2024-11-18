import SwiftUI

struct StockRowView: View {
    let ticker: String
    let latestData: StockHistory
    let gainPeriod: GainPeriod
    
    var body: some View {
        HStack {
            // Symbol Image (Placeholder)
            Image(systemName: "chart.bar")
                .resizable()
                .frame(width: 40, height: 40)
                .foregroundColor(.blue)
                .padding(.trailing, 10)
            
            // Stock Info
            VStack(alignment: .leading, spacing: 4) {
                Text(ticker)
                    .font(.headline)
                Text("Company Name") // Placeholder for company name
                    .font(.subheadline)
                    .foregroundColor(.gray)
            }
            
            Spacer()
            
            // Price and Gain/Loss
            VStack(alignment: .trailing, spacing: 4) {
                Text("$\(latestData.Close, specifier: "%.2f")")
                    .font(.headline)
                Text(gainText())
                    .font(.subheadline)
                    .foregroundColor(gainColor())
            }
        }
        .padding(.vertical, 8)
    }
    
    // Helper Methods
    private func gainText() -> String {
        // Calculate gain based on gainPeriod
        // For simplicity, using Open and Close prices
        let gain = ((latestData.Close - latestData.Open) / latestData.Open) * 100
        return String(format: "%@%.2f%%", gain >= 0 ? "+" : "", gain)
    }
    
    private func gainColor() -> Color {
        let gain = ((latestData.Close - latestData.Open) / latestData.Open) * 100
        return gain >= 0 ? .green : .red
    }
}
