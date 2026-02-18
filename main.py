import asyncio
import json
import os
import re
import pytz
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, ChatMemberUpdated, ChatPermissions
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.markdown import hlink
from aiohttp import web

# ==========================================
# 1. НАСТРОЙКИ
# ==========================================
TOKEN = "8463010853:AAE7piw8PFlxNCzKw9vIrmdJmTYAm1rBnuI"
CHAT_ID = -1002508735096
OWNER_ID = 7805872198
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
    return {"users": {}, "permissions": {}, "last_reset": datetime.now().strftime("%Y-%m-%d")}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def check_reset(db):
    tz = pytz.timezone('Europe/Moscow')
    today = datetime.now(tz).strftime("%Y-%m-%d")
    if db.get("last_reset") != today:
        for u in db["users"].values():
            if "stats" in u: u["stats"]["day"] = 0
        db["last_reset"] = today
        return True
    return False

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
    perms = {
        "варн": 3, "бан": 5, "разбан": 4, "мут": 3, "размут": 3, "кик": 4, 
        "повысить": 5, "понизить": 5, "кд": 5, "кто я": 0, "топ акт": 0, "список команд": 0
    }
    req = db.get("permissions", {}).get(cmd_name.lower(), perms.get(cmd_name.lower(), 0))
    if u["stars"] < req:
        await msg.reply(f"🛑 Уровня ранга не хватает! Нужно: {req} ⭐")
        return False
    return True

def parse_args(text):
    time_match = re.search(r'(\d+)\s*(ч|м)', text, flags=re.I)
    t_delta = None
    if time_match:
        val = int(time_match.group(1))
        unit = time_match.group(2).lower()
        t_delta = timedelta(hours=val) if unit == 'ч' else timedelta(minutes=val)
    
    clean_text = re.sub(r'(\d+)\s*(ч|м)', '', text, flags=re.I).split()
    reason = "Нарушение"
    if len(clean_text) > 1:
        reason = " ".join(clean_text[1:])
    return reason, t_delta

# ==========================================
# 3. КОМАНДЫ
# ==========================================
@dp.message(F.text.lower() == "список команд")
async def cmd_list(msg: Message):
    if not await check_access(msg, "список команд"): return
    text = (
        "📜 <b>Список команд Драконьего Края:</b>\n\n"
        "👤 <b>Профиль:</b>\n"
        "• Кто я / Кто ты — карточка викинга\n"
        "• +ник [текст] / +описание [текст]\n"
        "• Мои варны / Твои варны\n"
        "• Топ акт / Топ акт все\n\n"
        "⚖ <b>Модерация (ответ на сообщение):</b>\n"
        "• мут [причина] [время] / размут\n"
        "• варн [причина] [время] — 5 варнов = бан\n"
        "• бан [причина] / разбан — изгнание\n"
        "• кик [причина] — исключение\n\n"
        "⚙ <b>Админ:</b>\n"
        "• !повысить/!понизить [ранг]\n"
        "• !кд [команда] [ранг]\n"
        "• кто админ — список модераторов"
    )
    await msg.answer(text)

@dp.message(F.text.lower() == "размут")
async def cmd_unmute(msg: Message):
    if not await check_access(msg, "мут") or not msg.reply_to_message: return
    target = msg.reply_to_message.from_user
    await msg.chat.restrict(target.id, permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
    await msg.reply(f"🔊 Голос викинга {hlink(target.first_name, f'tg://user?id={target.id}')} снова слышен!")

@dp.message(F.text.lower() == "разбан")
async def cmd_unban(msg: Message):
    if not await check_access(msg, "разбан") or not msg.reply_to_message: return
    target = msg.reply_to_message.from_user
    await msg.chat.unban(target.id)
    await msg.reply(f"🕊 Викинг {hlink(target.first_name, f'tg://user?id={target.id}')} помилован!")

@dp.message(F.text.lower().startswith(("бан", "мут", "варн", "кик", "!бан", "!мут", "!варн", "!кик")))
async def cmd_moderate(msg: Message):
    cmd = msg.text.replace("!", "").lower().split()[0]
    if not await check_access(msg, cmd) or not msg.reply_to_message: return
    
    db = load_db(); admin = get_u(db, msg.from_user.id)
    target = msg.reply_to_message.from_user
    u = get_u(db, target.id, target.first_name)
    
    reason, t_delta = parse_args(msg.text)
    dur = t_delta if t_delta else timedelta(hours=1)
    
    if cmd == "варн":
        u["warns"].append({"reason": reason, "admin": admin['nick']})
        if len(u["warns"]) >= 5:
            await msg.chat.ban(target.id)
            return await msg.answer("💀 5/5 варнов! Изгнан навсегда.")
    elif cmd == "мут":
        await msg.chat.restrict(target.id, permissions=ChatPermissions(can_send_messages=False), until_date=datetime.now() + dur)
    elif cmd == "бан": await msg.chat.ban(target.id)
    elif cmd == "кик": await msg.chat.ban(target.id); await msg.chat.unban(target.id)

    save_db(db)
    user_link = hlink(u['nick'], f"tg://user?id={target.id}")
    caption = f"Нарушение покоя! 🐲\n\n<b>{cmd.upper()}</b> для {user_link}\nПричина: {reason}\nСрок: {dur if t_delta else '1 час (стандарт)'}"
    await msg.answer_animation(PUNISH_GIF, caption=caption)

@dp.message(F.text.lower().startswith("!кд"))
async def cmd_kd(msg: Message):
    if not await check_access(msg, "кд"): return
    try:
        parts = msg.text.split()
        db = load_db(); db["permissions"][parts[1].lower()] = int(parts[2]); save_db(db)
        await msg.reply(f"✅ Команда {parts[1]} теперь доступна от {parts[2]} ⭐")
    except: pass

@dp.message(F.text.lower().in_(["кто я", "кто ты"]))
async def cmd_profile(msg: Message):
    db = load_db()
    target = msg.reply_to_message.from_user if (msg.reply_to_message and "ты" in msg.text.lower()) else msg.from_user
    u = get_u(db, target.id, target.first_name)
    user_link = hlink(u['nick'], f"tg://user?id={target.id}")
    all_u = sorted(db["users"].items(), key=lambda x: x[1].get("messages", 0), reverse=True)
    pos = next((i for i, (uid, _) in enumerate(all_u, 1) if int(uid) == target.id), "?")
    text = (f"👤 <b>{user_link}</b>\n⭐ Ранг: {u['stars']} ({RANK_NAMES.get(u['stars'])})\n"
            f"🏆 Место в топе: {pos}\n💬 Сообщений:\n  Сегодня: {u.get('stats', {}).get('day', 0)}\n"
            f"  Всего: {u['messages']}\n📝 Описание: {u.get('desc', 'Пусто')}")
    await msg.reply(text)

@dp.message(F.text.lower().startswith("топ акт"))
async def cmd_top(msg: Message):
    db = load_db(); is_all = "все" in msg.text.lower(); check_reset(db)
    sort_f = (lambda x: x[1].get("messages", 0)) if is_all else (lambda x: x[1].get("stats", {}).get("day", 0))
    top = sorted(db["users"].items(), key=sort_f, reverse=True)[:30]
    res = f"<b>🏆 Топ активности ({'все' if is_all else 'сегодня'}):</b>\n"
    for i, (uid, d) in enumerate(top, 1):
        res += f"{i}. {hlink(d['nick'], f'tg://user?id={uid}')} - {sort_f((uid, d))}\n"
    await msg.answer(res)

@dp.message(F.text.lower().startswith(("+ник", "+описание")))
async def cmd_edit_profile(msg: Message):
    db = load_db(); u = get_u(db, msg.from_user.id)
    if "+ник" in msg.text.lower(): u["nick"] = msg.text[5:].strip()
    else: u["desc"] = msg.text[10:].strip()
    save_db(db); await msg.reply("✅ Обновлено!")

# ==========================================
# 4. АВТОМАТИКА И АНТИСПАМ
# ==========================================
@dp.chat_member()
async def on_join(event: ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        text = ("Привет!\nДобро пожаловать в Драконий край 🐲\n\nРады видеть тебя в нашем чате. Здесь собираются люди, которым близка вселенная «Как приручить дракона»...\n\nПриятного общения! 🐉✨")
        await bot.send_animation(event.chat.id, WELCOME_GIF, caption=text)

async def check_spam(msg: Message):
    if msg.content_type not in ['sticker', 'animation'] and not (msg.text and re.search(r'[\U00010000-\U0010ffff]', msg.text)): return False
    uid = msg.from_user.id; now = datetime.now()
    data = spam_tracker.get(uid, {'count': 0, 'msgs': [], 'last_time': now})
    if now - data['last_time'] < timedelta(seconds=10): data['count'] += 1
    else: data['count'] = 1
    data['msgs'].append(msg.message_id); data['last_time'] = now; spam_tracker[uid] = data
    if data['count'] >= 5:
        for m_id in data['msgs']: 
            try: await bot.delete_message(msg.chat.id, m_id)
            except: pass
        db = load_db(); u = get_u(db, uid); u["warns"].append({"reason": "Спам", "admin": "Автобот"}); save_db(db)
        await msg.chat.restrict(uid, permissions=ChatPermissions(can_send_messages=False), until_date=now + timedelta(hours=1))
        await msg.answer(f"🚫 {u['nick']} замучен за спам. Все сообщения удалены."); return True
    return False

# ==========================================
# 5. ЗАПУСК И РАСПИСАНИЕ
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
    db = load_db(); check_reset(db)
    u = get_u(db, msg.from_user.id, msg.from_user.first_name)
    u["messages"] += 1; u["stats"]["day"] = u["stats"].get("day", 0) + 1; save_db(db)

async def main():
    asyncio.create_task(scheduler())
    app = web.Application(); app.router.add_get("/", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
