
from aiogram import Bot, Dispatcher, executor, types
import json
import os
from config import API_TOKEN

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

tasks_file = "tasks.json"

def load_tasks():
    if os.path.exists(tasks_file):
        with open(tasks_file, "r") as f:
            return json.load(f)
    return {}

def save_tasks(data):
    with open(tasks_file, "w") as f:
        json.dump(data, f, indent=2)

# Классический способ через /task
@dp.message_handler(commands=["task"])
async def assign_task(message: types.Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[1].startswith("@"):
        await message.reply("Формат: /task @username Текст задачи")
        return

    username = parts[1][1:]
    task_text = parts[2]
    await process_task(message, username, task_text)

# Новый способ — без команды, просто "@username задача"
@dp.message_handler(lambda message: message.text and message.text.startswith("@"))
async def assign_task_freeform(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return

    username = parts[0][1:]
    task_text = parts[1]
    await process_task(message, username, task_text)

# Универсальная функция назначения задач
async def process_task(message, username, task_text):
    tasks = load_tasks()
    tasks.setdefault(username, []).append({
        "from": message.from_user.username,
        "text": task_text,
        "status": "assigned"
    })
    save_tasks(tasks)

    try:
        await bot.send_message(
            f"@{username}",
            f"Вам назначена задача от @{message.from_user.username}:

{task_text}",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("✅ Выполнено", callback_data=f"done|{username}|{task_text}"),
                types.InlineKeyboardButton("❌ Отказаться", callback_data=f"decline|{username}|{task_text}")
            )
        )
        await message.reply("Задача отправлена сотруднику.")
    except:
        await message.reply("Не удалось отправить задачу. Убедитесь, что сотрудник начал чат с ботом.")

@dp.callback_query_handler(lambda c: c.data.startswith(('done', 'decline')))
async def handle_response(callback_query: types.CallbackQuery):
    action, username, task_text = callback_query.data.split("|")
    tasks = load_tasks()

    if username in tasks:
        for t in tasks[username]:
            if t["text"] == task_text:
                t["status"] = "done" if action == "done" else "declined"
                save_tasks(tasks)
                await bot.send_message(
                    f"@{t['from']}",
                    f"@{username} {'выполнил' if action == 'done' else 'отклонил'} задачу:
"{task_text}""
                )
                await callback_query.answer("Ответ зарегистрирован.")
                return
    await callback_query.answer("Ошибка задачи.")

@dp.message_handler(commands=["mytasks"])
async def show_tasks(message: types.Message):
    username = message.from_user.username
    tasks = load_tasks().get(username, [])
    if not tasks:
        await message.reply("У вас нет задач.")
        return
    text = "\n\n".join([f"• {t['text']} (статус: {t['status']})" for t in tasks])
    await message.reply(f"Ваши задачи:\n\n{text}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
