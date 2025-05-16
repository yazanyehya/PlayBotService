#!/bin/bash

# Your Telegram bot token
export TELEGRAM_BOT_TOKEN=7661231941:AAE72m4R-mUSRVNRGlo24v5bxwF2b8wSkcI

# Optional: Auth token (only needed once)
ngrok config add-authtoken 2Q9QH5Gpabh5fmYbvSI6WBsnIFj_7ej3rHUkBw7wiizCiTTW9

# Start ngrok in background
/home/ubuntu/.nvm/versions/node/v20.9.0/bin/ngrok http 8443 > /dev/null &
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
