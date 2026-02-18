import asyncio, os, pytz
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

from admin import admin_router
from auto import auto_router
from profiles import profile_router
from database import load_db, save_db, get_u

TOKEN = "8463010853:AAE7piw8PFlxNCzKw9vIrmdJmTYAm1rBnuI"
CHAT_ID = -1002508735096 

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
dp.include_routers(admin_router, auto_router, profile_router)

@dp.message()
async def msg_handler(msg: types.Message):
    if not msg.from_user or msg.from_user.is_bot: return
    db = load_db()
    u = get_u(db, msg.from_user.id, msg.from_user.first_name)
    u["messages"] += 1
    u["stats"]["day"] = u["stats"].get("day", 0) + 1
    save_db(db)

async def scheduler():
    tz = pytz.timezone('Europe/Moscow')
    while True:
        now = datetime.now(tz)
        if now.minute == 0:
            if now.hour == 8:
                await bot.send_animation(CHAT_ID, "https://media1.tenor.com/-5D-bYxCvFAAAAAd/httyd-yeah.gif", caption="Доброе утро,Стая!🌞✨")
            elif now.hour == 21:
                await bot.send_animation(CHAT_ID, "https://media1.tenor.com/C3P-yay4lF8AAAAC/httyd-ruffnut.gif", caption="Спокойной ночи,Стая!🌙🌥")
            await asyncio.sleep(3600)
        await asyncio.sleep(30)

async def main():
    asyncio.create_task(scheduler())
    app = web.Application(); app.router.add_get("/", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
