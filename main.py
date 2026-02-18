import asyncio, os, pytz
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

# Импортируем наши части
from admin import admin_router
from auto import auto_router
from profiles import profile_router
from database import load_db, save_db, get_u

TOKEN = "8463010853:AAE7piw8PFlxNCzKw9vIrmdJmTYAm1rBnuI"
CHAT_ID = -1002508735096 

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# ВАЖНО: Сначала подключаем специализированные роутеры
dp.include_router(admin_router)
dp.include_router(profile_router)
dp.include_router(auto_router)

# Обработчик сообщений для статистики (ДОЛЖЕН БЫТЬ ПОСЛЕДНИМ)
@dp.message()
async def statistics_handler(msg: types.Message):
    if not msg.from_user or msg.from_user.is_bot: return
    db = load_db()
    u = get_u(db, msg.from_user.id, msg.from_user.first_name)
    u["messages"] += 1
    if "stats" not in u: u["stats"] = {"day": 0}
    u["stats"]["day"] = u["stats"].get("day", 0) + 1
    save_db(db)

async def scheduler():
    tz = pytz.timezone('Europe/Moscow')
    while True:
        now = datetime.now(tz)
        if now.minute == 0:
            try:
                if now.hour == 8:
                    await bot.send_animation(CHAT_ID, "https://media1.tenor.com/m/-5D-bYxCvFAAAAAd/httyd-yeah.gif", caption="Доброе утро,Стая!🌞✨")
                elif now.hour == 21:
                    await bot.send_animation(CHAT_ID, "https://media1.tenor.com/m/C3P-yay4lF8AAAAC/httyd-ruffnut.gif", caption="Спокойной ночи,Стая!🌙🌥")
            except Exception as e:
                print(f"Ошибка рассылки: {e}")
            await asyncio.sleep(61)
        await asyncio.sleep(30)

async def handle(request): return web.Response(text="Dragon Bot Active")

async def main():
    asyncio.create_task(scheduler())
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Указываем порт из переменной окружения Render
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, "0.0.0.0", port).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
