import re
from aiogram import Router, F, types
from aiogram.filters import Command
from datetime import datetime, timedelta
from database import load_db, save_db, get_u, RANK_NAMES, OWNER_ID

admin_router = Router()
GIF_URL = "https://media1.tenor.com/m/2DfpWS8cP48AAAAd/tuffnut-ruffnut.gif"

def parse_time(text):
    # Поиск часов и минут в тексте
    hours = re.search(r'(\d+)\s*ч', text)
    minutes = re.search(r'(\d+)\s*м', text)
    h = int(hours.group(1)) if hours else 0
    m = int(minutes.group(1)) if minutes else 0
    if h == 0 and m == 0: return None
    return timedelta(hours=h, minutes=m)

async def check_access(msg, cmd_name):
    db = load_db()
    u = get_u(db, msg.from_user.id)
    required = db["permissions"].get(cmd_name.lower(), 0)
    if u["stars"] < required:
        await msg.reply(f"🛑 Уровня ранга не хватает! Требуется: {required} ⭐ ({RANK_NAMES.get(required)})")
        return False
    return True

@admin_router.message(F.text.lower().startswith("!кд"))
async def cmd_set_kd(msg: types.Message):
    if not await check_access(msg, "кд"): return
    try:
        parts = msg.text.split()
        cmd_to_lock = parts[1].lower()
        rank_needed = int(parts[2])
        db = load_db()
        db["permissions"][cmd_to_lock] = rank_needed
        save_db(db)
        await msg.reply(f"✅ Команда <b>{cmd_to_lock}</b> теперь доступна от {rank_needed} ⭐")
    except: await msg.reply("Пример: !кд мут 4")

@admin_router.message(F.text.lower().startswith(("бан", "мут", "варн", "кик", "!бан", "!мут", "!варн", "!кик")))
async def moderate(msg: types.Message):
    raw_text = msg.text.replace("!", "").lower()
    cmd = raw_text.split()[0]
    if not await check_access(msg, cmd) or not msg.reply_to_message: return

    db = load_db()
    admin = get_u(db, msg.from_user.id)
    target_node = msg.reply_to_message.from_user
    u = get_u(db, target_node.id, target_node.first_name)
    
    # Парсинг времени и причины
    time_delta = parse_time(msg.text)
    reason_search = re.sub(r'(\d+)\s*(ч|м)', '', msg.text, flags=re.I).split(maxsplit=1)
    reason = reason_search[1] if len(reason_search) > 1 else "причина не указана"
    
    time_str = "24 часа" if cmd == "варн" else ("1 час" if not time_delta else f"{time_delta}")
    
    if cmd == "варн":
        u["warns"].append({"reason": reason, "admin": admin['nick'], "date": datetime.now().strftime("%d.%m")})
        if len(u["warns"]) >= 5:
            await msg.chat.ban(target_node.id)
            await msg.answer(f"🚀 {u['nick']} получил 5-й варн и отправлен в изгнание (Бан)!")
    elif cmd == "мут":
        until = datetime.now() + (time_delta if time_delta else timedelta(hours=1))
        await msg.chat.restrict(target_node.id, permissions=types.ChatPermissions(can_send_messages=False), until_date=until)

    save_db(db)
    text = (f"Ты нарушил спокойствие Драконьего Края! 🐲\n\n"
            f"Вам выдаётся <b>{cmd.upper()}</b> на <b>{time_str}</b>\n"
            f"Кто выдал: {msg.from_user.mention_html()}\n"
            f"Причина: {reason}")
    await msg.answer_animation(GIF_URL, caption=text)

@admin_router.message(F.text.lower().startswith("!повысить"))
async def promote(msg: types.Message):
    if not await check_access(msg, "повысить") or not msg.reply_to_message: return
    try:
        rank = int(msg.text.split()[-1])
        db = load_db()
        target = get_u(db, msg.reply_to_message.from_user.id)
        target["stars"] = rank
        save_db(db)
        await msg.reply(f"📈 Викинг {target['nick']} повышен до уровня {rank} ⭐")
    except: pass

@admin_router.message(F.text.lower().startswith("!понизить"))
async def demote(msg: types.Message):
    if not await check_access(msg, "понизить") or not msg.reply_to_message: return
    db = load_db()
    target = get_u(db, msg.reply_to_message.from_user.id)
    target["stars"] = 0
    save_db(db)
    await msg.reply(f"📉 Викинг {target['nick']} понижен до Изгоя (0 ⭐)")
      
