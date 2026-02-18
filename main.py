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
PUNISH_GIF = "https://media1.tenor.com/m/2DfpWS8cP48AAAAd/tuffnut-ruffnut.gif"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

# --- ВЕБ-СЕРВЕР ---
async def handle(request): return web.Response(text="Бот активен!")
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
        db["users"][uid] = {"nick": name, "stars": 1 if len(db["users"]) > 0 else 5, "messages": 0, "warns": []}
    return db["users"][uid]

async def check_perm(msg: Message, cmd: str):
    u = get_u(msg.from_user.id)
    req = db["permissions"].get(cmd.lower(), 1)
    if u["stars"] < req:
        await msg.reply(f"Ранг маловат! Нужно: {req} ⭐")
        return False
    return True

# --- ЛОГИКА ВАРНОВ ---

@dp.message(F.text.lower().startswith("варн"))
async def give_warn(msg: Message):
    if not await check_perm(msg, "варн"): return
    if not msg.reply_to_message: return await msg.reply("Ответь на сообщение нарушителя!")

    admin = get_u(msg.from_user.id)
    target_user = msg.reply_to_message.from_user
    u = get_u(target_user.id, target_user.first_name)

    # Извлекаем причину
    reason = msg.text[4:].strip() if len(msg.text) > 4 else "Нарушение правил"
    
    new_warn = {
        "id": len(u["warns"]) + 1,
        "reason": reason,
        "admin_name": admin["nick"],
        "admin_rank": admin["stars"],
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "expiry": (datetime.now() + timedelta(days=1)).timestamp()
    }
    
    u["warns"].append(new_warn)
    
    # Считаем только активные (не истекшие) варны
    active_warns = [w for w in u["warns"] if w["expiry"] > datetime.now().timestamp()]
    count = len(active_warns)

    save_db(db)
    
    if count >= 5:
        await msg.chat.ban(target_user.id)
        await msg.answer_animation(PUNISH_GIF, caption=f"🚀 {u['nick']} улетает в бан за 5 варнов!")
    else:
        await msg.answer_animation(PUNISH_GIF, caption=f"👊 <b>Варн выдан!</b>\nКому: {u['nick']}\nПричина: {reason}\nВсего активных: {count}/5")

@dp.message(F.text.lower() == "твои варны")
async def show_warns(msg: Message):
    if not msg.reply_to_message: return
    target = msg.reply_to_message.from_user
    u = get_u(target.id)
    
    now = datetime.now().timestamp()
    active = [w for w in u["warns"] if w["expiry"] > now]

    if not active:
        await msg.reply("У этого порядочного участника нет нарушений 🙈")
    else:
        text = f"У этого участника есть {len(active)}/5:\n"
        for i, w in enumerate(active, 1):
            text += f"<b>{i}.</b> {w['reason']} | <i>{w['date']}</i> (от {w['admin_name']})\n"
        await msg.reply(text)

@dp.message(F.text.lower().startswith("снять варн"))
async def remove_one_warn(msg: Message):
    if not await check_perm(msg, "варн"): return
    if not msg.reply_to_message: return
    
    admin = get_u(msg.from_user.id)
    u = get_u(msg.reply_to_message.from_user.id)
    
    try:
        num = int(msg.text.split()[-1]) - 1
        target_warn = [w for w in u["warns"] if w["expiry"] > datetime.now().timestamp()][num]
        
        # Проверка ранга (админ не может снять варн того, кто старше его)
        if target_warn["admin_rank"] > admin["stars"]:
            return await msg.reply("Ты не можешь снять варн, выданный более сильным драконом! 🐉")
            
        # Удаляем варн из общего списка
        u["warns"] = [w for w in u["warns"] if w != target_warn]
        save_db(db)
        await msg.reply(f"✅ Варн №{num+1} снят!")
    except:
        await msg.reply("Ошибка! Укажи правильный номер варна из списка.")

@dp.message(F.text.lower() == "снять все варны")
async def remove_all_warns(msg: Message):
    if not await check_perm(msg, "бан"): # Снимать все может только высший ранг
        return
    if not msg.reply_to_message: return
    
    u = get_u(msg.reply_to_message.from_user.id)
    u["warns"] = []
    save_db(db)
    await msg.reply("✨ Все варны участника аннулированы!")

# --- СТАНДАРТНЫЕ КОМАНДЫ ---

@dp.message(Command("кд", prefix="!"))
async def set_kd(msg: Message, command: CommandObject):
    if not await check_perm(msg, "бан"): return
    try:
        cmd_name, rank = command.args.split()
        db["permissions"][cmd_name.lower()] = int(rank)
        save_db(db)
        await msg.answer(f"✅ Команда {cmd_name} теперь доступна от {rank} ⭐")
    except: pass

@dp.message(F.text.lower() == "топ акт")
async def top_act(msg: Message):
    sorted_u = sorted(db["users"].items(), key=lambda x: x[1].get("messages", 0), reverse=True)[:15]
    res = "<b>🏆 Самые активные:</b>\n"
    for i, (uid, d) in enumerate(sorted_u, 1):
        res += f"{i}. {d['nick']} — {d.get('messages', 0)}\n"
    await msg.answer(res)

@dp.message()
async def main_handler(msg: Message):
    if not msg.from_user or msg.from_user.is_bot: return
    u = get_u(msg.from_user.id, msg.from_user.first_name)
    u["messages"] = u.get("messages", 0) + 1
    save_db(db)

async def main():
    asyncio.create_task(start_web_server())
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
                      
