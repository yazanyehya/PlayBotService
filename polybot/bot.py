import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
from polybot.img_proc import Img


class Bot:

    def __init__(self, token, telegram_chat_url):
        # create a new instance of the TeleBot class.
        # all communication with Telegram servers are done using self.telegram_bot_client
        self.telegram_bot_client = telebot.TeleBot(token)

        # remove any existing webhooks configured in Telegram servers
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # set the webhook URL
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)

        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return:
        """
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

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class QuoteBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if msg["text"] != 'Please don\'t quote me':
            self.send_text_with_quote(msg['chat']['id'], msg["text"], quoted_msg_id=msg["message_id"])


class ImageProcessingBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        chat_id = msg['chat']['id']

        # Handle /start
        if 'text' in msg and msg['text'].strip().lower() == '/start':
            self.send_text(chat_id,
                           "👋 Welcome! I'm your image assistant bot.\n\nSend me a photo with a caption like `rotate`, `blur`, or `segment`, and I’ll apply the filter for you.")
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
                "You can also *reply to a photo* with a command like `rotate` or `blur 2`."
            )
            self.send_text(chat_id, help_message)
            return

        # Filter map
        filter_map = {
            'blur': 'blur',
            'contour': 'contour',
            'rotate': 'rotate',
            'segment': 'segment',
            'salt_and_pepper': 'salt_n_pepper',
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

            # Try to get repeat count
            count = 1
            if i + 1 < len(parts) and parts[i + 1].isdigit():
                count = int(parts[i + 1])
                if filter_name in segment_strict:
                    self.send_text(chat_id, f"⚠️ `{filter_name}` does not support repeat count.")
                    return
                i += 1  # skip the count
            elif filter_name in segment_strict and i + 1 < len(parts) and parts[i + 1].isdigit():
                self.send_text(chat_id, f"⚠️ `{filter_name}` does not support repeat count.")
                return

            commands.append((filter_map[filter_name], count))
            i += 1

        try:
            # Download image
            image_path = self.download_user_photo(photo_msg)
            logger.info(f"Photo saved at {image_path}")

            # Apply filters in sequence
            img = Img(image_path)
            for method_name, repeat in commands:
                filter_func = getattr(img, method_name)
                for _ in range(repeat):
                    filter_func()
            filtered_path = img.save_img()

            # Send result
            self.send_photo(chat_id, filtered_path)

        except Exception as e:
            logger.exception("Image processing failed")
            self.send_text(chat_id, "❌ Something went wrong while processing your image.")

