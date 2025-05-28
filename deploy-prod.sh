#!/bin/bash

SERVICE_NAME="polybot-prod.service"
PROJECT_DIR="/home/ubuntu/PolybotService"
SERVICE_FILE="$PROJECT_DIR/$SERVICE_NAME"

echo "🚀 Deploying $SERVICE_NAME..."

sudo cp "$SERVICE_FILE" /etc/systemd/system/
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "📊 Service status:"
sudo systemctl status "$SERVICE_NAME" --no-pager
