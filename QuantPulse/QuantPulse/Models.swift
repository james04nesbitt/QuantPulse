import SwiftUI

// Enum for gain periods
enum GainPeriod: String, CaseIterable {
    case daily = "Daily"
    case weekly = "Weekly"
    case allTime = "All-Time"
}

// Stock model conforming to Identifiable
struct Stock: Identifiable {
    let id = UUID()
    let ticker: String
    let name: String
    let symbol: String // Assuming this is the image name
    let price: Double
    let dailyGain: Double
    let weeklyGain: Double
    let allTimeGain: Double
    
}

// Stock History Data
struct StockHistory: Codable, Identifiable {
    let id = UUID()
    let Date: String
    let Open: Double
    let High: Double
    let Low: Double
    let Close: Double
    let Volume: Int
}

// Update Message
struct UpdateMessage: Codable {
    let type: String
    let data: [String: [StockHistory]] // Ticker: [StockHistory]
}

