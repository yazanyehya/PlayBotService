import telebot
from loguru import logger
import time
from telebot.types import InputFile
from polybot.img_proc import Img
import requests
from collections import Counter
import boto3
import os
import uuid
from threading import Thread
import json


YOLO_URL = os.environ.get("YOLO_URL")
AWS_REGION = os.getenv("AWS_REGION", "us-west-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")


s3_client = boto3.client("s3", region_name=AWS_REGION)
sqs_client = boto3.client("sqs", region_name=AWS_REGION)


def poll_prediction_and_respond(chat_id: int, prediction_id: str, bot):
    MAX_RETRIES = 5
    RETRY_DELAY = 5  # seconds

    for attempt in range(MAX_RETRIES):
        try:
            res = requests.get(f"{YOLO_URL}/prediction/{prediction_id}")
            print(f"🔁 Attempt {attempt+1} - Status: {res.status_code}")
            data = res.json()
            print("🔥 RESPONSE JSON:", data)

            label_counts = data.get("label_counts", {})
            if label_counts:
                formatted = "\n".join([f"- {label} (×{count})" for label, count in label_counts.items()])
                bot.send_text(chat_id, f"🎯 Detected objects:\n{formatted}")
            else:
                bot.send_text(chat_id, "✅ No objects detected.")
            return
        except Exception as e:
            print(f"❌ Error fetching prediction (try {attempt + 1}): {e}")

        time.sleep(RETRY_DELAY)

    bot.send_text(chat_id, "⚠️ Still processing or failed to get results. Please try again later.")

class Bot:
    def __init__(self, token, telegram_chat_url):
        self.telegram_bot_client = telebot.TeleBot(token)
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60,
                                             certificate=open(os.getenv("BOT_APP_CERT_PATH"), 'r')
)
        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)

        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")
        self.telegram_bot_client.send_photo(chat_id, InputFile(img_path))

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class QuoteBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        if msg["text"] != 'Please don\'t quote me':
            self.send_text_with_quote(msg['chat']['id'], msg["text"], quoted_msg_id=msg["message_id"])


class ImageProcessingBot(Bot):
    media_group_cache = {}

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        chat_id = msg['chat']['id']
        group_id = msg.get('media_group_id')

        # Initialize media group cache if not already
        if not hasattr(self, 'media_group_cache'):
            self.media_group_cache = {}

        # Handle /start
        if 'text' in msg and msg['text'].strip().lower() == '/start':
            self.send_text(chat_id,
                           "👋 Welcome! Send a photo with a caption like `rotate`, `blur`, or `segment`, or send 2 photos with caption `concat` to join them.")
            return

        # Handle /help
        if 'text' in msg and msg['text'].strip().lower() == '/help':
            help_message = (
                "🤖 *Image Assistant Bot Help*\n\n"
                "Send a photo with one or more of these commands (optionally with repeat count):\n"
                "- `rotate`, `blur`, `contour`, `segment`, `salt and pepper`\n"
                "Examples:\n"
                "- `rotate blur`\n"
                "- `blur 2 contour`\n"
                "- `rotate 2 blur 3`\n\n"
                "Or send *2 photos* with caption `concat` to merge them horizontally.\n"
                "You can also *reply to a photo* with a command like `rotate` or `blur 2`."
            )
            self.send_text(chat_id, help_message)
            return

        # Handle media group for concat
        if group_id:
            if group_id not in self.media_group_cache:
                self.media_group_cache[group_id] = []
            self.media_group_cache[group_id].append(msg)

            if len(self.media_group_cache[group_id]) < 2:
                return  # Wait for second image

            if len(self.media_group_cache[group_id]) == 2:
                messages = self.media_group_cache.pop(group_id)
                caption = messages[0].get('caption', '').strip().lower()

                if caption != 'concat':
                    self.send_text(chat_id, "Please use `concat` as caption when sending 2 photos.")
                    return

                try:
                    path1 = self.download_user_photo(messages[0])
                    path2 = self.download_user_photo(messages[1])

                    img1 = Img(path1)
                    img2 = Img(path2)

                    img1.concat(img2)
                    result_path = img1.save_img()

                    self.send_photo(chat_id, result_path)
                except Exception as e:
                    logger.exception("Concat failed")
                    self.send_text(chat_id, "❌ Failed to concatenate the two images.")
                return

        # Handle normal photo with caption or reply command
        filter_map = {
            'blur': 'blur',
            'contour': 'contour',
            'rotate': 'rotate',
            'segment': 'segment',
            'salt_and_pepper': 'salt_n_pepper',
            'detect':'detect',
            'sharpen': 'sharpen',
        }
        segment_strict = {'segment'}

        # 1. Direct photo + caption
        if 'photo' in msg and 'caption' in msg:
            caption = msg['caption'].strip().lower()
            parts = caption.split()
            photo_msg = msg

        # 2. Reply to a photo with a command
        elif 'reply_to_message' in msg and 'text' in msg:
            caption = msg['text'].strip().lower()
            parts = caption.split()
            if 'photo' in msg['reply_to_message']:
                photo_msg = msg['reply_to_message']
            else:
                self.send_text(chat_id, "Please reply to a photo message.")
                return
        else:
            self.send_text(chat_id, "Please send a photo with a caption or reply to a photo with a command.")
            return

        # Validate and extract filters + counts
        commands = []
        i = 0
        while i < len(parts):
            filter_name = parts[i]
            if filter_name not in filter_map:
                self.send_text(chat_id, f"❌ Unsupported filter: {filter_name}")
                return

            count = 1
            if i + 1 < len(parts) and parts[i + 1].isdigit():
                count = int(parts[i + 1])
                if filter_name in segment_strict:
                    self.send_text(chat_id, f"⚠️ `{filter_name}` does not support repeat count.")
                    return
                i += 1
            elif filter_name in segment_strict and i + 1 < len(parts) and parts[i + 1].isdigit():
                self.send_text(chat_id, f"⚠️ `{filter_name}` does not support repeat count.")
                return

            commands.append((filter_map[filter_name], count))
            i += 1

        try:
            image_path = self.download_user_photo(photo_msg)
            logger.info(f"Photo saved at {image_path}")

            # NEW: Upload to S3
            image_filename = os.path.basename(image_path)
            s3_key = f"{chat_id}/original/{image_filename}"

            try:
                s3_client.upload_file(image_path, AWS_S3_BUCKET, s3_key)
                logger.info(f"✅ Uploaded {s3_key} to S3 bucket: {AWS_S3_BUCKET}")
            except Exception as e:
                logger.error(f"❌ Failed to upload to S3: {e}")
                self.send_text(chat_id, "❌ Failed to upload image to storage.")
                return

            # Check if detect is in commands
            # Check if 'detect' is among the commands
            detect_commands = [cmd for cmd in commands if cmd[0] == 'detect']
            if detect_commands:
                prediction_id = f"pred-{chat_id}-{uuid.uuid4()}"
                message_payload = {
                    "image_key": s3_key,
                    "chat_id": chat_id,
                    "prediction_id": prediction_id,
                    "caption": caption  # Optional, useful if YOLO will use it
                }

                try:
                    sqs_client.send_message(
                        QueueUrl=SQS_QUEUE_URL,
                        MessageBody=json.dumps(message_payload)
                    )
                    logger.info(f"✅ SQS message sent with prediction ID: {prediction_id}")
                    self.send_text(chat_id, "✅ Your image is being processed. You’ll receive results shortly.")
                    Thread(target=poll_prediction_and_respond, args=(chat_id, prediction_id, self)).start()

                except Exception as e:
                    logger.error(f"❌ Failed to send to SQS: {e}")
                    self.send_text(chat_id, "❌ Failed to submit image for processing. Please try again.")
                return  # Important: skip local image processing

            img = Img(image_path)
            for method_name, repeat in commands:
                filter_func = getattr(img, method_name)
                for _ in range(repeat):
                    filter_func()
            filtered_path = img.save_img()

            self.send_photo(chat_id, filtered_path)

        except Exception as e:
            logger.exception("Image processing failed")
            self.send_text(chat_id, "❌ Something went wrong while processing your image.")

