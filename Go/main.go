// main.go

package main

import (
	"context"
	"encoding/json"
	"log"
	"sync"

	"cloud.google.com/go/pubsub"
	"google.golang.org/api/option"
)

// CalculationTask represents the incoming task message
type CalculationTask struct {
	Ticker string    `json:"ticker"`
	Prices []float64 `json:"prices"`
	Period int       `json:"period"` // Number of days
}

// CalculationResult represents the result to be published
type CalculationResult struct {
	Ticker string    `json:"ticker"`
	SMA    []float64 `json:"sma"`
	RSI    []float64 `json:"rsi"`
}

func main() {
	ctx := context.Background()

	// Set up Pub/Sub client with credentials
	projectID := "your-gcp-project-id"                            // Replace with your GCP Project ID
	serviceAccountKey := "/path/to/your/service-account-key.json" // Replace with your key path

	client, err := pubsub.NewClient(ctx, projectID, option.WithCredentialsFile(serviceAccountKey))
	if err != nil {
		log.Fatalf("Failed to create Pub/Sub client: %v", err)
	}
	defer client.Close()

	// Define topics and subscriptions
	taskTopic := client.Topic("stock-calculation-tasks")
	resultTopic := client.Topic("stock-calculation-results")

	// Ensure topics exist
	if exists, err := topicExists(ctx, client, "stock-calculation-tasks"); err != nil {
		log.Fatalf("Error checking task topic existence: %v", err)
	} else if !exists {
		log.Fatalf("Task topic 'stock-calculation-tasks' does not exist.")
	}

	if exists, err := topicExists(ctx, client, "stock-calculation-results"); err != nil {
		log.Fatalf("Error checking result topic existence: %v", err)
	} else if !exists {
		log.Fatalf("Result topic 'stock-calculation-results' does not exist.")
	}

	// Subscribe to the task subscription
	subscriptionID := "go-backend-subscription"
	sub := client.Subscription(subscriptionID)

	// Use a wait group to handle concurrent message processing
	var wg sync.WaitGroup

	err = sub.Receive(ctx, func(ctx context.Context, msg *pubsub.Message) {
		wg.Add(1)
		go func(msg *pubsub.Message) {
			defer wg.Done()
			var task CalculationTask
			if err := json.Unmarshal(msg.Data, &task); err != nil {
				log.Printf("Error unmarshalling message: %v", err)
				msg.Nack()
				return
			}

			log.Printf("Received task for ticker: %s", task.Ticker)

			// Calculate SMA and RSI
			sma := calculateSMA(task.Prices, task.Period)
			rsi := calculateRSI(task.Prices, task.Period)

			// Create result
			result := CalculationResult{
				Ticker: task.Ticker,
				SMA:    sma,
				RSI:    rsi,
			}

			// Marshal result to JSON
			resultData, err := json.Marshal(result)
			if err != nil {
				log.Printf("Error marshalling result: %v", err)
				msg.Nack()
				return
			}

			// Publish result
			_, err = resultTopic.Publish(ctx, &pubsub.Message{
				Data: resultData,
			}).Get(ctx)
			if err != nil {
				log.Printf("Error publishing result for %s: %v", task.Ticker, err)
				msg.Nack()
				return
			}

			log.Printf("Published result for ticker: %s", task.Ticker)
			msg.Ack()
		}(msg)
	})

	if err != nil {
		log.Fatalf("Error receiving messages: %v", err)
	}

	// Wait for all goroutines to finish
	wg.Wait()
}

// topicExists checks if a topic exists
func topicExists(ctx context.Context, client *pubsub.Client, topicName string) (bool, error) {
	exists, err := client.Topic(topicName).Exists(ctx)
	if err != nil {
		return false, err
	}
	return exists, nil
}

// calculateSMA calculates the Simple Moving Average
func calculateSMA(prices []float64, period int) []float64 {
	var sma []float64
	for i := 0; i <= len(prices)-period; i++ {
		sum := 0.0
		for _, price := range prices[i : i+period] {
			sum += price
		}
		sma = append(sma, sum/float64(period))
	}
	return sma
}

// calculateRSI calculates the Relative Strength Index
func calculateRSI(prices []float64, period int) []float64 {
	var rsi []float64
	for i := 0; i <= len(prices)-period-1; i++ {
		gains := 0.0
		losses := 0.0
		for j := i; j < i+period; j++ {
			change := prices[j+1] - prices[j]
			if change > 0 {
				gains += change
			} else {
				losses -= change
			}
		}
		avgGain := gains / float64(period)
		avgLoss := losses / float64(period)
		if avgLoss == 0 {
			rsi = append(rsi, 100)
			continue
		}
		rs := avgGain / avgLoss
		rsiValue := 100 - (100 / (1 + rs))
		rsi = append(rsi, rsiValue)
	}
	return rsi
}
