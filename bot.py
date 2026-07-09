import telebot
import requests
import base64
import json
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import types

# ===== ТОКЕНЫ (вставлены напрямую для теста) =====
TELEGRAM_TOKEN = "8362080141:AAHLVRsdS6ub6Bm6mTq-wuqT_8CEEB3GBTY"
OPENROUTER_API_KEY = "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"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
MODEL = "google/gemini-2.5-flash-preview-09-2025"

# ===== ВЕБ-СЕРВЕР ДЛЯ RENDER =====
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

# Запускаем веб-сервер в отдельном потоке
thread = threading.Thread(target=run_web_server)
thread.daemon = True
thread.start()

# ===== ФУНКЦИЯ АНАЛИЗА ГРАФИКА =====
def analyze_chart(image_bytes):
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    prompt = """
    Ты — эксперт по техническому анализу криптовалют.
    Проанализируй этот график и дай структурированный ответ.

    Ответь строго в формате:

    📊 **Текущий паттерн:**
    [краткое описание формы графика, если видишь паттерн]

    📈 **Прогноз:**
    [куда вероятнее всего пойдет цена (кратко)]

    Если паттерн не определить — напиши: «Не удаётся идентифицировать чёткий паттерн» и дай общую оценку настроения рынка (бычье, медвежье, нейтральное).
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                ]
            }
        ]
    }
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ Ошибка при анализе: {str(e)}"

# ===== ОБРАБОТЧИКИ TELEGRAM =====
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    bot.send_chat_action(message.chat.id, 'typing')
    result = analyze_chart(downloaded_file)
    bot.reply_to(message, result, parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
📈 **Крипто-аналитик**

Пришли мне **скриншот графика** (фото), и я:
1️⃣ Распознаю текущий паттерн
2️⃣ Дам прогноз, куда вероятнее всего пойдет цена

🔹 Поддерживаются графики с TradingView, Binance, любой биржи.
🔹 Можно отправить как фото, так и ссылку на изображение.
🔹 Чем чётче скриншот — тем точнее анализ.

Используется модель **Gemini Flash** через OpenRouter.
"""
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

if __name__ == "__main__":
    print("Бот-аналитик с OpenRouter запущен и слушает порт")
    bot.infinity_polling()