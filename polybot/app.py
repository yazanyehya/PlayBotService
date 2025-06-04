import flask
from flask import request
import os
from .bot import Bot, QuoteBot, ImageProcessingBot
from telegram import Bot
import asyncio

app = flask.Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
BOT_APP_URL = os.environ['BOT_APP_URL']


@app.route('/', methods=['GET'])
def index():
    return 'Ok'


@app.route(f'/{TELEGRAM_BOT_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


if __name__ == "__main__":
    bot = ImageProcessingBot(TELEGRAM_BOT_TOKEN, BOT_APP_URL)

    try:
        with open("polybot/polybot-dev.crt", "rb") as cert:
            info = bot.telegram_bot_client.get_webhook_info()
            if info.url != "https://yazanpolybot-dev.fursa.click/":
                asyncio.run(
                    bot.telegram_bot_client.set_webhook(
                        url="https://yazanpolybot-dev.fursa.click/",
                        certificate=cert
                    )
                )
                print("✅ Webhook set successfully")
            else:
                print("ℹ️ Webhook already set")
    except Exception as e:
        print("⚠️ Failed to set webhook:", e)

    app.run(host="0.0.0.0", port=8443)


