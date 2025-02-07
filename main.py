from aiogram import Dispatcher, Bot
import asyncio
from aiogram.types import CallbackQuery, Message
from aiogram.filters import CommandStart
from keyboard import *
from database import *

TOKEN = ''


bot = Bot(TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_message(message: Message):
    await message.answer(f"Hey {message.from_user.full_name}! I'm KindSpark 🤖, here to spark kindness daily! \n\n"
                         f"Ready to make someone's day?\n"
                         f"Type /kindness to get started! ✨ or proceed to the menu")
    await register_user(message)

async def register_user(message: Message):
    chat_id = message.chat.id
    username = message.from_user.username
    user = select_user_from_db(chat_id)
    if user:
        await message.answer('Authentication is successful')
        await show_main_menu(message)
    else:
        full_name = message.from_user.full_name
        add_new_user(username=username, chat_id=chat_id, full_name=full_name)
        await message.answer('Registration is successful, you can continue')
        await show_main_menu(message)


async def show_main_menu(message: Message):
    await message.answer('Choose one of the options below to get started: ', reply_markup=generate_main_menu())


@dp.message(lambda message: '💖 New Kindness' in message.text or message.text == '/kindness')
async def return_kindness(message: Message):
    random_kindness = fetch_random_kindness()
    if random_kindness:
        await message.answer(
            f"Here's a random act of kindness for you:\n\n**  {random_kindness[1]}  **",
            reply_markup=user_choice_for_randomizer(random_kindness[0]) # inLine button
        )
    else:
        await message.answer("Sorry, no acts of kindness found. Please try again later.")


@dp.callback_query(lambda call: 'continue_kindness' in call.data)
async def save_user_kindness_choice(call: CallbackQuery):
    chat_id = call.message.chat.id
    kindness_id = call.data.split('_')[0]
    user = select_user_from_db(chat_id)

    if user:
        user_id = user[0]
        kindness_text = fetch_kindness_text_by_id(kindness_id)

        insert_into_user_kindness_table(user_id, kindness_id)

        await call.message.edit_text(
            f"Awesome, {call.from_user.first_name}! You've started the following kindness act:\n\n**  {kindness_text}  **\n\nKeep going and make someone's day brighter! 🌟")
    else:
        await call.message.answer("It seems you're not registered. Please start by typing /start.")


@dp.callback_query(lambda call: 'another_kindness' in call.data)
async def generate_new_kindness(call: CallbackQuery):
    random_kindness = fetch_random_kindness()
    current = call.data.split('_')[0]
    while random_kindness[0] == current:
        random_kindness = fetch_random_kindness()
    else:
        await call.message.answer(
            f"Here's another random act of kindness for you:\n\n**  {random_kindness[1]}  **",
            reply_markup=user_choice_for_randomizer(random_kindness[0])  # inLine button
        )


@dp.message(lambda message: '📊 My Stats' in message.text or message.text == 'my_stats')
async def my_stats_show_off(message: Message):
    chat_id = message.chat.id
    user = select_user_from_db(chat_id)
    if user is None:
        await message.answer("You are not registered yet. Please start by typing /start.")
        return

    user_id, _, full_name, username, kindness_count, _, highest_streak, joined_at = user

    response = (
        f"📊 *My Stats*\n\n"
        f"👤 *Name:* {full_name}\n"
        f"❤️ *Kindness Acts Completed:* {kindness_count}\n"
        f"📅 *Member Since:* {joined_at}\n\n"
        f"🔥 *Highest streak:* {highest_streak}\n\n"
        f"Keep spreading kindness! 😊"
    )

    await message.answer(response, parse_mode='Markdown', reply_markup=my_stats_buttons(user_id))


from datetime import datetime
import sqlite3
import io
import matplotlib.pyplot as plt
from aiogram.types import BufferedInputFile
from aiogram.types import Message


@dp.callback_query(lambda call: '_see_progress' in call.data)
async def get_progress_data(call: CallbackQuery):
    user_id = select_user_from_db(chat_id=call.message.chat.id)[0]
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()
    cursor.execute('''
        SELECT started_at, 
               COUNT(CASE WHEN completed = 0 THEN 1 END) AS started_count, 
               COUNT(CASE WHEN completed = 1 THEN 1 END) AS completed_count
        FROM user_kindness
        WHERE user_id = ?
        GROUP BY started_at
        ORDER BY started_at ASC
    ''', (user_id,))

    data = cursor.fetchall()
    database.close()

    if not data:
        await call.message.answer("No progress data available. Start tracking your kindnesses to see progress!")
        return
    timestamps = []
    completed_counts = []
    cumulative_completed_count = 0

    for started_at, started_count, completed_count in data:
        try:
            timestamp = datetime.strptime(started_at, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue

        # Update cumulative completed count
        cumulative_completed_count += completed_count
        timestamps.append(timestamp)
        completed_counts.append(cumulative_completed_count)
    if not timestamps:
        await call.message.answer("No valid progress data to display. Please check your tracking records!")
        return

    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, completed_counts, marker='x', label="Completed Kindnesses", color='green')
    plt.title("Kindness Progress Over Time (Completed Acts)")
    plt.xlabel("Time (When Acts Started)")
    plt.ylabel("Cumulative Completed Acts")
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True)
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    photo = BufferedInputFile(buffer.read(), filename="progress.png")
    await call.message.answer_photo(photo, caption="Here's your kindness progress over time 📊")

    await call.answer()


@dp.callback_query(lambda call: '_view_completed_acts' in call.data)
async def view_completed_acts(call: CallbackQuery):
    user_id = call.data.split('_')[0]
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()

    cursor.execute('''
        SELECT kindness_id, started_at
        FROM user_kindness
        WHERE user_id = ? AND completed = 1
        ORDER BY started_at DESC
    ''', (user_id,))

    completed_acts = cursor.fetchall()

    if not completed_acts:
        await call.message.edit_text("You have no completed acts yet.")
        return

    message = "Here are your completed acts within one day:\n"

    for kindness_id, started_at in completed_acts:
        cursor.execute('''
            SELECT kindness_text
            FROM kindnesses
            WHERE id = ?
        ''', (kindness_id,))
        act_name = cursor.fetchone()

        if act_name:
            act_name = act_name[0]
        else:
            act_name = "Unknown Act"

        timestamp = datetime.strptime(started_at, '%Y-%m-%d %H:%M:%S')
        message += f"- Act: {act_name}\n  Started at: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    await call.message.edit_text(message)
    await call.answer()


@dp.callback_query(lambda call: '_reset_stats' in call.data)
async def reset_stats(call: CallbackQuery):
    user_id = call.data.split('_')[0]
    database = sqlite3.connect('kindness_bot.db')
    cursor = database.cursor()

    cursor.execute('''
        UPDATE users
        SET kindness_count = 0,
            current_streak = 0,
            highest_streak = 0
        WHERE id = ?
    ''', (user_id,))

    # cursor.execute('''
    #     DELETE FROM user_kindness
    #     WHERE user_id = ? AND completed = 0
    # ''', (user_id,))

    database.commit()
    database.close()

    await call.message.answer("Your stats have been reset.")
    await call.answer()


@dp.message(lambda message: '🔄 Manage my act' in message.text or message.text == '🔄 Manage my act')
async def managing_current_kindness_act(message: Message):
    chat_id = message.chat.id
    user = select_user_from_db(chat_id)

    if user:
        user_id = user[0]
        database = sqlite3.connect('kindness_bot.db')
        cursor = database.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM user_kindness
            WHERE user_id = ? AND completed = 0
        ''', (user_id,))
        uncompleted_count = cursor.fetchone()[0]
        database.close()

        if uncompleted_count > 0:
            kindness_markup = get_kindness_list(user_id)
            if isinstance(kindness_markup, str):
                await message.answer(kindness_markup)
            else:
                await message.answer("You have uncompleted kindness acts. Click on them to modify:",
                                     reply_markup=kindness_markup)
        else:
            await message.answer("You have no uncompleted kindness acts. You can start a new one! Type /kindness")
    else:
        await message.answer("You are not registered yet. Please start by typing /start.")


@dp.callback_query(lambda call: 'start_kindness_' in call.data)
async def kindness_settings(call: CallbackQuery):
    _, _, kindness_id, user_id = call.data.split('_')

    kindness_text = fetch_kindness_text_by_id(kindness_id)
    await call.message.edit_text(
        f"Kindness Act:\n\n{kindness_text}\n\nWhat would you like to do?",
        reply_markup=generate_kindness_settings(kindness_id, user_id)
    )
    await call.answer()


@dp.callback_query(lambda call: 'go_back_' in call.data)
async def go_back(call: CallbackQuery):
    chat_id = call.message.chat.id
    user = select_user_from_db(chat_id)

    if user:
        user_id = user[0]
        kindness_markup = get_kindness_list(user_id)

        if isinstance(kindness_markup, str):
            await call.message.answer(kindness_markup)
        else:
            await call.message.edit_text(
                "You have uncompleted kindness acts. Click on them to modify:",
                reply_markup=kindness_markup
            )
    else:
        await call.message.answer("You are not registered yet. Please start by typing /start.")

@dp.callback_query(lambda call: 'complete_kindness' in call.data)
async def complete_kindness(call: CallbackQuery):
    chat_id = call.message.chat.id
    _, _, kindness_id, user_id = call.data.split('_')
    user = select_user_from_db(chat_id)

    if user:
        kindness_text = fetch_kindness_text_by_id(kindness_id)
        mark_kindness_as_complete(user_id, kindness_id)
        update_user_kindness_in_db(user_id)

        await call.message.edit_text(
            f"Awesome, {call.from_user.first_name}! You've completed the following kindness act:\n\n**  {kindness_text}  **\n\nGreat job! Keep spreading kindness! 🌟")
    else:
        await call.message.edit_text("It seems you're not registered. Please start by typing /start.")


@dp.callback_query(lambda call: 'delete_kindness' in call.data)
async def delete_kindness_action(call: CallbackQuery):
    _, _, kindness_id, user_id = call.data.split('_')
    delete_kindness(user_id, kindness_id)
    await call.message.edit_text(
        f"The kindness act has been deleted successfully.\n\nYour progress has been updated!",
        reply_markup=get_kindness_list(user_id)
    )
    await call.answer()

@dp.message(lambda message: '❓ Help & Info' in message.text or message.text == '/help')
async def help_info(message: Message):
    help_message = (
        "Welcome to Spark Kindness Bot! 🤖\n\n"
        "Here’s how you can use the bot:\n\n"
        "1. *Start* - Get started by typing /start.\n"
        "2. *Kindness* - Find a new act of kindness to do by typing /kindness.\n"
        "3. *My Stats* - Check your progress on kindness acts by typing /my_stats.\n\n"
        "If you need any further help or have questions, feel free to contact the bot owner @d_azamjonov."
    )
    await message.answer(help_message)


from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup

router = Router()

class KindnessState(StatesGroup):
    waiting_for_kindness_text = State()

@dp.message(lambda message: '✍️ Add own kindness' in message.text or message.text == '/add_kindness')
async def adding_own_kindness(message: types.Message, state: FSMContext):
    await state.set_state(KindnessState.waiting_for_kindness_text)
    await message.answer('Send the text explaining your kindness (Note it must not exceed 100 characters)')

@dp.message(StateFilter(KindnessState.waiting_for_kindness_text))
async def save_own_kindness(message: types.Message, state: FSMContext):
    kindness_text = message.text.strip()

    if len(kindness_text) > 100:
        await message.answer('Your text exceeds 100 characters. Please send a shorter message.')
        return
    try:
        user_id = select_user_from_db(message.chat.id)[0]
        print(user_id)
        save_user_kindness(user_id=user_id ,text=kindness_text)
    except:
        await message.answer('There was an error saving your kindness. Please try again later.')
        await state.clear()
        return

    await message.answer('Thank you for sharing your kindness!')
    await state.clear()

@dp.callback_query(lambda call: '_view_goals' in call.data)
async def show_user_acts(call: CallbackQuery):
    user_id = int(call.data.split('_')[0])
    await call.message.edit_text(
            "Here is the list of acts you added. Click on them to remove",
            reply_markup=show_user_acts_buttons(user_id)
        )

@dp.callback_query(lambda call: 'deleting_kindness_' in call.data)
async def deleting_user_kindness(call: CallbackQuery):
    _, _, kindness_id, user_id  = call.data.split('_')
    remove_user_kindness(user_id, kindness_id)
    await call.answer('Your kindness has been removed')
    await call.message.edit_text('Here is the list of acts you added. Click on them to remove',
                                 reply_markup=show_user_acts_buttons(user_id))





from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger


async def scheduled_task():
    update_user_streak_automatically()

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduled_task, IntervalTrigger(days=1, start_date='2025-02-01 00:00:00'))
    scheduler.start()

    # Start bot polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
asyncio.run(main())




