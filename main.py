import asyncio
import json
import os
import re
import pytz
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, ChatMemberUpdated, ChatPermissions
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

# ==========================================
# 1. НАСТРОЙКИ
# ==========================================
TOKEN = "8463010853:AAE7piw8PFlxNCzKw9vIrmdJmTYAm1rBnuI"
CHAT_ID = -1002508735096
OWNER_ID = 7805872198  # Твой ID (Всегда 5 звезд)
DB_FILE = "dragon_data.json"

PUNISH_GIF = "https://media1.tenor.com/m/2DfpWS8cP48AAAAd/tuffnut-ruffnut.gif"
WELCOME_GIF = "https://media1.tenor.com/m/cHFxDQOITxwAAAAd/ruffnut-and-tuffnut-happiness-dragons-riders-of-berk.gif"
MORNING_GIF = "https://media1.tenor.com/m/-5D-bYxCvFAAAAAd/httyd-yeah.gif"
NIGHT_GIF = "https://media1.tenor.com/m/C3P-yay4lF8AAAAC/httyd-ruffnut.gif"

RANK_NAMES = {5: "Вожак", 4: "Совожак", 3: "Старейшина", 2: "Опытный викинг", 1: "Житель Олуха", 0: "Изгой"}

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
spam_tracker = {}

# ==========================================
# 2. РАБОТА С ДАННЫМИ
# ==========================================
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {
        "users": {}, 
        "permissions": {
            "варн": 3, "бан": 5, "мут": 3, "кик": 4, 
            "повысить": 5, "понизить": 5, "кд": 5,
            "кто я": 0, "топ акт": 0, "мои варны": 0, "твои варны": 2, "кто админ": 0
        }
    }

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_u(db, uid, name="Викинг"):
    uid_str = str(uid)
    if uid_str not in db["users"]:
        db["users"][uid_str] = {
            "nick": name, "stars": 0, "messages": 0, "warns": [], 
            "desc": "Обычный житель", "stats": {"day": 0}
        }
    if int(uid) == OWNER_ID: db["users"][uid_str]["stars"] = 5
    return db["users"][uid_str]

async def check_access(msg: Message, cmd_name: str):
    db = load_db()
    u = get_u(db, msg.from_user.id)
    req = db["permissions"].get(cmd_name.lower(), 0)
    if u["stars"] < req:
        await msg.reply(f"🛑 Уровня ранга не хватает! Нужно: {req} ⭐ ({RANK_NAMES.get(req)})")
        return False
    return True

def parse_time(text):
    hours = re.search(r'(\d+)\s*ч', text)
    minutes = re.search(r'(\d+)\s*м', text)
    h = int(hours.group(1)) if hours else 0
    m = int(minutes.group(1)) if minutes else 0
    return timedelta(hours=h, minutes=m) if (h or m) else None

# ==========================================
# 3. АДМИН-КОМАНДЫ
# ==========================================
@dp.message(F.text.lower().startswith("!кд"))
async def cmd_kd(msg: Message):
    if not await check_access(msg, "кд"): return
    try:
        parts = msg.text.split()
        db = load_db()
        db["permissions"][parts[1].lower()] = int(parts[2])
        save_db(db)
        await msg.reply(f"✅ Команда {parts[1]} теперь доступна от {parts[2]} ⭐")
    except: await msg.reply("Пример: !кд мут 3")

@dp.message(F.text.lower() == "кто админ")
async def cmd_admins(msg: Message):
    db = load_db()
    admins = [f"• {u['nick']} ({u['stars']} ⭐)" for uid, u in db["users"].items() if u["stars"] >= 2]
    await msg.answer("🛡 <b>Администрация стаи:</b>\n" + ("\n".join(admins) if admins else "Только Вожак"))

@dp.message(F.text.lower().startswith(("бан", "мут", "варн", "кик", "!бан", "!мут", "!варн", "!кик")))
async def cmd_moderate(msg: Message):
    cmd = msg.text.replace("!", "").lower().split()[0]
    if not await check_access(msg, cmd) or not msg.reply_to_message: return
    
    db = load_db(); admin = get_u(db, msg.from_user.id)
    target_user = msg.reply_to_message.from_user
    u = get_u(db, target_user.id, target_user.first_name)
    
    t_delta = parse_time(msg.text)
    reason_parts = re.sub(r'(\d+)\s*(ч|м)', '', msg.text, flags=re.I).split(maxsplit=1)
    reason = reason_parts[1] if len(reason_parts) > 1 else "причина не указана"
    t_str = f"{t_delta}" if t_delta else ("24 часа" if cmd == "варн" else "1 час")

    if cmd == "варн":
        u["warns"].append({"reason": reason, "admin": admin['nick']})
        if len(u["warns"]) >= 5:
            await msg.chat.ban(target_user.id)
            return await msg.answer("💀 Изгнание! 5/5 варнов.")
    elif cmd == "мут":
        dur = t_delta if t_delta else timedelta(hours=1)
        await msg.chat.restrict(target_user.id, permissions=ChatPermissions(can_send_messages=False), until_date=datetime.now() + dur)
    elif cmd == "бан": await msg.chat.ban(target_user.id)
    elif cmd == "кик": await msg.chat.ban(target_user.id); await msg.chat.unban(target_user.id)

    save_db(db)
    caption = f"Ты нарушил спокойствие Драконьего Края! 🐲\n\nВам выдан <b>{cmd.upper()}</b> на {t_str}\nКто выдал: {admin['nick']}\nПричина: {reason}"
    await msg.answer_animation(PUNISH_GIF, caption=caption)

@dp.message(F.text.lower().startswith("!повысить"))
async def cmd_promote(msg: Message):
    if not await check_access(msg, "повысить") or not msg.reply_to_message: return
    try:
        rank = int(msg.text.split()[-1])
        db = load_db(); target = get_u(db, msg.reply_to_message.from_user.id)
        target["stars"] = rank; save_db(db)
        await msg.reply(f"📈 {target['nick']} теперь {RANK_NAMES.get(rank)} ({rank} ⭐)")
    except: pass

@dp.message(F.text.lower().startswith("!понизить"))
async def cmd_demote(msg: Message):
    if not await check_access(msg, "понизить") or not msg.reply_to_message: return
    db = load_db(); target = get_u(db, msg.reply_to_message.from_user.id)
    target["stars"] = 0; save_db(db)
    await msg.reply(f"📉 {target['nick']} теперь Изгой (0 ⭐)")

# ==========================================
# 4. ПРОФИЛИ И ТОП
# ==========================================
@dp.message(F.text.lower().startswith(("+ник", "+описание")))
async def cmd_edit_profile(msg: Message):
    db = load_db(); u = get_u(db, msg.from_user.id)
    if "+ник" in msg.text.lower(): u["nick"] = msg.text[5:].strip()
    else: u["desc"] = msg.text[10:].strip()
    save_db(db); await msg.reply("✅ Обновлено!")

@dp.message(F.text.lower().in_(["кто я", "кто ты"]))
async def cmd_profile(msg: Message):
    db = load_db()
    target = msg.reply_to_message.from_user if (msg.reply_to_message and "ты" in msg.text.lower()) else msg.from_user
    u = get_u(db, target.id, target.first_name)
    all_u = sorted(db["users"].items(), key=lambda x: x[1].get("messages", 0), reverse=True)
    pos = next((i for i, (uid, _) in enumerate(all_u, 1) if int(uid) == target.id), "?")
    
    text = (f"👤 <b>{u['nick']}</b>\n⭐ Ранг: {u['stars']} ({RANK_NAMES.get(u['stars'])})\n"
            f"🏆 Место в топе: {pos}\n💬 Сообщений:\n  Сегодня: {u.get('stats', {}).get('day', 0)}\n"
            f"  Всего: {u['messages']}\n📝 Описание: {u.get('desc', 'Пусто')}")
    await msg.reply(text)

@dp.message(F.text.lower().in_(["мои варны", "твои варны"]))
async def cmd_warns(msg: Message):
    db = load_db()
    target = msg.reply_to_message.from_user if (msg.reply_to_message and "твои" in msg.text.lower()) else msg.from_user
    u = get_u(db, target.id)
    if not u["warns"]: return await msg.reply(f"🛡 {u['nick']} — добросовестный гражданин!")
    res = f"Варны {u['nick']} ({len(u['warns'])}/5):\n" + "\n".join([f"{i+1}. {w['reason']} ({w['admin']})" for i, w in enumerate(u['warns'])])
    await msg.reply(res)

@dp.message(F.text.lower().startswith("топ акт"))
async def cmd_top(msg: Message):
    db = load_db(); is_all = "все" in msg.text.lower()
    sort_f = (lambda x: x[1].get("messages", 0)) if is_all else (lambda x: x[1].get("stats", {}).get("day", 0))
    top = sorted(db["users"].items(), key=sort_f, reverse=True)[:30]
    res = f"<b>🏆 Топ активности ({'все' if is_all else 'сегодня'}):</b>\n"
    for i, (uid, d) in enumerate(top, 1): res += f"{i}. {d['nick']} - {sort_f((uid, d))}\n"
    await msg.answer(res)

# ==========================================
# 5. АВТОМАТИКА И АНТИСПАМ
# ==========================================
@dp.chat_member()
async def on_join(event: ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        text = "Привет! Добро пожаловать в Драконий край 🐲\n\nПриятного общения! 🐉✨"
        await bot.send_animation(event.chat.id, WELCOME_GIF, caption=text)

async def check_spam(msg: Message):
    if msg.content_type not in ['sticker', 'animation'] and not msg.text: return False
    uid = msg.from_user.id; now = datetime.now()
    data = spam_tracker.get(uid, {'count': 0, 'time': now})
    if now - data['time'] < timedelta(seconds=10): data['count'] += 1
    else: data['count'] = 1
    data['time'] = now; spam_tracker[uid] = data
    if data['count'] >= 5:
        db = load_db(); u = get_u(db, uid); u["warns"].append({"reason": "Спам", "admin": "Автобот"})
        save_db(db); await msg.delete()
        await msg.chat.restrict(uid, permissions=ChatPermissions(can_send_messages=False), until_date=now + timedelta(hours=1))
        await msg.answer(f"🚫 {u['nick']} замучен на 1 час за спам!"); return True
    return False

# ==========================================
# 6. ГЛАВНЫЙ ЦИКЛ И РАСПИСАНИЕ
# ==========================================
async def scheduler():
    tz = pytz.timezone('Europe/Moscow')
    while True:
        now = datetime.now(tz)
        if now.minute == 0:
            if now.hour == 8: await bot.send_animation(CHAT_ID, MORNING_GIF, caption="Доброе утро,Стая!🌞✨")
            elif now.hour == 21: await bot.send_animation(CHAT_ID, NIGHT_GIF, caption="Спокойной ночи,Стая!🌙🌥")
            await asyncio.sleep(61)
        await asyncio.sleep(30)

@dp.message()
async def global_handler(msg: Message):
    if not msg.from_user or msg.from_user.is_bot: return
    if await check_spam(msg): return
    db = load_db(); u = get_u(db, msg.from_user.id, msg.from_user.first_name)
    u["messages"] += 1; u["stats"]["day"] = u["stats"].get("day", 0) + 1; save_db(db)

async def main():
    asyncio.create_task(scheduler())
    app = web.Application(); app.router.add_get("/", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
