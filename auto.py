from aiogram import Router, F, types
from datetime import datetime, timedelta
from database import load_db, save_db, get_u

auto_router = Router()

# Временное хранилище для антиспама (счетчик подряд)
spam_tracker = {}

@auto_router.chat_member()
async def welcome(event: types.ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        text = (
            "Привет!\nДобро пожаловать в Драконий край 🐲\n\n"
            "Рады видеть тебя в нашем чате. Здесь собираются люди, которым близка вселенная «Как приручить дракона»: "
            "обсуждения, теории, размышления и живое общение — без лишнего шума и конфликтов\n\n"
            "Чувствуй себя комфортно, знакомься, участвуй в разговорах — будем рады твоему присутствию 😀\n"
            "Если возникнут вопросы или понадобится помощь, смело обращайся к администрации\n\n"
            "Приятного общения и хорошего дня 🐉✨"
        )
        await event.bot.send_animation(
            chat_id=event.chat.id,
            animation="https://media1.tenor.com/m/cHFxDQOITxwAAAAd/ruffnut-and-tuffnut-happiness-dragons-riders-of-berk.gif",
            caption=text
        )

@auto_router.message(F.content_type.in_({'sticker', 'animation'}) | F.text.regexp(r'[\U00010000-\U0010ffff]'))
async def anti_spam(msg: types.Message):
    user_id = msg.from_user.id
    now = datetime.now()
    
    if user_id not in spam_tracker:
        spam_tracker[user_id] = {'count': 1, 'last_time': now}
    else:
        # Если интервал между сообщениями меньше 10 секунд, считаем "подряд"
        if now - spam_tracker[user_id]['last_time'] < timedelta(seconds=10):
            spam_tracker[user_id]['count'] += 1
        else:
            spam_tracker[user_id]['count'] = 1
        spam_tracker[user_id]['last_time'] = now

    if spam_tracker[user_id]['count'] >= 5:
        db = load_db()
        u = get_u(db, user_id)
        # Наказание
        u["warns"].append({"reason": "Спам", "admin": "Автобот", "date": now.strftime("%d.%m")})
        save_db(db)
        
        await msg.delete()
        await msg.chat.restrict(user_id, permissions=types.ChatPermissions(can_send_messages=False), until_date=now + timedelta(hours=1))
        await msg.answer(f"🚫 {msg.from_user.first_name} замучен на 1 час и получил варн. Причина: Спам")
        spam_tracker[user_id]['count'] = 0

        # Проверка на 5 варнов
        if len(u["warns"]) >= 5:
            await msg.chat.ban(user_id)
            await msg.answer(f"💀 {u['nick']} забанен. Причина: максимальное количество варнов")
          
