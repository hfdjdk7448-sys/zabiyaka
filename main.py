import asyncio
import logging
import time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, ChatPermissions

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8463010853:AAE7piw8PFlxNCzKw9vIrmdJmTYAm1rBnuI"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Иерархия (в реальности лучше использовать БД, здесь — словарь для работы в ОЗУ)
# {user_id: rank_level}
user_ranks = {} 
# {chat_id: {user_id: [warn_timestamps]}}
warns = {}
# Настройки команд (команда: минимальный_ранг)
command_access = {
    "бан": 3, "мут": 2, "варн": 2, "кик": 2, "дк": 4, "смс": 1
}

RANKS = {
    5: "Вожак стаи 👑",
    4: "Старший всадник 🐉",
    3: "Главный драконовед 📚",
    2: "Главный наездник ⚔️",
    1: "Простой житель 🪵",
    0: "Обычный участник"
}

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_rank(user_id):
    return user_ranks.get(user_id, 0)

def parse_time(time_str: str):
    if not time_str: return 3600 # 1 час по умолчанию
    units = {'м': 60, 'ч': 3600, 'д': 86400}
    try:
        val = int(time_str[:-1])
        unit = time_str[-1].lower()
        return val * units.get(unit, 3600)
    except: return 3600

# --- КОМАНДЫ МОДЕРАЦИИ ---

@dp.message(Command("кто_админ", "админы", ignore_case=True))
async def list_admins(message: Message):
    text = "📜 **Совет Драконьего Края:**\n\n"
    sorted_ranks = sorted(user_ranks.items(), key=lambda x: x[1], reverse=True)
    for uid, rank in sorted_ranks:
        if rank > 0:
            text += f"{RANKS[rank]} — [ID: {uid}]\n"
    await message.answer(text or "Пока только драконы... Админов не густо.")

@dp.message(F.text.lower().startswith(("повысить", "понизить")))
async def change_rank(message: Message):
    if get_rank(message.from_user.id) < 4: return
    
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target: return
    
    parts = message.text.split()
    delta = 1
    if len(parts) > 1 and parts[1].isdigit(): delta = int(parts[1])
    
    current = get_rank(target.id)
    if "повысить" in message.text.lower():
        new_rank = min(current + delta, 5)
    else:
        new_rank = max(current - delta, 0)
        
    user_ranks[target.id] = new_rank
    await message.answer(f"💥 **Задирака:** Смотри, Забияка, у нас пополнение!\n**Забияка:** Теперь {target.first_name} официально **{RANKS[new_rank]}**!")

@dp.message(F.text.lower().startswith(("варн", "пред", "!warn")))
async def set_warn(message: Message):
    if get_rank(message.from_user.id) < command_access["варн"]: return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target: return

    user_warns = warns.get(target.id, [])
    user_warns.append(time.time() + 86400) # По умолчанию на сутки
    warns[target.id] = user_warns
    
    await message.answer_animation(
        animation="https://media1.tenor.com/m/2DfpWS8cP48AAAAd/tuffnut-ruffnut.gif",
        caption=f"🧨 **БАБАХ!**\n{target.first_name}, ты получил ВАРН от {message.from_user.first_name}!\nПредупреждений: {len(user_warns)}/5"
    )
    if len(user_warns) >= 5:
        await message.chat.ban(user_id=target.id)
        await message.answer("💀 Всё, лимит исчерпан. Близнецы в восторге, а ты летишь из чата!")

@dp.message(F.text.lower().startswith(("мут", "mute", "заткнуть")))
async def mute_user(message: Message):
    if get_rank(message.from_user.id) < command_access["мут"]: return
    if not message.reply_to_message: return
    
    args = message.text.split()
    duration = parse_time(args[1]) if len(args) > 1 else 3600
    
    until = datetime.now() + timedelta(seconds=duration)
    await message.chat.restrict(user_id=message.reply_to_message.from_user.id, permissions=ChatPermissions(can_send_messages=False), until_date=until)
    
    await message.answer_animation(
        animation="https://media1.tenor.com/m/2DfpWS8cP48AAAAd/tuffnut-ruffnut.gif",
        caption=f"🤐 **Забияка:** Тсс! {message.reply_to_message.from_user.first_name} теперь молчит.\n**Задирака:** Обожаю тишину перед взрывом!"
    )

# --- ПРИВЕТСТВИЕ ---
@dp.chat_member()
async def welcome(event: types.ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        await bot.send_video(
            chat_id=event.chat.id,
            video="https://media.tenor.com/TphIrQuFImkAAAA1/drake-how-to-train-your-dragon.webp",
            caption=(
                "Привет!\nДобро пожаловать в **Драконий край** 🐲\n\n"
                "Рады видеть тебя в нашем чате. Здесь собираются люди, которым близка вселенная «Как приручить дракона».\n\n"
                "Чувствуй себя комфортно, будем рады твоему присутствию 😀"
            )
        )

# --- АНТИСПАМ (Пример упрощенный) ---
user_messages = {}

@dp.message(F.content_type.in_({'sticker', 'animation'}))
async def antispam_handler(message: Message):
    uid = message.from_user.id
    now = time.time()
    user_data = user_messages.get(uid, [])
    user_data = [t for t in user_data if now - t < 10] # окно 10 сек
    user_data.append(now)
    user_messages[uid] = user_data
    
    if len(user_data) >= 5:
        await message.chat.restrict(user_id=uid, permissions=ChatPermissions(can_send_messages=False), until_date=datetime.now() + timedelta(hours=1))
        await message.answer("🔥 **АНТИСПАМ:** Близнецы не любят, когда мельтешат! Мут на час за спам стикерами.")

# --- ПРОФИЛЬ ---
@dp.message(Command("кто_я", "профиль", ignore_case=True))
async def my_profile(message: Message):
    rank = get_rank(message.from_user.id)
    await message.answer(f"👤 **Твоя карточка:**\nИмя: {message.from_user.full_name}\nРанг: {RANKS[rank]}\nСтатус: Наездник готов к бою!")

async def main():
    print("Бот Задирака и Забияка запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
