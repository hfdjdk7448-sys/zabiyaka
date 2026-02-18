from aiogram import Router, F, types
from database import load_db, save_db, get_u, RANK_NAMES

profile_router = Router()

@profile_router.message(F.text.lower().startswith("+ник"))
async def set_nick(msg: types.Message):
    db = load_db()
    u = get_u(db, msg.from_user.id)
    new_nick = msg.text[5:].strip()
    if new_nick:
        u["nick"] = new_nick
        save_db(db)
        await msg.reply(f"✅ Теперь тебя зовут: {new_nick}")

@profile_router.message(F.text.lower().startswith("+описание"))
async def set_desc(msg: types.Message):
    db = load_db()
    u = get_u(db, msg.from_user.id)
    new_desc = msg.text[10:].strip()
    if new_desc:
        u["desc"] = new_desc
        save_db(db)
        await msg.reply("✅ Описание профиля обновлено!")

@profile_router.message(F.text.lower().in_(["кто я", "кто ты"]))
async def profile_card(msg: types.Message):
    db = load_db()
    # Если "кто ты" — берем юзера из реплая, если "кто я" — автора
    target = msg.reply_to_message.from_user if "ты" in msg.text.lower() and msg.reply_to_message else msg.from_user
    u = get_u(db, target.id, target.first_name)
    
    # Считаем место в топе
    all_users = sorted(db["users"].items(), key=lambda x: x[1].get("messages", 0), reverse=True)
    rank_pos = next((i for i, (uid, _) in enumerate(all_users, 1) if int(uid) == target.id), "?")

    text = (
        f"👤 <b>{u['nick']}</b>\n"
        f"🎖 Ранг: {RANK_NAMES.get(u['stars'], 'Житель')}\n"
        f"🏆 Место в топе: {rank_pos}\n"
        f"💬 Сообщений:\n"
        f"   За сегодня: {u['stats'].get('day', 0)}\n"
        f"   Всего: {u['messages']}\n"
        f"📝 Описание: {u.get('desc', 'Не заполнено')}"
    )
    await msg.reply(text)

@profile_router.message(F.text.lower().startswith("топ акт"))
async def show_top(msg: types.Message):
    db = load_db()
    is_all = "все" in msg.text.lower()
    
    # Сортировка (по 'messages' для "все" или по 'stats/day' для "сегодня")
    sort_key = (lambda x: x[1].get("messages", 0)) if is_all else (lambda x: x[1].get("stats", {}).get("day", 0))
    top_list = sorted(db["users"].items(), key=sort_key, reverse=True)[:30]
    
    res = f"<b>🏆 Топ активности ({'за всё время' if is_all else 'за сегодня'}):</b>\n\n"
    for i, (uid, d) in enumerate(top_list, 1):
        count = d['messages'] if is_all else d.get('stats', {}).get('day', 0)
        res += f"{i}. {d['nick']} - {count} сообщений\n"
    
    await msg.answer(res)
  
