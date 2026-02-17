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
# Гифка со злым Задиракой
PUNISH_GIF = "https://media1.tenor.com/m/2DfpWS8cP48AAAAd/tuffnut-ruffnut.gif"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

# --- ВЕБ-СЕРВЕР ДЛЯ ПОДДЕРЖКИ ЖИЗНИ ---
async def handle(request):
    return web.Response(text="Бот Стаи активен!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- ЛОГИКА БАЗЫ ДАННЫХ ---
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
        # Если это самый первый пользователь в истории бота — даем 5 звезд (Вожак)
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

# --- КОМАНДЫ МОДЕРАЦИИ С ГИФКОЙ ---
@dp.message(Command("бан", "мут", "варн", "кик", prefix="!"))
async def moderate(message: Message):
    cmd = message.text[1:].split()[0].lower()
    if not await has_access(message, cmd): return
    if not message.reply_to_message: return await message.reply("Целься точнее! Нужно ответить на сообщение нарушителя")
    
    target = message.reply_to_message.from_user
    u = get_u(target.id, target.first_name)
    
    # Текст для гифки
    action_text = ""
    if cmd == "варн":
        u["warns"].append(datetime.now().strftime("%d.%m %H:%M"))
        action_text = f"Викинг {u['nick']} получил взбучку от близнецов! Варн ({len(u['warns'])}/5)"
        if len(u["warns"]) >= 5:
            await message.chat.ban(target.id)
            action_text = f"Всё, {u['nick']} доигрался! Близнецы вышвырнули его из чата за 5 варнов!"
    elif cmd == "бан":
        await message.chat.ban(target.id)
        action_text = f"Задирака в ярости! {u['nick']} отправлен в изгнание навсегда!"
    elif cmd == "кик":
        await message.chat.ban(target.id); await message.chat.unban(target.id)
        action_text = f"Лети отсюда, {u['nick']}! И не возвращайся, пока не научишься правилам!"
    elif cmd == "мут":
        until = datetime.now() + timedelta(minutes=15)
        await message.chat.restrict(target.id, permissions=types.ChatPermissions(can_send_messages=False), until_date=until)
        action_text = f"Тссс! Близнецы заклеили рот викингу {u['nick']} на 15 минут за плохое поведение!"

    save_db(db)
    await message.answer_animation(PUNISH_GIF, caption=f"<b>УДАР БЛИЗНЕЦОВ!</b> 👊🔥\n\n{action_text}")

# --- ОСТАЛЬНЫЕ КОМАНДЫ ---
@dp.message(F.text.lower() == "кто админ")
async def who_is_admin(message: Message):
    admins = [f"• <a href='tg://user?id={uid}'>{u['nick']}</a> — {u['stars']} ⭐" for uid, u in db["users"].items() if u["stars"] >= 2]
    resp = "<b>📜 Старейшины и Вожаки Драконьего Края:</b>\n\n" + "\n".join(admins) if admins else "В этой стае пока нет старейшин."
    await message.answer(resp)

@dp.message(F.text.lower() == "топ акт")
async def top_act(message: Message):
    # Берем всех юзеров и сортируем по сообщениям
    sorted_u = sorted(db["users"].items(), key=lambda x: x[1].get("messages", 0), reverse=True)[:20]
    res = "<b>🏆 Самые активные викинги Стаи:</b>\n<i>(Статистика копится бесконечно)</i>\n\n"
    for i, (uid, data) in enumerate(sorted_u, 1):
        res += f"{i}. <a href='tg://user?id={uid}'>{data['nick']}</a> — {data.get('messages', 0)} сообщ.\n"
    await message.answer(res)

@dp.message(Command("повысить", prefix="!"))
async def promote_user(message: Message, command: CommandObject):
    if not await has_access(message, "повысить"): return
    if not message.reply_to_message: return
    target = message.reply_to_message.from_user
    u = get_u(target.id, target.first_name)
    u["stars"] = min(u["stars"] + 1, 5)
    if command.args and command.args.isdigit(): u["stars"] = min(int(command.args), 5)
    save_db(db)
    await message.answer(f"📈 Ранг викинга <b>{u['nick']}</b> теперь {u['stars']} ⭐")

# --- ПРИВЕТСТВИЕ ---
@dp.chat_member()
async def member_update(event: ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        welcome = "Привет! Добро пожаловать в Драконий край 🐲\nЧувствуй себя как дома!"
        try: await bot.send_animation(event.chat.id, "https://media1.tenor.com/m/-5D-bYxCvFAAAAAC/httyd-yeah.gif", caption=welcome)
        except: pass

# --- ГЛАВНЫЙ ОБРАБОТЧИК ---
@dp.message()
async def main_handler(msg: Message):
    if not msg.from_user or msg.from_user.is_bot: return
    
    # Регистрация сообщения в статистику (БЕЗ ОБНУЛЕНИЯ)
    u = get_u(msg.from_user.id, msg.from_user.first_name)
    u["messages"] = u.get("messages", 0) + 1
    
    # Антиспам медиа
    uid = str(msg.from_user.id)
    if msg.content_type in [ContentType.PHOTO, ContentType.ANIMATION, ContentType.STICKER]:
        db["media_counter"][uid] = db["media_counter"].get(uid, 0) + 1
        if uid not in db["media_history"]: db["media_history"][uid] = []
        db["media_history"][uid].append(msg.message_id)
        
        if db["media_counter"][uid] >= 6:
            try:
                until = datetime.now() + timedelta(minutes=5)
                await msg.chat.restrict(msg.from_user.id, permissions=types.ChatPermissions(can_send_messages=False), until_date=until)
                for m_id in db["media_history"][uid]:
                    try: await bot.delete_message(msg.chat.id, m_id)
                    except: pass
                await msg.answer_animation(PUNISH_GIF, caption=f"🛡 {u['nick']} завалил чат мусором! Близнецы всё прибрали, а хулиган в муте.")
            except: pass
            db["media_counter"][uid] = 0
            db["media_history"][uid] = []
    else:
        db["media_counter"][uid] = 0
        db["media_history"][uid] = []
    
    save_db(db)

async def main():
    asyncio.create_task(start_web_server())
    scheduler.start()
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
