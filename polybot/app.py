import flask
from flask import request
import os
from .bot import Bot, QuoteBot, ImageProcessingBot
from telegram import Bot

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
            telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)
            telegram_bot.set_webhook(
                url="https://yazanpolybot-dev.fursa.click/",
                certificate=cert
            )
            print("✅ Webhook set successfully")
    except Exception as e:
        print("⚠️ Failed to set webhook:", e)

    # Start the app anyway
    app.run(host="0.0.0.0", port=8443)

