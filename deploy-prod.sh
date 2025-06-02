#!/bin/bash

SERVICE_NAME="polybot-prod.service"
PROJECT_DIR="/home/ubuntu/PlayBotService"
SERVICE_FILE="$PROJECT_DIR/$SERVICE_NAME"

echo "🚀 Deploying $SERVICE_NAME..."

# Step 1: Copy systemd service file
sudo cp "$SERVICE_FILE" /etc/systemd/system/

# Step 2: Reload systemd
sudo systemctl daemon-reexec
sudo systemctl daemon-reload

# Step 3: Enable on boot
sudo systemctl enable "$SERVICE_NAME"

# Step 4: Restart service
sudo systemctl restart "$SERVICE_NAME"

# Step 5: Show status
echo "📊 Service status:"
sudo systemctl status "$SERVICE_NAME" --no-pager

# -----------------------------
# 📡 OpenTelemetry Collector Setup
# -----------------------------
echo "📡 Setting up OpenTelemetry Collector..."

# Install otelcol if not already installed
if ! command -v otelcol &> /dev/null
then
  echo "📥 Installing OpenTelemetry Collector..."
  wget -q https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.98.0/otelcol_0.98.0_linux_amd64.deb
  sudo dpkg -i otelcol_0.98.0_linux_amd64.deb
  rm otelcol_0.98.0_linux_amd64.deb
else
  echo "✅ otelcol already installed"
fi

# Write otelcol config
sudo tee /etc/otelcol/config.yaml > /dev/null <<EOF
receivers:
  hostmetrics:
    collection_interval: 15s
    scrapers:
      cpu:
      memory:
      disk:
      filesystem:
      load:
      network:
      processes:

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"

service:
  pipelines:
    metrics:
      receivers: [hostmetrics]
      exporters: [prometheus]
EOF

# Restart and enable otelcol
sudo systemctl restart otelcol
sudo systemctl enable otelcol

echo "✅ OpenTelemetry Collector is running and exposing metrics on :8889"
