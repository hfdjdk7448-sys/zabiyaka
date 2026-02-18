import asyncio
import logging
import time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, ChatPermissions

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8463010853:AAE7piw8PFlxNCzKw9vIrmdJmTYAm1rBnuI"
GIF_PUNISH = "https://media1.tenor.com/m/2DfpWS8cP48AAAAd/tuffnut-ruffnut.gif"
GIF_WELCOME = "https://media1.tenor.com/m/TphIrQuFImkAAAAC/drake-how-to-train-your-dragon.gif"

# Ранги
RANKS = {
    5: "Вожак стаи 👑",
    4: "Старший всадник 🐉",
    3: "Главный драконовед 📜",
    2: "Главный наездник 🐎",
    1: "Простой житель 🛖",
    0: "Участник 🥚"
}

# Временная база данных (в продакшене лучше использовать БД)
db = {
    "users": {}, # {user_id: {"rank": 0, "warns": [], "nick": None, "bio": None, "msgs": 0}}
    "settings": {"warn_limit": 5, "cmd_access": {"бан": 2, "мут": 1}}
}

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_user_data(user_id):
    if user_id not in db["users"]:
        db["users"][user_id] = {"rank": 0, "warns": [], "nick": None, "bio": None, "msgs": 0}
    return db["users"][user_id]

async def check_access(message: Message, required_rank: int):
    user = get_user_data(message.from_user.id)
    if user["rank"] < required_rank:
        await message.reply("Задирака: Эй! У тебя кость не доросла командовать!\nЗабияка: Ага, брысь отсюда, мелюзга!")
        return False
    return True

# --- КОМАНДЫ МОДЕРАЦИИ ---

@dp.message(Command("кто_админ", "админы", ignore_case=True))
async def list_admins(message: Message):
    text = "📜 **Иерархия Драконьего Края:**\n"
    sorted_users = sorted(db["users"].items(), key=lambda x: x[1]['rank'], reverse=True)
    found = False
    for uid, data in sorted_users:
        if data['rank'] > 0:
            text += f"{data['rank']}- {RANKS[data['rank']]} | [Укротитель](tg://user?id={uid})\n"
            found = True
    if not found: text += "Пока только драконы... Админов нет."
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text.lower().startswith(("повысить", "понизить")))
async def change_rank(message: Message):
    if not await check_access(message, 4): return
    
    parts = message.text.split()
    target_id = message.reply_to_message.from_user.id if message.reply_to_message else None
    
    # Логика парсинга числа и юзера тут (упрощенно)
    diff = 1
    if len(parts) > 1 and parts[1].isdigit(): diff = int(parts[1])
    
    if not target_id: return await message.reply("Забияка: В кого тыкать-то? Ответь на сообщение!")
    
    user = get_user_data(target_id)
    if "повысить" in parts[0].lower():
        user["rank"] = min(5, user["rank"] + diff)
        await message.reply(f"Задирака: Опа! Теперь ты {RANKS[user['rank']]}! Не зазнайся.")
    else:
        user["rank"] = max(0, user["rank"] - diff)
        await message.reply(f"Забияка: Ха! Опустили тебя до {RANKS[user['rank']]}. Иди чисти стойла!")

# --- БАНЫ / МУТЫ / ВАРНЫ ---

@dp.message(Command("warn", "варн", "пред", ignore_case=True))
async def warn_user(message: Message):
    if not await check_access(message, 2): return
    target = message.reply_to_message
    if not target: return
    
    u_data = get_user_data(target.from_user.id)
    u_data["warns"].append(datetime.now() + timedelta(days=1))
    
    count = len(u_data["warns"])
    await message.answer_animation(
        animation=GIF_PUNISH,
        caption=f"🔥 **ВАРН!**\nАдмин: {message.from_user.first_name}\nНарушитель: {target.from_user.first_name}\nПредупреждений: {count}/{db['settings']['warn_limit']}\n\nЗадирака: Получи по башке! Еще чуть-чуть, и вылетишь из Края!"
    )
    
    if count >= db["settings"]["warn_limit"]:
        await message.chat.ban(target.from_user.id)
        await message.answer("Забияка: Всё, терпение лопнуло! В бездну его!")

# --- ПРИВЕТСТВИЕ ---

@dp.message(F.new_chat_members)
async def welcome(message: Message):
    for member in message.new_chat_members:
        await message.answer_animation(
            animation=GIF_WELCOME,
            caption=f"Привет! {member.first_name}\nДобро пожаловать в Драконий край 🐲\n\nРады видеть тебя в нашем чате..."
        )

# --- АНТИСПАМ ---
user_spam_check = {} # {user_id: [timestamp1, timestamp2...]}

@dp.message(F.sticker | F.animation)
async def anti_spam(message: Message):
    uid = message.from_user.id
    now = time.time()
    user_spam_check.setdefault(uid, [])
    user_spam_check[uid] = [t for t in user_spam_check[uid] if now - t < 10]
    user_spam_check[uid].append(now)
    
    if len(user_spam_check[uid]) >= 5:
        await message.chat.restrict(uid, permissions=ChatPermissions(can_send_messages=False), until_date=timedelta(hours=1))
        await warn_user(message) # Автоварн
        await message.answer("Задирака: ХВАТИТ КАРТИНКАМИ КИДАТЬСЯ! У меня глаза болят! Мут на час!")

# --- СТАТИСТИКА ---

@dp.message(F.text)
async def track_stats(message: Message):
    # Учет сообщений
    u_data = get_user_data(message.from_user.id)
    u_data["msgs"] += 1
    
    # Команда ТОП
    if message.text.lower() in ["топ акт", "стата топ"]:
        top = sorted(db["users"].items(), key=lambda x: x[1]['msgs'], reverse=True)[:30]
        res = "🏆 **Топ всадников Края:**\n"
        for i, (uid, data) in enumerate(top, 1):
            name = data['nick'] or f"Викинг_{uid}"
            res += f"{i}. [{name}](tg://user?id={uid}) — {data['msgs']} соо\n"
        await message.answer(res, parse_mode="Markdown")

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
    
