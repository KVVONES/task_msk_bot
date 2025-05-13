from aiogram import Bot, Dispatcher, executor, types
import json
import os
from config import API_TOKEN

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Пути к файлам
BASE_DIR = "/tmp"
tasks_file = os.path.join(BASE_DIR, "tasks.json")
user_map_file = os.path.join(BASE_DIR, "user_map.json")

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_map = load_json(user_map_file)
    username = message.from_user.username
    if username:
        user_map[username] = message.from_user.id
        save_json(user_map_file, user_map)
        await message.reply("✅ Ты зарегистрирован и можешь получать задачи.")
    else:
        await message.reply("❗ У тебя не установлен username в Telegram.")

@dp.message_handler(commands=["task"])
async def assign_task(message: types.Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[1].startswith("@"):
        await message.reply("Формат: /task @username Текст задачи")
        return
    username = parts[1][1:]
    task_text = parts[2]
    await process_task(message, username, task_text)

@dp.message_handler(lambda m: m.text and m.text.startswith("@"))
async def assign_task_freeform(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return
    username = parts[0][1:]
    task_text = parts[1]
    await process_task(message, username, task_text)

async def process_task(message, username, task_text):
    tasks = load_json(tasks_file)
    tasks.setdefault(username, []).append({
        "from": message.from_user.username,
        "text": task_text,
        "status": "assigned"
    })
    save_json(tasks_file, tasks)

    user_map = load_json(user_map_file)
    chat_id = user_map.get(username)

    if chat_id:
        await bot.send_message(
            chat_id,
            f"Вам назначена задача от @{message.from_user.username}:\n\n{task_text}",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("✅ Выполнено", callback_data=f"done|{username}|{task_text}"),
                types.InlineKeyboardButton("❌ Отказаться", callback_data=f"decline|{username}|{task_text}")
            )
        )
        await message.reply("Задача отправлена сотруднику.")
    else:
        await message.reply("❌ Не удалось отправить задачу. Сотрудник не начал чат с ботом (/start).")

@dp.callback_query_handler(lambda c: c.data.startswith(('done', 'decline')))
async def handle_response(callback_query: types.CallbackQuery):
    action, username, task_text = callback_query.data.split("|")
    tasks = load_json(tasks_file)
    for t in tasks.get(username, []):
        if t["text"] == task_text:
            t["status"] = "done" if action == "done" else "declined"
            save_json(tasks_file, tasks)

            user_map = load_json(user_map_file)
            from_chat_id = user_map.get(t["from"])
            if from_chat_id:
                await bot.send_message(
                    from_chat_id,
                    f"@{username} {'выполнил' if action == 'done' else 'отклонил'} задачу:\n\"{task_text}\""
                )
            await callback_query.answer("Ответ зарегистрирован.")
            return
    await callback_query.answer("Ошибка задачи.")

@dp.message_handler(commands=["mytasks"])
async def show_tasks(message: types.Message):
    username = message.from_user.username
    tasks = load_json(tasks_file).get(username, [])
    if not tasks:
        await message.reply("У вас нет задач.")
        return
    text = "\n\n".join([f"• {t['text']} (статус: {t['status']})" for t in tasks])
    await message.reply(f"Ваши задачи:\n\n{text}")

if __name__ == '__main__':
    print("✅ Бот запущен")
    executor.start_polling(dp, skip_updates=True)
