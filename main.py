import asyncio
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, ChatMemberUpdated, ContentType
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web

# --- НАСТРОЙКИ ---
TOKEN = "8463010853:AAE7piw8PFlxNCzKw9vIrmdJmTYAm1rBnuI"
CHAT_ID = -1002508735096  
DB_FILE = "dragon_data.json"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

# --- ВЕБ-СЕРВЕР ДЛЯ ПОДДЕРЖКИ ЖИЗНИ ---
async def handle(request):
    return web.Response(text="Бот активен!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render передает порт в переменной окружения PORT
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Веб-сервер запущен на порту {port}")

# --- БАЗА ДАННЫХ ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {
        "users": {}, 
        "permissions": {"бан": 5, "мут": 4, "варн": 3, "кик": 3, "кд": 5, "повысить": 5, "понизить": 5},
        "media_counter": {},
        "media_history": {}
    }

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

def get_u(uid, name="Викинг"):
    uid = str(uid)
    if uid not in db["users"]:
        is_first = len(db["users"]) == 0
        db["users"][uid] = {"nick": name, "stars": 5 if is_first else 1, "messages": 0, "warns": []}
        save_db(db)
    return db["users"][uid]

async def has_access(message: Message, cmd_name: str):
    u = get_u(message.from_user.id)
    required = db["permissions"].get(cmd_name.lower(), 1)
    if u["stars"] < required:
        await message.reply(f"Ошибка доступа! 🚫\nТвой ранг: {u['stars']} ⭐\nНужно: {required} ⭐")
        return False
    return True

# --- КОМАНДЫ ---
@dp.message(Command("повысить", prefix="!"))
async def promote_user(message: Message, command: CommandObject):
    if not await has_access(message, "повысить"): return
    if not message.reply_to_message: return await message.reply("Ответь на сообщение!")
    target = message.reply_to_message.from_user
    u = get_u(target.id, target.first_name)
    new_rank = u["stars"] + 1
    if command.args:
        try:
            val = int(command.args)
            if 1 <= val <= 5: new_rank = val
        except: pass
    u["stars"] = min(new_rank, 5)
    save_db(db)
    await message.answer(f"📈 Викинг <b>{u['nick']}</b> повышен до {u['stars']} ⭐")

@dp.message(Command("понизить", prefix="!"))
async def demote_user(message: Message):
    if not await has_access(message, "понизить"): return
    if not message.reply_to_message: return await message.reply("Ответь на сообщение!")
    target = message.reply_to_message.from_user
    u = get_u(target.id, target.first_name)
    u["stars"] = 1
    save_db(db)
    await message.answer(f"📉 Викинг <b>{u['nick']}</b> разжалован до 1 ⭐")

@dp.message(Command("бан", "мут", "варн", "кик", prefix="!"))
async def moderate(message: Message):
    cmd = message.text[1:].split()[0].lower()
    if not await has_access(message, cmd): return
    if not message.reply_to_message: return await message.reply("Ответь на сообщение!")
    target = message.reply_to_message.from_user
    u = get_u(target.id)
    if cmd == "варн":
        u["warns"].append(datetime.now().strftime("%d.%m %H:%M"))
        if len(u["warns"]) >= 5:
            await message.chat.ban(target.id)
            await message.answer(f"Викинг {u['nick']} изгнан за 5 варнов!")
        else:
            await message.answer_animation("https://media1.tenor.com/m/2DfpWS8cP48AAAAd/tuffnut-ruffnut.gif", 
                                           caption=f"Варн {u['nick']} ({len(u['warns'])}/5)")
    elif cmd == "бан":
        await message.chat.ban(target.id); await message.answer(f"Изгнан {u['nick']}!")
    elif cmd == "кик":
        await message.chat.ban(target.id); await message.chat.unban(target.id)
        await message.answer(f"{u['nick']} вылетел из чата!")
    elif cmd == "мут":
        until = datetime.now() + timedelta(minutes=10)
        await message.chat.restrict(target.id, permissions=types.ChatPermissions(can_send_messages=False), until_date=until)
        await message.answer(f"{u['nick']} в муте на 10 мин.")
    save_db(db)

@dp.message(F.text.lower() == "топ акт")
async def top_act(message: Message):
    sorted_u = sorted(db["users"].items(), key=lambda x: x[1]["messages"], reverse=True)[:30]
    res = "<b>🏆 Топ активности:</b>\n\n"
    for i, (uid, data) in enumerate(sorted_u, 1):
        res += f"{i}. <a href='tg://user?id={uid}'>{data['nick']}</a> — {data['messages']} мсг.\n"
    await message.answer(res)

@dp.chat_member()
async def member_update(event: ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        welcome_text = (
            "Привет!\nДобро пожаловать в Драконий край 🐲\n\n"
            "Рады видеть тебя в нашем чате. Здесь собираются люди, которым близка вселенная «Как приручить дракона».\n\n"
            "Приятного общения и хорошего дня 🐉✨"
        )
        try: await bot.send_animation(event.chat.id, "https://media1.tenor.com/m/-5D-bYxCvFAAAAAC/httyd-yeah.gif", caption=welcome_text)
        except: pass

@dp.message()
async def main_handler(msg: Message):
    if not msg.from_user or msg.from_user.is_bot: return
    u = get_u(msg.from_user.id, msg.from_user.first_name)
    u["messages"] += 1
    
    uid = str(msg.from_user.id)
    if msg.content_type in [ContentType.PHOTO, ContentType.ANIMATION, ContentType.STICKER]:
        db["media_counter"][uid] = db["media_counter"].get(uid, 0) + 1
        if uid not in db["media_history"]: db["media_history"][uid] = []
        db["media_history"][uid].append(msg.message_id)
        
        if db["media_counter"][uid] >= 5:
            until = datetime.now() + timedelta(minutes=5)
            try:
                await msg.chat.restrict(msg.from_user.id, permissions=types.ChatPermissions(can_send_messages=False), until_date=until)
                for m_id in db["media_history"][uid]:
                    try: await bot.delete_message(msg.chat.id, m_id)
                    except: pass
                await msg.answer(f"🛡 <b>{u['nick']}</b>, спам удален. Мут 5 мин.")
            except: pass
            db["media_counter"][uid] = 0
            db["media_history"][uid] = []
    else:
        db["media_counter"][uid] = 0
        db["media_history"][uid] = []
    save_db(db)

async def scheduled_msg(text, gif):
    try: await bot.send_animation(CHAT_ID, gif, caption=text)
    except: pass

async def main():
    # Запускаем веб-сервер вместе с ботом
    asyncio.create_task(start_web_server())
    
    scheduler.add_job(scheduled_msg, "cron", hour=9, minute=0, args=["Доброе утро!", "https://media1.tenor.com/m/TphIrQuFImkAAAAC/drake-how-to-train-your-dragon.gif"])
    scheduler.add_job(scheduled_msg, "cron", hour=22, minute=0, args=["Сладких снов!", "https://media1.tenor.com/m/C3P-yay4lF8AAAAC/httyd-ruffnut.gif"])
    scheduler.start()
    
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
