#!/bin/bash

# Your Telegram bot token
export TELEGRAM_BOT_TOKEN=7661231941:AAE72m4R-mUSRVNRGlo24v5bxwF2b8wSkcI

# ✅ REMOVE THIS LINE: it should only be run ONCE manually
# ngrok config add-authtoken ...

# Start ngrok in background
/usr/local/bin/ngrok http 8443 > /dev/null &
sleep 3  # Wait a few seconds for ngrok to initialize

# Get the public URL from ngrok API
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | grep -o 'https://[^"]*ngrok-free.app' | head -n 1)

if [ -z "$NGROK_URL" ]; then
  echo "❌ Failed to get ngrok URL"
  exit 1
fi

export BOT_APP_URL=$NGROK_URL
echo "🌍 Ngrok URL is: $BOT_APP_URL"

# Start the bot
source venv/bin/activate
python3 -m polybot.app
