from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from database import *


def generate_main_menu():
    button1 = KeyboardButton(text='💖 New Kindness')
    button2 = KeyboardButton(text='📊 My Stats')
    button3 = KeyboardButton(text='✍️ Add own kindness')
    # button4 = KeyboardButton(text='📅 My Streak')
    button5 = KeyboardButton(text='🔄 Manage my act')
    button6 = KeyboardButton(text='❓ Help & Info')
    # button7 = KeyboardButton(text='⚙️ Settings')

    main_menu = ReplyKeyboardMarkup(
        keyboard=[
            [button1, button2],
            [button5, button3],
            [button6],
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return main_menu

def user_choice_for_randomizer(kindness_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍 Continue", callback_data=f"{kindness_id}_continue_kindness")],
        [InlineKeyboardButton(text="🔄 Another one", callback_data=f"{kindness_id}another_kindness")]
    ])
    return keyboard


def my_stats_buttons(user_id):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📈 See Progress Graph', callback_data=f'{user_id}_see_progress'),
         InlineKeyboardButton(text='📝 View Completed Acts', callback_data=f'{user_id}_view_completed_acts')],
        [InlineKeyboardButton(text='🔄 Reset Stats', callback_data=f'{user_id}_reset_stats'),
         InlineKeyboardButton(text="📜 View My Acts", callback_data=f"{user_id}_view_goals")]
    ])
    return markup




def get_kindness_list(user_id):
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    uncompleted_kindnesses = select_uncompleted_kindnesses(user_id)
    row = []
    for idx, kindness in enumerate(uncompleted_kindnesses):
        kindness_id = kindness[2]
        kindness_text = fetch_kindness_text_by_id(kindness_id)
        button = InlineKeyboardButton(text=f"{kindness_text}",
                                      callback_data=f"start_kindness_{kindness_id}_{user_id}")
        row.append(button)

        if len(row) == 2:
            markup.inline_keyboard.append(row)
            row = []
    if row:
        markup.inline_keyboard.append(row)

    return markup


def generate_kindness_settings(kindness_id, user_id):
    markup = InlineKeyboardMarkup(inline_keyboard=[])

    button_complete = InlineKeyboardButton(text="✅ Mark as Completed",
                                           callback_data=f'complete_kindness_{kindness_id}_{user_id}')
    button_delete = InlineKeyboardButton(text="❌ Delete",
                                         callback_data=f'delete_kindness_{kindness_id}_{user_id}')
    button_go_back = InlineKeyboardButton(text="↩️ Go Back",
                                          callback_data=f'go_back_{user_id}')

    markup.inline_keyboard.append([button_complete, button_delete])
    markup.inline_keyboard.append([button_go_back])

    return markup


def show_user_acts_buttons(user_id):
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    uncompleted_kindnesses = select_user_kindness(user_id)
    row = []

    for kindness_id, kindness_text in uncompleted_kindnesses:
        button = InlineKeyboardButton(
            text=f"{kindness_text}",
            callback_data=f"deleting_kindness_{kindness_id}_{user_id}"
        )
        row.append(button)

        if len(row) == 2:
            markup.inline_keyboard.append(row)
            row = []

    if row:
        markup.inline_keyboard.append(row)


    return markup
