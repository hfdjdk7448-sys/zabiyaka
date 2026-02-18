import asyncio
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, ChatMemberUpdated, ContentType
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

# --- НАСТРОЙКИ ---
TOKEN = "8463010853:AAE7piw8PFlxNCzKw9vIrmdJmTYAm1rBnuI"
CHAT_ID = -1002508735096  
OWNER_ID = 7457754972  # Твой ID
OWNER_HANDLE = "@odos765" 
DB_FILE = "dragon_data.json"

PUNISH_GIF = "https://media1.tenor.com/m/2DfpWS8cP48AAAAd/tuffnut-ruffnut.gif"
WELCOME_GIF = "https://media1.tenor.com/m/-5D-bYxCvFAAAAAC/httyd-yeah.gif"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# --- ВЕБ-СЕРВЕР ---
async def handle(request): return web.Response(text="Бот Стаи активен!")
async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()

# --- БАЗА ДАННЫХ ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"users": {}, "permissions": {"варн": 3, "бан": 5, "мут": 4, "кик": 3}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

def get_u(uid, name="Викинг"):
    uid = str(uid)
    if uid not in db["users"]:
        db["users"][uid] = {
            "nick": name, 
            "stars": 5 if int(uid) == OWNER_ID else 1, 
            "messages": 0, "warns": [], "desc": "Обычный житель Олуха",
            "joined": datetime.now().strftime("%d.%m.%Y"), "stats": {"day": 0}
        }
    if int(uid) == OWNER_ID: 
        db["users"][uid]["stars"] = 5
        db["users"][uid]["nick"] = OWNER_HANDLE # Автоматически ставим твой ник
    return db["users"][uid]

async def check_perm(msg: Message, cmd: str):
    u = get_u(msg.from_user.id)
    req = db["permissions"].get(cmd.lower(), 1)
    if u["stars"] < req:
        await msg.reply(f"Ранг маловат! Нужно минимум {req} ⭐")
        return False
    return True

# --- КОМАНДА: КТО АДМИН (ИСПРАВЛЕНО) ---
@dp.message(F.text.lower() == "кто админ")
async def show_admins(msg: Message):
    # Фильтруем тех, у кого есть звезды, и сортируем по убыванию (от 5 до 1)
    admins = [
        (uid, u) for uid, u in db["users"].items() 
        if u.get("stars", 0) >= 1 
    ]
    # Сортировка: сначала те, у кого больше звезд
    admins.sort(key=lambda x: x[1].get("stars", 0), reverse=True)

    if not admins:
        return await msg.answer("В стае пока нет иерархии.")

    res = "<b>📜 Иерархия Драконьего Края:</b>\n"
    res += "━━━━━━━━━━━━━━\n"
    
    for uid, u in admins:
        star_icon = "👑" if u['stars'] == 5 else "🛡"
        res += f"{star_icon} {u['nick']} — <b>{u['stars']} ⭐</b>\n"
    
    res += "━━━━━━━━━━━━━━"
    await msg.answer(res)

# --- МОДЕРАЦИЯ (ГИФ + ТВОЙ ТЕКСТ) ---
@dp.message(F.text.lower().startswith(("бан", "мут", "варн", "кик", "!бан", "!мут", "!варн", "!кик")))
async def moderate(msg: Message):
    text_parts = msg.text.lower().replace("!", "").split()
    cmd = text_parts[0]
    if not await check_perm(msg, cmd): return
    if not msg.reply_to_message: return await msg.reply("Нужен ответ на сообщение нарушителя!")
    
    admin = get_u(msg.from_user.id)
    target_user = msg.reply_to_message.from_user
    u = get_u(target_user.id, target_user.first_name)
    
    reason = " ".join(msg.text.split()[1:]) if len(msg.text.split()) > 1 else "Нарушение правил"
    duration = "бессрочно"
    action_name = ""

    if cmd == "варн":
        action_name = "Варн"; duration = "24 часа"
        u["warns"].append({"reason": reason, "admin": admin["nick"], "expiry": (datetime.now() + timedelta(days=1)).timestamp()})
        if len([w for w in u["warns"] if w["expiry"] > datetime.now().timestamp()]) >= 5:
            await msg.chat.ban(target_user.id); action_name = "Бан (5/5 варнов)"
    elif cmd == "мут":
        action_name = "Мут"; duration = "15 минут"
        await msg.chat.restrict(target_user.id, permissions=types.ChatPermissions(can_send_messages=False), until_date=datetime.now() + timedelta(minutes=15))
    elif cmd == "бан":
        action_name = "Бан"; await msg.chat.ban(target_user.id)
    elif cmd == "кик":
        action_name = "Кик"; duration = "моментально"
        await msg.chat.ban(target_user.id); await msg.chat.unban(target_user.id)

    save_db(db)
    caption = f"Вы нарушаете спокойствие Драконьего Края! 😡\n\nВам выдан <b>{action_name}</b> на <b>({duration})</b>\n<b>Причина:</b> {reason}\n<b>Кто выдал:</b> {admin['nick']}"
    await msg.answer_animation(PUNISH_GIF, caption=caption)

# --- КАРТОЧКА КТО Я ---
@dp.message(F.text.lower() == "кто я")
async def who_am_i(msg: Message):
    u = get_u(msg.from_user.id, msg.from_user.first_name)
    all_u = sorted(db["users"].items(), key=lambda x: x[1].get("messages", 0), reverse=True)
    pos = next((i for i, (uid, _) in enumerate(all_u, 1) if int(uid) == msg.from_user.id), 0)
    text = (
        f"<b>📜 Карточка Викинга</b>\n━━━━━━━━━━━━━━\n"
        f"👤 <b>Ник:</b> {u['nick']}\n⭐ <b>Ранг:</b> {u['stars']} звезд\n"
        f"🏆 <b>Место в топе:</b> {pos}\n━━━━━━━━━━━━━━\n"
        f"💬 <b>Сообщений:</b>\n• Всего: {u['messages']}\n• За сегодня: {u['stats'].get('day', 0)}\n"
        f"━━━━━━━━━━━━━━\n📝 <b>Описание:</b>\n<i>{u.get('desc', 'Пусто')}</i>"
    )
    await msg.reply(text)

@dp.message(F.text.lower().startswith("+описание"))
async def set_desc(msg: Message):
    u = get_u(msg.from_user.id); u["desc"] = msg.text[10:].strip()[:150]
    save_db(db); await msg.reply("✅ Описание обновлено!")

@dp.message(F.text.lower() == "топ акт")
async def show_top(msg: Message):
    top = sorted(db["users"].items(), key=lambda x: x[1].get("messages", 0), reverse=True)[:15]
    res = "<b>🏆 Топ активности:</b>\n\n"
    for i, (uid, d) in enumerate(top, 1): res += f"{i}. {d['nick']} — {d.get('messages', 0)} мсг.\n"
    await msg.answer(res)

# --- ПРИВЕТСТВИЕ ---
@dp.chat_member()
async def welcome(event: ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        text = "Привет!\nДобро пожаловать в Драконий край 🐲\n\nРады видеть тебя в нашем чате. Здесь собираются люди, которым близка вселенная «Как приручить дракона».\n\nЧувствуй себя комфортно, будем рады твоему присутствию 😀\nПриятного общения и хорошего дня 🐉✨"
        try: await bot.send_animation(event.chat.id, WELCOME_GIF, caption=text)
        except: pass

# --- ОБРАБОТЧИК ---
@dp.message()
async def h(msg: Message):
    if not msg.from_user or msg.from_user.is_bot: return
    u = get_u(msg.from_user.id, msg.from_user.first_name)
    u["messages"] += 1
    u["stats"]["day"] = u["stats"].get("day", 0) + 1
    save_db(db)

async def main():
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
            
