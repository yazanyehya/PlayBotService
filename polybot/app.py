import flask
from flask import request
import os
from .bot import Bot, QuoteBot, ImageProcessingBot
from telegram import Bot
from polybot.dynamodb import DynamoDBStorage
import asyncio
import requests
app = flask.Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
BOT_APP_URL = os.environ['BOT_APP_URL']
YOLO_URL =os.environ['YOLO_URL']
storage = DynamoDBStorage()

@app.route('/', methods=['GET'])
def index():
    return 'Ok'


@app.route(f'/{TELEGRAM_BOT_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'

@app.route('/predictions/<prediction_id>', methods=['POST'])
def receive_prediction(prediction_id):
    data = request.get_json()
    print(f"📬 Received prediction notification for {prediction_id}: {data}")

    chat_id = data.get("chat_id")
    uid = data.get("uid")  # Same as prediction_id typically

    if not chat_id or not uid:
        print("⚠️ Missing chat_id or uid")
        return 'Bad Request', 400

    # 🔍 Fetch from DynamoDB via storage class
    prediction = storage.get_prediction(uid)

    if not prediction:
        bot.send_text(chat_id, "❌ Failed to retrieve your prediction. Please try again later.")
        return 'Not Found', 404

    # 🧠 Optional: summarize prediction
    objects = prediction.get("detection_objects", [])
    if objects:
        label_counts = {}
        for obj in objects:
            label = obj.get("label")
            if label:
                label_counts[label] = label_counts.get(label, 0) + 1

        formatted = "\n".join([f"- {label} (×{count})" for label, count in label_counts.items()])
        bot.send_text(chat_id, f"🎯 Detected objects:\n{formatted}")
    else:
        bot.send_text(chat_id, "✅ No objects detected.")

    return 'OK', 200



if __name__ == "__main__":
    bot = ImageProcessingBot(TELEGRAM_BOT_TOKEN, BOT_APP_URL)


    app.run(host="0.0.0.0", port=8443)

