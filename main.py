import asyncio
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, ChatMemberUpdated, ContentType
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- НАСТРОЙКИ ---
TOKEN = "8463010853:AAE7piw8PFlxNCzKw9vIrmdJmTYAm1rBnuI"
CHAT_ID = -1002508735096  
DB_FILE = "dragon_data.json"

# Инициализация бота БЕЗ прокси
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

# --- ЛОГИКА БАЗЫ ДАННЫХ ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            return json.load(open(DB_FILE, "r", encoding="utf-8"))
        except:
            pass
    return {
        "users": {}, 
        "permissions": {"бан": 5, "мут": 4, "варн": 3, "кик": 3, "кд": 5},
        "spam_limit": 5,
        "media_counter": {}
    }

def save_db(data):
    json.dump(data, open(DB_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=4)

db = load_db()

def get_u(uid, name="Викинг"):
    uid = str(uid)
    if uid not in db["users"]:
        # Если это вообще первый пользователь в базе — он становится Вожаком (5 звезд)
        is_first = len(db["users"]) == 0
        db["users"][uid] = {
            "nick": name, 
            "stars": 5 if is_first else 1, 
            "messages": 0, 
            "warns": []
        }
        save_db(db)
    return db["users"][uid]

# --- ПРОВЕРКА ПРАВ ---
async def has_access(message: Message, cmd_name: str):
    u = get_u(message.from_user.id)
    required = db["permissions"].get(cmd_name.lower(), 1)
    if u["stars"] < required:
        await message.reply(f"Ошибка доступа! 🚫\nТвой ранг: {u['stars']} ⭐\nНужно: {required} ⭐")
        return False
    return True

# --- КОМАНДЫ ---

@dp.message(F.text.lower() == "кто админ")
async def who_is_admin(message: Message):
    admins = []
    for uid, u in db["users"].items():
        if u["stars"] >= 2:
            admins.append(f"• <a href='tg://user?id={uid}'>{u['nick']}</a> — {u['stars']} ⭐")
    resp = "<b>📜 Администрация Стаи:</b>\n" + "\n".join(admins) if admins else "В стае пока только один Вожак."
    await message.answer(resp)

@dp.message(Command("кд"))
async def setup_kd(message: Message, command: CommandObject):
    if not await has_access(message, "кд"): return
    try:
        args = command.args.split()
        cmd, rank = args[0].lower(), int(args[1])
        db["permissions"][cmd] = rank
        save_db(db)
        await message.answer(f"✅ Команда <b>{cmd}</b> теперь доступна от {rank} ⭐")
    except:
        await message.answer("Ошибка! Пиши: <code>кд бан 5</code>")

@dp.message(F.text.startswith("+ник "))
async def set_nick(message: Message):
    new_nick = message.text[5:].strip()
    if len(new_nick) > 20: return await message.reply("Ник слишком длинный!")
    u = get_u(message.from_user.id)
    u["nick"] = new_nick
    save_db(db)
    await message.answer(f"Теперь ты известен как <b>{new_nick}</b>")

@dp.message(F.text.lower() == "топ акт")
async def top_act(message: Message):
    sorted_u = sorted(db["users"].items(), key=lambda x: x[1]["messages"], reverse=True)[:30]
    res = "<b>🏆 Топ активности викингов:</b>\n\n"
    for i, (uid, data) in enumerate(sorted_u, 1):
        res += f"{i}. <a href='tg://user?id={uid}'>{data['nick']}</a> — ({data['messages']})\n"
    await message.answer(res)

@dp.message(Command("бан", "мут", "варн", prefix="!"))
async def moderate(message: Message):
    cmd = message.text[1:].split()[0].lower()
    if not await has_access(message, cmd): return
    if not message.reply_to_message: return await message.reply("Нужен ответ на сообщение!")
    
    target = message.reply_to_message.from_user
    u = get_u(target.id)
    
    if cmd == "варн":
        u["warns"].append(datetime.now().strftime("%d.%m %H:%M"))
        if len(u["warns"]) >= 5:
            await message.chat.ban(target.id)
            await message.answer(f"Викинг {u['nick']} изгнан за 5 варнов!")
        else:
            await message.answer_animation("https://media1.tenor.com/m/2DfpWS8cP48AAAAd/tuffnut-ruffnut.gif", 
                                           caption=f"Викинг {u['nick']} получил варн! ({len(u['warns'])}/5)")
    elif cmd == "бан":
        await message.chat.ban(target.id)
        await message.answer(f"Вожак изгнал {u['nick']}!")
    elif cmd == "мут":
        until = datetime.now() + timedelta(minutes=10)
        await message.chat.restrict(target.id, permissions=types.ChatPermissions(can_send_messages=False), until_date=until)
        await message.answer(f"{u['nick']} замолчал на 10 минут.")
    save_db(db)

# --- АНТИСПАМ И СЧЕТЧИК ---
@dp.message()
async def main_handler(msg: Message):
    if not msg.from_user or msg.from_user.is_bot: return
    u = get_u(msg.from_user.id, msg.from_user.first_name)
    u["messages"] += 1
    
    uid = str(msg.from_user.id)
    is_media = msg.content_type in [ContentType.PHOTO, ContentType.ANIMATION, ContentType.STICKER]
    
    if is_media:
        db["media_counter"][uid] = db["media_counter"].get(uid, 0) + 1
        if db["media_counter"][uid] >= 5:
            u["warns"].append("Авто-варн: Спам медиа")
            until = datetime.now() + timedelta(minutes=1)
            try:
                await msg.chat.restrict(msg.from_user.id, permissions=types.ChatPermissions(can_send_messages=False), until_date=until)
                await msg.reply("🛡 Антиспам: Мут на 1 мин + Варн.")
            except: pass
            db["media_counter"][uid] = 0
    else:
        db["media_counter"][uid] = 0
    save_db(db)

# --- ПРИВЕТСТВИЯ ---
@dp.chat_member()
async def member_update(event: ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        text = "Привет!\nДобро пожаловать в Драко
  
