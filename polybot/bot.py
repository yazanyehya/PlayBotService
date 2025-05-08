import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
from polybot.img_proc import Img
from collections import defaultdict
import requests
from collections import Counter



class Bot:
    def __init__(self, token, telegram_chat_url):
        self.telegram_bot_client = telebot.TeleBot(token)
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)
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
            # Check if detect is in commands
            detect_commands = [cmd for cmd in commands if cmd[0] == 'detect']
            if detect_commands:
                try:
                    with open(image_path, 'rb') as img_file:
                        res = requests.post(
                            "http://localhost:8081/predict",  # or your actual YOLO URL
                            files={"file": img_file}
                        )
                    if res.status_code != 200:
                        self.send_text(chat_id, "❌ Failed to connect to object detection service.")
                        return

                    result = res.json()
                    labels = result.get('labels', [])
                    if labels:
                        label_counts = Counter(labels)
                        formatted = "\n".join([f"- {label} (×{count})" for label, count in label_counts.items()])
                        self.send_text(chat_id, f"🎯 Detected objects:\n{formatted}")
                    else:
                        self.send_text(chat_id, "✅ No objects detected.")

                except Exception as e:
                    logger.exception("Detection failed")
                    self.send_text(chat_id, "❌ Error during object detection.")
                return  # Skip local filters if 'detect' was used

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

