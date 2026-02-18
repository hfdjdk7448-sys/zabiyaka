import asyncio
import os
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions
from aiohttp import web

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8463010853:AAE7piw8PFlxNCzKw9vIrmdJmTYAm1rBnuI"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище (в памяти)
user_ranks = {}

RANKS = {
    5: "Вожак стаи 👑",
    4: "Старший всадник 🐉",
    3: "Главный драконовед 📚",
    2: "Главный наездник ⚔️",
    1: "Простой житель 🪵",
    0: "Обычный участник"
}

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="Задирака и Забияка на посту!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Берем порт, который дает Render
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server is live on port {port}")

# --- КОМАНДЫ ---

@dp.message(Command("старт", "start"))
async def cmd_start(message: Message):
    # Автоматически даем тебе 5 ранг, если ты первый
    if message.from_user.id not in user_ranks:
        user_ranks[message.from_user.id] = 5
    
    await message.answer(
        "Привет!\nДобро пожаловать в Драконий край 🐲\n\n"
        "Я готов к работе. Ты назначен Вожаком стаи! Попробуй команду /админы"
    )

@dp.message(Command("админы"))
async def list_admins(message: Message):
    text = "📜 **Совет Драконьего Края:**\n\n"
    if not user_ranks:
        text += "Пока никого нет."
    else:
        for uid, rank in sorted(user_ranks.items(), key=lambda x: x[1], reverse=True):
            text += f"{RANKS.get(rank, 'Участник')} — ID: {uid}\n"
    await message.answer(text)

@dp.chat_member()
async def welcome(event: types.ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        await bot.send_video(
            chat_id=event.chat.id,
            video="https://media.tenor.com/TphIrQuFImkAAAA1/drake-how-to-train-your-dragon.webp",
            caption=(
                "Привет!\n"
                "Добро пожаловать в Драконий край 🐲\n\n"
                "Рады видеть тебя в нашем чате. Здесь собираются люди, которым близка вселенная «Как приручить дракона»: обсуждения, теории, размышления и живое общение — без лишнего шума и конфликтов\n\n"
                "Чувствуй себя комфортно, знакомься, участвуй в разговорах — будем рады твоему присутствию 😀\n"
                "Если возникнут вопросы или понадобится помощь, смело обращайся к администрации\n\n"
                "Приятного общения и хорошего дня 🐉✨"
            )
        )

# --- ГЛАВНЫЙ ЗАПУСК ---
async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Сначала запускаем сервер, чтобы Render сразу его увидел
    await start_web_server()
    
    # Потом запускаем бота
    logging.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
            
