import sys
import os
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

    photos = vk_client.get_user_photos(candidate['id'])

    message = f"{candidate['first_name']} {candidate['last_name']}\n"
    message += f"https://vk.com/{candidate.get('domain', '')}\n"

    age = vk_client._calculate_age(candidate.get('bdate'))
    if age:
        message += f"Возраст: {age}\n"

    attachment = ','.join([p['attachment'] for p in photos]) if photos else ''

    keyboard = {
        "one_time": False,
        "buttons": [
            [
                {"action": {"type": "text", "label": "Дальше"}, "color": "primary"},
                {"action": {"type": "text", "label": "В избранное"}, "color": "positive"}
            ],
            [
                {"action": {"type": "text", "label": "Показать избранное"}, "color": "secondary"}
            ]
        ]
    }

    write_msg(user_id, message, keyboard=keyboard, attachment=attachment)

    state['current_index'] += 1

def start_bot():
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id
            text = event.text.lower()

            if text == "привет" or text == "start" or text == "начать":
                user_info = vk_client.get_user_info(user_id)
                print(user_info)


                if not user_info:
                    write_msg(user_id, "Не удалось получить информацию. Проверь настройки приватности.")
                    continue

                user_states[user_id] = {
                    'info': user_info,
                    'candidates': [],
                    'current_index': 0
                }

                greeting = f"Привет, {user_info['first_name']} {user_info['last_name']}!\n"
                greeting += f"Твой возраст: {user_info['age']} лет\n"
                greeting += f"Твой город: {user_info['city_title']}\n\n"
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
                if user_id not in user_states:
                    write_msg(user_id, "Сначала напиши 'Привет'")
                    continue

                state = user_states[user_id]
                user_info = state['info']

                target_sex = 2 if user_info['sex'] == 1 else 1

                candidates = vk_client.search_users(
                    city_id=user_info['city_id'],
                    age=user_info['age'],
                    sex=target_sex,
                    count=20
                )

                if not candidates:
                    write_msg(user_id, "Не найдено кандидатов по твоим критериям.")
                    continue

                state['candidates'] = candidates
                state['current_index'] = 0

                send_candidate(user_id, candidates[0], state)

            elif text == "дальше":
                if user_id not in user_states:
                    write_msg(user_id, "Сначала напиши 'Привет'")
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
                    write_msg(user_id, "Сначала напиши 'Привет'")
                    continue

                state = user_states[user_id]
                current_index = state['current_index'] - 1

                if current_index < 0 or not state['candidates']:
                    write_msg(user_id, "Нет текущего кандидата для добавления.")
                    continue

                candidate = state['candidates'][current_index]
                candidate_name = f"{candidate['first_name']} {candidate['last_name']}"

                # TODO: Здесь будет вызов БД

                write_msg(user_id, f"✅ {candidate_name} добавлен в избранное!")

            elif text == "показать избранное":
                # TODO: Здесь будет вызов БД (напарник добавит)
                write_msg(user_id, "Список избранных (пока временно пуст).\nНапарник добавит БД позже.")
            else:
                write_msg(user_id,
                          "Не понял команду. Доступные команды: 'Привет', 'Начать поиск', 'Дальше', 'В избранное', 'Показать избранное'.")



