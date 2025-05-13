from aiogram import Bot, Dispatcher, executor, types
import json
import os
from config import API_TOKEN

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

tasks_file = "tasks.json"
user_map_file = "user_map.json"

# ===== UTILS =====

def load_tasks():
    if os.path.exists(tasks_file):
        with open(tasks_file, "r") as f:
            return json.load(f)
    return {}

def save_tasks(data):
    with open(tasks_file, "w") as f:
        json.dump(data, f, indent=2)

def load_user_map():
    if os.path.exists(user_map_file):
        with open(user_map_file, "r") as f:
            return json.load(f)
    return {}

def save_user_map(data):
    with open(user_map_file, "w") as f:
        json.dump(data, f, indent=2)

# ===== START (регистрация) =====

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_map = load_user_map()
    username = message.from_user.username
    if username:
        user_map[username] = message.from_user.id
        save_user_map(user_map)
        await message.reply("✅ Ты зарегистрирован, теперь можешь получать задачи.")
    else:
        await message.reply("⚠️ У тебя не установлен username. Установи его в Telegram настройках.")

# ===== POST TASK (/task @username текст) =====

@dp.message_handler(commands=["task"])
async def assign_task(message: types.Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[1].startswith("@"):
        await message.reply("Формат: /task @username Текст задачи")
        return

    username = parts[1][1:]
    task_text = parts[2]
    await process_task(message, username, task_text)

# ===== POST TASK (@username текст) =====

@dp.message_handler(lambda message: message.text and message.text.startswith("@"))
async def assign_task_freeform(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return

    username = parts[0][1:]
    task_text = parts[1]
    await process_task(message, username, task_text)

# ===== PROCESS TASK =====

async def process_task(message, username, task_text):
    tasks = load_tasks()
    tasks.setdefault(username, []).append({
        "from": message.from_user.username,
        "text": task_text,
        "status": "assigned"
    })
    save_tasks(tasks)

    user_map = load_user_map()
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
        await message.reply("Не удалось отправить задачу. Убедитесь, что сотрудник написал /start.")

# ===== HANDLE BUTTONS =====

@dp.callback_query_handler(lambda c: c.data.startswith(('done', 'decline')))
async def handle_response(callback_query: types.CallbackQuery):
    action, username, task_text = callback_query.data.split("|")
    tasks = load_tasks()

    if username in tasks:
        for t in tasks[username]:
            if t["text"] == task_text:
                t["status"] = "done" if action == "done" else "declined"
                save_tasks(tasks)

                user_map = load_user_map()
                from_username = t["from"]
                from_chat_id = user_map.get(from_username)

                if from_chat_id:
                    await bot.send_message(
                        from_chat_id,
                        f"@{username} {'выполнил' if action == 'done' else 'отклонил'} задачу:\n\"{task_text}\""
                    )

                await callback_query.answer("Ответ зарегистрирован.")
                return
    await callback_query.answer("Ошибка задачи.")

# ===== /mytasks =====

@dp.message_handler(commands=["mytasks"])
async def show_tasks(message: types.Message):
    username = message.from_user.username
    tasks = load_tasks().get(username, [])
    if not tasks:
        await message.reply("У вас нет задач.")
        return
    text = "\n\n".join([f"• {t['text']} (статус: {t['status']})" for t in tasks])
    await message.reply(f"Ваши задачи:\n\n{text}")

# ===== MAIN =====

if __name__ == '__main__':
    print("✅ Бот запущен")
    executor.start_polling(dp, skip_updates=True)
