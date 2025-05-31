#!/bin/bash

# Dev Telegram bot token
export TELEGRAM_BOT_TOKEN=8114485374:AAEd8gZSRBuOQUu8w10IIZVbQQN_WNJuqmU

# Start ngrok in background
/usr/local/bin/ngrok http 8443 > /dev/null &
sleep 3

# Get the public URL from ngrok API
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | grep -o 'https://[^"]*ngrok-free.app' | head -n 1)

if [ -z "$NGROK_URL" ]; then
  echo "❌ Failed to get ngrok URL"
  exit 1
fi

export BOT_APP_URL=https://ed14-18-144-8-188.ngrok-free.app
echo "🌍 Dev Ngrok URL is: $BOT_APP_URL"

source venv/bin/activate
python3 -m polybot.app
