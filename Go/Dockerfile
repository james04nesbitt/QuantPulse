# Dockerfile for Go Backend

# Stage 1: Build the Go binary
FROM golang:1.20-alpine AS builder

# Set environment variables
ENV GO111MODULE=on

# Create and change to the app directory
WORKDIR /app

# Copy go.mod and go.sum files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy the source code
COPY . .

# Build the Go app
RUN go build -o main .

# Stage 2: Create a minimal image for running the app
FROM alpine:latest

# Install CA certificates
RUN apk --no-cache add ca-certificates

# Set the working directory
WORKDIR /root/

# Copy the binary from the builder stage
COPY --from=builder /app/main .

# Expose port (optional, as Cloud Run manages ports)
EXPOSE 8080

# Command to run the executable
CMD ["./main"]
