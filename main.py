import asyncio
import os
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
  raise ValueError("Помилка: Не знайдено змінну середовища BOT_TOKEN!")

conn = sqlite3.connect("users_cities.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        city TEXT
    )
"""
)
conn.commit()

CITIES = {
    "kyiv": "Київ",
    "kaniv": "Канів",
    "pavlohrad": "Павлоград",
    "kryvyi_rih": "Кривий Ріг",
}

ALIASES = {"kryvyirih": "kryvyi_rih"}


def get_cities_keyboard():
  builder = []
  for code, name in CITIES.items():
    builder.append(
        [InlineKeyboardButton(text=name, callback_data=f"city_{code}")]
    )
  return InlineKeyboardMarkup(inline_keyboard=builder)


async def main():
  bot = Bot(token=TOKEN)
  dp = Dispatcher()

  @dp.message(CommandStart(), F.chat.type == "private")
  async def cmd_start(message: Message):
    keyboard = get_cities_keyboard()
    await message.answer(
        "Привіт! Обери своє місто зі списку нижче:", reply_markup=keyboard
    )

  @dp.callback_query(F.data.startswith("city_"))
  async def process_city_selection(callback: CallbackQuery):
    city_code = callback.data.split("_", 1)[1]
    city_name = CITIES.get(city_code, "Невідомо")
    user = callback.from_user

    cursor.execute(
        """
            INSERT INTO users (user_id, username, full_name, city) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET city=?, username=?, full_name=?
        """,
        (
            user.id,
            user.username,
            user.full_name,
            city_code,
            user.username,
            user.full_name,
        ),
    )
    conn.commit()

    await callback.message.edit_text(
        f"✅ Твоє місто успішно збережено: **{city_name}**.\nЯкщо захочеш"
        " змінити — просто напиши /start боту знову.",
        parse_mode="Markdown",
    )
    await callback.answer()

  @dp.message(F.chat.type.in_(["group", "supergroup"]))
  async def handle_city_command(message: Message):
    if not message.text or not message.text.startswith("/"):
      return

    command = message.text.split()[0].lstrip("/").lower()
    if "@" in command:
      command = command.split("@")[0]

    if command in ALIASES:
      command = ALIASES[command]

    if command not in CITIES:
      return

    city_code = command
    city_name = CITIES[city_code]

    cursor.execute(
        "SELECT user_id, username, full_name FROM users WHERE city = ?",
        (city_code,),
    )
    rows = cursor.fetchall()

    if not rows:
      await message.reply(
          f"У місті {city_name} поки немає зареєстрованих учасників."
      )
      return

    mentions = []
    for user_id, username, full_name in rows:
      if username:
        mentions.append(f"@{username}")
      else:
        safe_name = full_name.replace("[", "").replace("]", "")
        mentions.append(f"[{safe_name}](tg://user?id={user_id})")

    chunk_size = 10
    for i in range(0, len(mentions), chunk_size):
      chunk = " ".join(mentions[i : i + chunk_size])
      await message.answer(
          f"📢 Збір для мешканців **{city_name}**:\n{chunk}",
          parse_mode="Markdown",
      )

  print("Бот запущено на сервері!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
