from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import dotenv_values

from utils.db import DatabaseManager
from handlers import (menu_router,
                      add_router,
                      catalog_router,
                      basket_router,
                      delivery_router,
                      orders_router,
                      sos_router,
                      questions_router)


db = DatabaseManager('database.db')
bot = Bot(token=dotenv_values(".env").get('TOKEN'),
          parse_mode=ParseMode.HTML)
dp = Dispatcher(bot=bot, storage=MemoryStorage())
dp.include_routers(menu_router, catalog_router, add_router, basket_router,
                   delivery_router, orders_router, sos_router,
                   questions_router)
