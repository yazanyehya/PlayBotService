# 🤖 Telegram Image Processing Bot

This bot is a Telegram assistant that lets users process images using a set of simple, caption-based commands. It responds to both direct photo messages and replies, making it a flexible and user-friendly tool for performing common image transformations.

---

## 🎯 Project Overview

The bot supports the following image processing operations:

- **rotate** – Rotates the image 90 degrees clockwise. You can specify how many times: `rotate 3` (270°).
- **blur** – Applies a blur filter. You can intensify it with a count: `blur 2`.
- **contour** – Applies a contour filter to highlight edges.
- **segment** – Performs binary segmentation (black and white), useful for high-contrast analysis.
- **salt and pepper** – Adds random noise to simulate corrupted data.

---

## 💬 User Commands & Behavior

### `/start`
- Greets the user with a welcome message.
- Informs them how to use the bot (send a photo with a caption).

### `/help`
- Lists all supported commands with short explanations.
- Provides examples like `rotate 2 blur` and how to reply to photos.

---

## 📷 How Users Interact

### 1. **Send Photo with Caption**
Users can send a photo with a command in the caption:
rotate 2 blur

The bot applies the filters in order — rotating the image twice and then blurring it.

### 2. **Reply to a Photo**
Users can reply to a photo with a text command:
blur 3
This allows users to reprocess existing images in the chat history.

---

## ⚠️ Smart Error Handling

- If a user sends a photo **without a caption**, the bot replies:  
  `"⚠️ Missing caption. Please use a caption like: rotate, blur, or segment."`

- If a user sends an **unsupported caption**, it replies:  
  `"❌ Unsupported filter: xyz"`

- If a user sends something like `segment 2` (which doesn’t make sense), it replies:  
  `"⚠️ segment does not support repeat count."`

- If the user replies to a message that **isn’t a photo**, it replies:  
  `"Please reply to a photo message."`

- For all unexpected errors (e.g., file issues, image corruption), the bot logs the error and replies:

---

## 🧪 Testing

The project includes unittests that:
- Mock Telegram API calls.
- Simulate sending photos with captions.
- Validate that the filters are applied.
- Ensure proper error handling when the bot encounters file or caption issues.

---

## 🧠 Summary of Core Logic

- **Command Parsing:** Splits the caption into filters and optional repeat counts.
- **Filter Execution:** Dynamically calls image processing methods using `getattr`.
- **Message Handling:** Differentiates between direct image messages and replies.
- **Extensibility:** You can easily add new filters by updating the `filter_map`.

---

## ✅ Example Use Cases

| User Input              | Bot Behavior                           |
|-------------------------|-----------------------------------------|
| `rotate` (with photo)   | Rotates the image once                  |
| `blur 3` (with photo)   | Applies blur 3 times                    |
| Reply `contour`         | Applies contour filter to the replied photo |
| `segment 2`             | Warns user: segment doesn't take count |
| No caption              | Asks user to add a valid command        |

---

## 👨‍💻 Developer Note

All communication with Telegram is done through `pyTelegramBotAPI`. Flask is used to expose a webhook endpoint that listens for incoming messages.

The image processing is handled using a custom `Img` class that wraps functionality from the `PIL` (Pillow) library.

---

