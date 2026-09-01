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
from aiogram.utils.formatting import Bold, Link, as_list

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
  raise ValueError("Помилка: Не знайдено змінну середовища BOT_TOKEN!")

conn = sqlite3.connect("users_cities.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
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

ALIASES = {
    "kryvyirih": "kryvyi_rih",
    "кривийріг": "kryvyi_rih",
    "кривий_ріг": "kryvyi_rih",
    "kyiv": "kyiv",
    "київ": "kyiv",
    "киив": "kyiv",
    "kaniv": "kaniv",
    "канів": "kaniv",
    "pavlohrad": "pavlohrad",
    "павлоград": "павлоград",
}


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

    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user.id,))
    row = cursor.fetchone()

    if row:
      cursor.execute(
          "UPDATE users SET city = ?, full_name = ? WHERE user_id = ?",
          (city_code, user.full_name, user.id),
      )
    else:
      cursor.execute(
          "INSERT INTO users (user_id, full_name, city) VALUES (?, ?, ?)",
          (user.id, user.full_name, city_code),
      )
    conn.commit()

    await callback.message.edit_text(
        f"✅ Твоє місто успішно збережено: <b>{city_name}</b>.\nЯкщо захочеш"
        " змінити — просто напиши /start боту знову.",
        parse_mode="HTML",
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
        "SELECT user_id, full_name FROM users WHERE city = ?", (city_code,)
    )
    rows = cursor.fetchall()

    if not rows:
      await message.reply(
          f"У місті {city_name} поки немає зареєстрованих учасників."
      )
      return

    content = []
    for user_id, full_name in rows:
      name = full_name or "Користувач"
      content.append(Link(name, url=f"tg://user?id={user_id}"))

    chunk_size = 10
    for i in range(0, len(content), chunk_size):
      chunk_items = content[i : i + chunk_size]
      text_obj = as_list(
          Bold(f"📢 Збір для мешканців {city_name}:"),
          as_list(*chunk_items, sep=" "),
      )
      await message.answer(**text_obj.as_kwargs())

  print("Бот запущено на сервері!")
  await bot.delete_webhook(drop_pending_updates=True)
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
