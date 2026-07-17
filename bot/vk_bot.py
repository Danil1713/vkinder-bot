
import sys
import os

from data_base.db import Database

# Добавляем путь к корневой папке проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from random import randrange
from config import Config
from vk_api_client.vk_client import VK_client

vk_session = vk_api.VkApi(token=Config.group_token)
longpoll = VkLongPoll(vk_session)
vk = vk_session.get_api()

vk_client = VK_client()
user_states = {}
db = Database()


def write_msg(user_id, message, keyboard=None, attachment=None):

    params = {
        'user_id': user_id,
        'message': message,
        'random_id': randrange(10 ** 7)
    }

    if keyboard:
        params['keyboard'] = json.dumps(keyboard)
    if attachment:
        params['attachment'] = attachment

    vk.messages.send(**params)


def send_candidate(user_id, candidate, state):

    photos = vk_client.get_top_3_photos(candidate['id'])

    message = f"{candidate['first_name']} {candidate['last_name']}\n"
    message += f"https://vk.com/{candidate.get('domain', '')}\n"

    if candidate.get('age'):
        message += f"Возраст: {candidate['age']}\n"

    attachment = ','.join([p['attachment'] for p in photos]) if photos else ''

    keyboard = {
        "one_time": False,
        "buttons": [
            [
                {"action": {"type": "text", "label": "Дальше"}, "color": "primary"},
            ],
            [
                {"action": {"type": "text", "label": "В избранное"}, "color": "positive"},
                {"action": {"type": "text", "label": "В черный список"}, "color": "negative"}

            ],
            [
                {"action": {"type": "text", "label": "Показать избранное"}, "color": "secondary"},
                {"action": {"type": "text", "label": "Показать черный список"}, "color": "secondary"}
            ]
        ]
    }

    write_msg(user_id, message, keyboard=keyboard, attachment=attachment)
    db.add_viewed_user(user_id, candidate['id']) # Сразу добавили в просмотренные
    state['current_index'] += 1

def add_to_favorites(user_id, state):
    """Добавление в избранное"""
    current_index = state['current_index'] - 1

    if current_index < 0 or not state['candidates']:
        write_msg(user_id, "Нет текущего кандидата для добавления.")
        return

    candidate = state['candidates'][current_index]
    candidate_name = f"{candidate['first_name']} {candidate['last_name']}"
    # Проверка на нахождение в "Избранное"
    if db.is_favorite(user_id, candidate['id']):
        write_msg(user_id, f"{candidate_name} уже в избранном!")
        return

    # Получаем фото для сохранения
    photos = vk_client.get_top_3_photos(candidate['id'])
    photo_attachments = [p['attachment'] for p in photos] if photos else []

    if db.add_favorite(user_id, candidate, photo_attachments):
        write_msg(user_id, f"{candidate_name} добавлен в избранное!")
    else:
        write_msg(user_id, "Ошибка при добавлении в избранное.")

def add_to_blacklist(user_id, state):
    """Добавление в черный список"""
    current_index = state['current_index'] - 1

    if current_index < 0 or not state['candidates']:
        write_msg(user_id, "Нет текущего кандидата.")
        return

    candidate = state['candidates'][current_index]
    candidate_name = f"{candidate['first_name']} {candidate['last_name']}"

    if db.is_blacklisted(user_id, candidate['id']):
        write_msg(user_id, f"{candidate_name} уже в черном списке!")
        return

    if db.add_to_blacklist(user_id, candidate['id'], "Добавлен пользователем"):
        write_msg(user_id, f"{candidate_name} добавлен в черный список.\n")
        # Следующий
        state['current_index'] += 1
        if state['current_index'] < len(state['candidates']):
            send_candidate(user_id, state['candidates'][state['current_index']], state)
    else:
        write_msg(user_id, "Ошибка при добавлении в черный список.")


def show_favorites(user_id):
    """Показать избранных"""
    favorites = db.get_favorites(user_id)

    if not favorites:
        write_msg(user_id, "Избранных пока нет.")
        return

    message = "Ваши избранные:\n\n"
    for fav in favorites[:6]:
        message += f"{fav['first_name']} {fav['last_name']}\n"
        message += f"{fav['profile_url']}\n"

        photos = []
        for photo in [fav['photo1'], fav['photo2'], fav['photo3']]:
            if photo:
                photos.append(photo)

        if photos:
            write_msg(user_id, f"Фото {fav['first_name']}:", attachment=','.join(photos))

        message += f"Добавлен: {fav['added_date']}\n\n"

    write_msg(user_id, message)


def show_blacklist(user_id):
    """Показать черный список"""
    blacklist = db.get_blacklist(user_id)

    if not blacklist:
        write_msg(user_id, "Черный список пуст.")
        return

    message = "Черный список:\n\n"
    for idx, item in enumerate(blacklist, 1):
        message += f"{idx}. ID: {item['blacklisted_id']}\n"
        if item.get('reason'):
            message += f"   Причина: {item['reason']}\n"
        message += f"   Добавлен: {item['added_date']}\n\n"

    write_msg(user_id, message)

def start_search(user_id):
    """Начало поиска"""
    if user_id not in user_states:
        keyboard = {
            "one_time": False,
            "buttons": [
                [
                    {"action": {"type": "text", "label": "start"}, "color": "primary"}
                ]
            ]
        }
        write_msg(user_id, "Нажми на кнопку 'start'", keyboard=keyboard)
        return

    state = user_states[user_id]

    blacklist = db.get_blacklist(user_id)
    blacklist_id = [item['blacklisted_id'] for item in blacklist]
    viewed_users = db.get_viewed_users(user_id)

    candidates = vk_client.find_partners_for_user(
        source_user_id=user_id,
        count=20,
        blacklist=blacklist_id,
        viewed_users=viewed_users
    )

    if not candidates:
        write_msg(user_id, "Не найдено кандидатов по твоим критериям.")
        return

    state['candidates'] = candidates
    state['current_index'] = 0

    send_candidate(user_id, candidates[0], state)

def start_bot():
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id
            text = event.text.lower()

            if text == "привет" or text == "start" or text == "начать":
                user_info = vk_client.get_users_info(user_id)
                print(user_info)

                if not user_info:
                    keyboard = {
                        "one_time": False,
                        "buttons": [
                            [
                                {"action": {"type": "text", "label": "start"}, "color": "primary"}
                            ]
                        ]
                    }
                    write_msg(
                        user_id,
                        "Не удалось получить информацию. "
                        "Проверь настройки приватности и снова нажми кнопку 'start'",
                        keyboard=keyboard
                    )
                    continue

                db.add_user(user_info)
                user_states[user_id] = {
                    'info': user_info,
                    'candidates': [],
                    'current_index': 0
                }

                greeting = f"Привет, {user_info['first_name']} {user_info['last_name']}!\n"
                greeting += f"Твой возраст: {user_info['age']} лет\n"
                greeting += f"Твой город: {user_info['city_title']}\n\n"
                greeting += ("Вы можете найти кандидатов противоположного пола\n "
                             "со статусом 'В активном поиске' +-5 лет от Вашего возраста\n\n")
                greeting += "Нажми 'Начать поиск', чтобы найти кандидатов."

                keyboard = {
                    "one_time": False,
                    "buttons": [
                        [
                            {"action": {"type": "text", "label": "Начать поиск"}, "color": "primary"}
                        ]
                    ]
                }

                write_msg(user_id, greeting, keyboard)

            elif text == "начать поиск":
                start_search(user_id) # Вывел в функцию

            elif text == "дальше":
                if user_id not in user_states:
                    keyboard = {
                        "one_time": False,
                        "buttons": [
                            [
                                {"action": {"type": "text", "label": "start"}, "color": "primary"}
                            ]
                        ]
                    }
                    write_msg(user_id, "Нажми на кнопку 'start'", keyboard=keyboard)
                    continue

                state = user_states[user_id]
                candidates = state['candidates']
                index = state['current_index']

                if not candidates or index >= len(candidates):
                    keyboard = {
                        "one_time": False,
                        "buttons": [
                            [
                                {"action": {"type": "text", "label": "Начать поиск"}, "color": "primary"}
                            ]
                        ]
                    }
                    write_msg(user_id, "Больше нет кандидатов. Нажми 'Начать поиск' снова.", keyboard=keyboard)
                    continue

                send_candidate(user_id, candidates[index], state)

            elif text == "в избранное":
                if user_id not in user_states:
                    keyboard = {
                        "one_time": False,
                        "buttons": [
                            [
                                {"action": {"type": "text", "label": "start"}, "color": "primary"}
                            ]
                        ]
                    }
                    write_msg(user_id, "Нажми на кнопку 'start'", keyboard=keyboard)
                    continue

                state = user_states[user_id]
                add_to_favorites(user_id, state)

            elif text == "в черный список":
                if user_id not in user_states:
                    keyboard = {
                        "one_time": False,
                        "buttons": [
                            [
                                {"action": {"type": "text", "label": "start"}, "color": "primary"}
                            ]
                        ]
                    }
                    write_msg(user_id, "Нажми на кнопку 'start'", keyboard=keyboard)
                    continue

                state = user_states[user_id]
                add_to_blacklist(user_id, state)

            elif text == "показать избранное":
                show_favorites(user_id)

            elif text == "показать черный список":
                show_blacklist(user_id)

            else:
                keyboard = {
                    "one_time": False,
                    "buttons": [
                        [
                            {"action": {"type": "text", "label": "Дальше"}, "color": "primary"},
                        ],
                        [
                            {"action": {"type": "text", "label": "В избранное"}, "color": "positive"},
                            {"action": {"type": "text", "label": "В черный список"}, "color": "negative"}

                        ],
                        [
                            {"action": {"type": "text", "label": "Показать избранное"}, "color": "secondary"},
                            {"action": {"type": "text", "label": "Показать черный список"}, "color": "secondary"}
                        ]
                    ]
                }
                write_msg(user_id,
                          "Не понял команду. "
                          "Используй кнопки",
                          keyboard=keyboard
                          )
