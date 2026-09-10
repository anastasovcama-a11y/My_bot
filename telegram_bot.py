import asyncio
import csv
import os
import threading
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile

# ============================================================
# НАСТРОЙКИ
# ============================================================
CSV_FILE = "messages.csv"          # ← общий файл для всех ботов (НЕ МЕНЯТЬ, если хотите общую выгрузку)
MEDIA_DIR = "media"                # ← папка для медиа
ADMIN_CHAT_ID = 863066338          # ← ИЗМЕНИТЬ на ваш Telegram ID (узнать у @userinfobot)

os.makedirs(MEDIA_DIR, exist_ok=True)

# ============================================================
# ЗАГРУЗКА СТОП-СЛОВ
# ============================================================
def load_bad_words():
    try:
        with open("bad_words.txt", "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        return ["спам", "реклама", "казино", "ставки"]

BAD_WORDS = load_bad_words()

def normalize_text(text):
    text = text.lower()
    replacements = {
        "@": "а", "a": "а", "e": "е", "o": "о",
        "p": "р", "c": "с", "x": "х", "y": "у",
        "0": "о", "1": "и", "3": "з", "6": "б",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

# ============================================================
# СОХРАНЕНИЕ В ОБЩИЙ CSV (потокобезопасно)
# ============================================================
csv_lock = threading.Lock()

def save_to_csv(source, username, text, media_path=""):
    with csv_lock:
        file_exists = os.path.isfile(CSV_FILE)
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Дата", "Источник", "Отправитель", "Текст", "Медиа"])
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                source,
                username,
                text,
                media_path
            ])

# ============================================================
# СКАЧИВАНИЕ МЕДИА
# ============================================================
async def download_telegram_media(message: types.Message):
    media_path = ""
    try:
        if message.photo:
            file = await message.bot.get_file(message.photo[-1].file_id)
            filename = f"{MEDIA_DIR}/tg_{message.message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            await message.bot.download_file(file.file_path, filename)
            media_path = filename
        elif message.video:
            file = await message.bot.get_file(message.video.file_id)
            filename = f"{MEDIA_DIR}/tg_{message.message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            await message.bot.download_file(file.file_path, filename)
            media_path = filename
        elif message.document:
            file = await message.bot.get_file(message.document.file_id)
            original_name = message.document.file_name or "file"
            filename = f"{MEDIA_DIR}/tg_{message.message_id}_{original_name}"
            await message.bot.download_file(file.file_path, filename)
            media_path = filename
        elif message.voice:
            file = await message.bot.get_file(message.voice.file_id)
            filename = f"{MEDIA_DIR}/tg_{message.message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ogg"
            await message.bot.download_file(file.file_path, filename)
            media_path = filename
        elif message.audio:
            file = await message.bot.get_file(message.audio.file_id)
            filename = f"{MEDIA_DIR}/tg_{message.message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            await message.bot.download_file(file.file_path, filename)
            media_path = filename
        elif message.sticker:
            file = await message.bot.get_file(message.sticker.file_id)
            filename = f"{MEDIA_DIR}/tg_{message.message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webp"
            await message.bot.download_file(file.file_path, filename)
            media_path = filename
    except Exception as e:
        print(f"Ошибка скачивания медиа: {e}")
    return media_path

# ============================================================
# ФУНКЦИЯ ДЛЯ ЗАПУСКА ОДНОГО TELEGRAM-БОТА
# ============================================================
async def start_telegram_bot(token: str, bot_name: str):
    bot = Bot(token=token)
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def start_handler(message: types.Message):
        await message.answer("Привет! Я записываю все сообщения.")

    @dp.message(Command("export"))
    async def export_handler(message: types.Message):
        if os.path.isfile(CSV_FILE):
            await message.answer_document(FSInputFile(CSV_FILE), caption="📊 Выгрузка сообщений")
        else:
            await message.answer("Файл пока пуст — нет записанных сообщений.")

    @dp.message()
    async def tg_handler(message: types.Message):
        username = message.from_user.username or message.from_user.first_name or "Аноним"
        text = message.text or message.caption or ""
        normalized = normalize_text(text)
        if any(word in normalized for word in BAD_WORDS):
            try:
                await message.delete()
            except Exception as e:
                print(f"Ошибка удаления: {e}")
            return
        media_path = await download_telegram_media(message)
        if text or media_path:
            save_to_csv(f"Telegram ({bot_name})", username, text, media_path)

    print(f"✅ Telegram-бот '{bot_name}' запущен")
    await dp.start_polling(bot)

# ============================================================
# ЗАПУСК ВСЕХ TELEGRAM-БОТОВ (МНОЖЕСТВЕННЫЕ АККАУНТЫ)
# ============================================================
# <<< СЕЙЧАС: один бот. ПОЗЖЕ: добавьте остальных, убрав # >>>
TELEGRAM_BOTS = [
    {"token": "ТОКЕН_БОТА_1", "name": "Основной"},     # ← ИЗМЕНИТЬ: вставьте токен от @BotFather
    # {"token": "ТОКЕН_БОТА_2", "name": "Второй"},     # ← ДОБАВИТЬ ПОЗЖЕ: раскомментируйте и вставьте токен
    # {"token": "ТОКЕН_БОТА_3", "name": "Третий"},     # ← ДОБАВИТЬ ПОЗЖЕ
]

async def main():
    tasks = []
    for bot_info in TELEGRAM_BOTS:
        task = asyncio.create_task(
            start_telegram_bot(bot_info["token"], bot_info["name"])
        )
        tasks.append(task)
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())