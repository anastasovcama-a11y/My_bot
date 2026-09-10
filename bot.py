import asyncio
import csv
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from vkbottle.bot import Bot as VKBot, Message as VKMessage
from vkbottle import GroupEventType, GroupTypes

# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
VK_TOKEN = os.environ.get("VK_TOKEN")
VK_GROUP_ID = int(os.environ.get("VK_GROUP_ID", 0))
CSV_FILE = os.environ.get("CSV_FILE", "messages.csv")
MEDIA_DIR = "media"

# Создаём папку для медиа, если её нет
os.makedirs(MEDIA_DIR, exist_ok=True)

# ========== ЗАПИСЬ В CSV ==========
def save_to_csv(source, username, text, media_path=""):
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

# ========== СОХРАНЕНИЕ МЕДИА (Telegram) ==========
async def download_telegram_media(message: types.Message):
    """Скачивает медиа из сообщения Telegram и возвращает путь к файлу."""
    media_path = ""
    
    try:
        # Фото
        if message.photo:
            file = await message.bot.get_file(message.photo[-1].file_id)
            ext = "jpg"
            filename = f"{MEDIA_DIR}/tg_{message.message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            await message.bot.download_file(file.file_path, filename)
            media_path = filename
        
        # Видео
        elif message.video:
            file = await message.bot.get_file(message.video.file_id)
            filename = f"{MEDIA_DIR}/tg_{message.message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            await message.bot.download_file(file.file_path, filename)
            media_path = filename
        
        # Документы
        elif message.document:
            file = await message.bot.get_file(message.document.file_id)
            original_name = message.document.file_name or "file"
            filename = f"{MEDIA_DIR}/tg_{message.message_id}_{original_name}"
            await message.bot.download_file(file.file_path, filename)
            media_path = filename
        
        # Голосовые
        elif message.voice:
            file = await message.bot.get_file(message.voice.file_id)
            filename = f"{MEDIA_DIR}/tg_{message.message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ogg"
            await message.bot.download_file(file.file_path, filename)
            media_path = filename
        
        # Аудио
        elif message.audio:
            file = await message.bot.get_file(message.audio.file_id)
            filename = f"{MEDIA_DIR}/tg_{message.message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            await message.bot.download_file(file.file_path, filename)
            media_path = filename
        
        # Стикеры
        elif message.sticker:
            file = await message.bot.get_file(message.sticker.file_id)
            filename = f"{MEDIA_DIR}/tg_{message.message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webp"
            await message.bot.download_file(file.file_path, filename)
            media_path = filename
    
    except Exception as e:
        print(f"Ошибка скачивания медиа: {e}")
    
    return media_path

# ========== TELEGRAM ==========
tg_bot = Bot(token=TELEGRAM_TOKEN)
tg_dp = Dispatcher()

@tg_dp.message()
async def tg_handler(message: types.Message):
    username = message.from_user.username or message.from_user.first_name or "Аноним"
    text = message.text or message.caption or ""
    
    # Скачиваем медиа, если оно есть
    media_path = await download_telegram_media(message)
    
    # Если ни текста, ни медиа — пропускаем
    if not text and not media_path:
        return
    
    save_to_csv("Telegram", username, text, media_path)

async def run_telegram():
    await tg_dp.start_polling(tg_bot)

# ========== VK ==========
vk_bot = VKBot(token=VK_TOKEN)

def extract_vk_media(message: VKMessage):
    """Извлекает ссылки на медиа из сообщения ВК."""
    media_links = []
    
    if message.attachments:
        for attach in message.attachments:
            if attach.type == "photo":
                # Берём самое большое фото
                sizes = attach.photo.sizes
                if sizes:
                    media_links.append(sizes[-1].url)
            elif attach.type == "video":
                media_links.append(f"https://vk.com/video{attach.video.owner_id}_{attach.video.id}")
            elif attach.type == "doc":
                media_links.append(attach.doc.url)
            elif attach.type == "audio":
                media_links.append(f"audio{attach.audio.owner_id}_{attach.audio.id}")
            elif attach.type == "voice":
                media_links.append(attach.voice.link_ogg)
    
    return "; ".join(media_links) if media_links else ""

@vk_bot.on.message()
async def vk_handler(message: VKMessage):
    user_info = await vk_bot.api.users.get(user_ids=message.from_id)
    username = user_info[0].first_name if user_info else "Аноним"
    text = message.text or ""
    media = extract_vk_media(message)
    
    if not text and not media:
        return
    
    save_to_csv("VK", username, text, media)

@vk_bot.on.raw_event(GroupEventType.WALL_REPLY_NEW)
async def vk_comment_handler(event: GroupTypes.WallReplyNew):
    username = f"id{event.object.from_id}"
    text = event.object.text or ""
    
    # Медиа в комментариях ВК
    media = ""
    if event.object.attachments:
        links = []
        for attach in event.object.attachments:
            if attach.type == "photo":
                sizes = attach.photo.sizes
                if sizes:
                    links.append(sizes[-1].url)
        media = "; ".join(links)
    
    save_to_csv("VK-Comment", username, text, media)

# ========== ЗАПУСК ==========
async def main():
    await asyncio.gather(
        run_telegram(),
        vk_bot.run_polling()
    )

if __name__ == "__main__":
    asyncio.run(main())