import re
from aiogram import Router, F, types
from datetime import datetime, timedelta
from database import load_db, save_db, get_u, RANK_NAMES

admin_router = Router()
GIF_URL = "https://media1.tenor.com/m/2DfpWS8cP48AAAAd/tuffnut-ruffnut.gif"

def parse_time(text):
    hours = re.search(r'(\d+)\s*ч', text)
    minutes = re.search(r'(\d+)\s*м', text)
    h = int(hours.group(1)) if hours else 0
    m = int(minutes.group(1)) if minutes else 0
    return timedelta(hours=h, minutes=m) if (h or m) else None

async def check_access(msg, cmd_name):
    db = load_db()
    u = get_u(db, msg.from_user.id)
    required = db["permissions"].get(cmd_name.lower(), 0)
    if u["stars"] < required:
        await msg.reply(f"🛑 Уровня ранга не хватает! Нужно: {required} ⭐")
        return False
    return True

@admin_router.message(F.text.lower().startswith("!кд"))
async def cmd_set_kd(msg: types.Message):
    if not await check_access(msg, "кд"): return
    try:
        parts = msg.text.split()
        db = load_db()
        db["permissions"][parts[1].lower()] = int(parts[2])
        save_db(db)
        await msg.reply(f"✅ Команда {parts[1]} теперь доступна от {parts[2]} ⭐")
    except: await msg.reply("Пример: !кд мут 3")

@admin_router.message(F.text.lower() == "кто админ")
async def show_admins(msg: types.Message):
    db = load_db()
    admins = [f"{u['nick']} ({u['stars']} ⭐)" for uid, u in db["users"].items() if u["stars"] >= 2]
    await msg.answer("🛡 <b>Администрация стаи:</b>\n" + "\n".join(admins))

@admin_router.message(F.text.lower().startswith(("бан", "мут", "варн", "кик", "!бан", "!мут", "!варн", "!кик")))
async def moderate(msg: types.Message):
    raw_cmd = msg.text.replace("!", "").lower().split()[0]
    if not await check_access(msg, raw_cmd) or not msg.reply_to_message: return
    
    db = load_db()
    admin = get_u(db, msg.from_user.id)
    target_user = msg.reply_to_message.from_user
    u = get_u(db, target_user.id, target_user.first_name)
    
    t_delta = parse_time(msg.text)
    reason_parts = re.sub(r'(\d+)\s*(ч|м)', '', msg.text, flags=re.I).split(maxsplit=1)
    reason = reason_parts[1] if len(reason_parts) > 1 else "причина не указана"
    
    if raw_cmd == "варн":
        u["warns"].append({"reason": reason, "admin": admin['nick']})
        if len(u["warns"]) >= 5:
            await msg.chat.ban(target_user.id)
            await msg.answer(f"💀 {u['nick']} забанен (максимум варнов)!")
    elif raw_cmd == "мут":
        dur = t_delta if t_delta else timedelta(hours=1)
        await msg.chat.restrict(target_user.id, permissions=types.ChatPermissions(can_send_messages=False), 
                                until_date=datetime.now() + dur)
    elif raw_cmd == "бан": await msg.chat.ban(target_user.id)
    elif raw_cmd == "кик": 
        await msg.chat.ban(target_user.id)
        await msg.chat.unban(target_user.id)

    save_db(db)
    await msg.answer_animation(GIF_URL, caption=f"Ты нарушил спокойствие Драконьего Края! 🐲\nВыдан <b>{raw_cmd.upper()}</b>\nКто: {admin['nick']}\nПричина: {reason}")
    
