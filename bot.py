from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import json
import os
from config import API_TOKEN

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

tasks_file = "/data/tasks.json"
user_map_file = "/data/user_map.json"


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


async def set_commands(bot: Bot):
    commands = [
        types.BotCommand(command="/start", description="Зарегистрироваться"),
        types.BotCommand(command="/task", description="Поставить задачу"),
        types.BotCommand(command="/mytasks", description="Показать мои задачи"),
        types.BotCommand(command="/help", description="Помощь по командам"),
        types.BotCommand(command="/info", description="О боте"),
    ]
    await bot.set_my_commands(commands)


@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    user_map = load_user_map()
    user_map[message.from_user.username] = message.from_user.id
    save_user_map(user_map)
    await message.reply("Вы зарегистрированы и готовы получать задачи.")


@dp.message_handler(commands=["help"])
async def cmd_help(message: types.Message):
    await message.reply("Список команд:\n"
                        "/start — зарегистрироваться\n"
                        "/task @username задача — поставить задачу\n"
                        "/mytasks — показать мои задачи\n"
                        "/info — информация о боте")


@dp.message_handler(commands=["info"])
async def cmd_info(message: types.Message):
    await message.reply("Этот бот помогает ставить и отслеживать задачи внутри команды.")


@dp.message_handler(commands=["task"])
async def assign_task(message: types.Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[1].startswith("@"):
        await message.reply("Формат: /task @username Текст задачи")
        return

    username = parts[1][1:]
    task_text = parts[2]
    await process_task(message, username, task_text)


@dp.message_handler(lambda message: message.text and message.text.startswith("@"))
async def assign_task_freeform(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return

    username = parts[0][1:]
    task_text = parts[1]
    await process_task(message, username, task_text)


async def process_task(message, username, task_text):
    tasks = load_tasks()
    user_map = load_user_map()

    tasks.setdefault(username, []).append({
        "from": message.from_user.username,
        "text": task_text,
        "status": "assigned"
    })
    save_tasks(tasks)

    chat_id = user_map.get(username)
    if not chat_id:
        await message.reply("Не удалось отправить задачу. Сотрудник не зарегистрирован командой /start.")
        return

    try:
        await bot.send_message(
            chat_id,
            f"Вам назначена задача от @{message.from_user.username}:\n\n{task_text}",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("✅ Выполнено", callback_data=f"done|{username}|{task_text}"),
                types.InlineKeyboardButton("❌ Отказаться", callback_data=f"decline|{username}|{task_text}")
            )
        )
        await message.reply("Задача отправлена сотруднику.")
    except Exception as e:
        await message.reply(f"Ошибка при отправке задачи: {e}")


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
                    f"@{username} {'выполнил' if action == 'done' else 'отклонил'} задачу:\n\"{task_text}\""
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


async def on_startup(dp):
    await set_commands(bot)
    print("✅ Бот успешно запущен и команды зарегистрированы")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
