from aiogram import Router, F, types
from database import load_db, save_db, get_u, RANK_NAMES

profile_router = Router()

@profile_router.message(F.text.lower().startswith(("+ник", "+описание")))
async def edit_profile(msg: types.Message):
    db = load_db()
    u = get_u(db, msg.from_user.id)
    if "+ник" in msg.text.lower():
        u["nick"] = msg.text[5:].strip()
    else:
        u["desc"] = msg.text[10:].strip()
    save_db(db)
    await msg.reply("✅ Данные профиля обновлены!")

@profile_router.message(F.text.lower().in_(["кто я", "кто ты"]))
async def show_profile(msg: types.Message):
    db = load_db()
    target = msg.reply_to_message.from_user if (msg.reply_to_message and "ты" in msg.text.lower()) else msg.from_user
    u = get_u(db, target.id, target.first_name)
    
    all_u = sorted(db["users"].items(), key=lambda x: x[1].get("messages", 0), reverse=True)
    pos = next((i for i, (uid, _) in enumerate(all_u, 1) if int(uid) == target.id), "?")

    text = (f"👤 <b>{u['nick']}</b>\n"
            f"⭐ Ранг: {u['stars']} ({RANK_NAMES.get(u['stars'])})\n"
            f"🏆 Место в топе: {pos}\n"
            f"💬 Сообщений за всё время: {u['messages']}\n"
            f"📝 Описание: {u.get('desc', 'Отсутствует')}")
    await msg.reply(text)

@profile_router.message(F.text.lower().in_(["мои варны", "твои варны"]))
async def show_warns(msg: types.Message):
    db = load_db()
    target = msg.reply_to_message.from_user if (msg.reply_to_message and "твои" in msg.text.lower()) else msg.from_user
    u = get_u(db, target.id)
    
    if not u["warns"]:
        await msg.reply(f"🛡 Викинг {u['nick']} добросовестный гражданин!")
    else:
        res = f"Варны {u['nick']} ({len(u['warns'])}/5):\n"
        for i, w in enumerate(u["warns"], 1):
            res += f"{i}. {w['reason']} (от {w['admin']})\n"
        await msg.reply(res)
        
