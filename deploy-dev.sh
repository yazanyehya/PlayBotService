#!/bin/bash

SERVICE_NAME="polybot-dev.service"
PROJECT_DIR="/home/ubuntu/PolybotService"
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
