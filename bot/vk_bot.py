import sys
import os
import json
import logging
import vk_api
from random import randrange
from vk_api.longpoll import VkLongPoll, VkEventType
from config import Config
from vk_api_client.vk_client import VK_client
from data_base.db import Database
from logging_config import setup_logging

# Добавляем путь к корневой папке проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настраиваем логирование
setup_logging(log_file="vkinder.log", log_level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    vk_session = vk_api.VkApi(token=Config.group_token)
    longpoll = VkLongPoll(vk_session)
    vk = vk_session.get_api()
    logger.info("VK API успешно инициализирован")
except Exception as e:
    logger.critical(f"Ошибка инициализации VK API: {e}")
    sys.exit(1)

vk_client = VK_client()
user_states = {}
db = Database()

logger.info("Бот VKinder инициализирован")


def write_msg(user_id, message, keyboard=None, attachment=None):
    """
    Отправляет сообщение пользователю.
    """
    params = {
        'user_id': user_id,
        'message': message,
        'random_id': randrange(10 ** 7)
    }

    if keyboard:
        params['keyboard'] = json.dumps(keyboard)
    if attachment:
        params['attachment'] = attachment

    try:
        vk.messages.send(**params)
        logger.debug(f"Сообщение отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
        raise


def send_candidate(user_id, candidate, state):
    """
    Отправляет кандидата с фото и клавиатурой.
    Добавляет кандидата в просмотренные.
    """
    try:
        logger.info(f"Отправка кандидата {candidate.get('id')} пользователю {user_id}")

        photos = vk_client.get_top_3_photos(candidate['id'])
        logger.debug(f"Получено {len(photos)} фото для кандидата")

        message = f"{candidate['first_name']} {candidate['last_name']}\n"
        message += f"https://vk.com/{candidate.get('domain', '')}\n"

        if candidate.get('age'):
            message += f"Возраст: {candidate['age']}\n"

        attachment = ','.join([p['attachment'] for p in photos]) if photos else ''

        keyboard = {
            "one_time": False,
            "buttons": [
                [
                    {"action": {"type": "text", "label": "Дальше"},
                     "color": "primary"}
                ],
                [
                    {"action": {"type": "text", "label": "В избранное"},
                     "color": "positive"},
                    {"action": {"type": "text", "label": "В черный список"},
                     "color": "negative"}
                ],
                [
                    {"action": {"type": "text", "label": "Показать избранное"},
                     "color": "secondary"},
                    {"action": {"type": "text", "label": "Показать черный список"},
                     "color": "secondary"}
                ]
            ]
        }

        write_msg(user_id, message, keyboard=keyboard, attachment=attachment)
        db.add_viewed_user(user_id, candidate['id'])
        state['current_index'] += 1

        logger.info(f"Кандидат {candidate.get('id')} отправлен")
    except Exception as e:
        logger.error(f"Ошибка при отправке кандидата: {e}")
        write_msg(user_id, "Произошла ошибка. Попробуйте снова.")


def add_to_favorites(user_id, state):
    """Добавляет текущего кандидата в избранное."""
    logger.info(f"Пользователь {user_id} добавляет в избранное")

    current_index = state['current_index'] - 1

    if current_index < 0 or not state['candidates']:
        logger.warning(f"Пользователь {user_id} попытался добавить в избранное без кандидата")
        write_msg(user_id, "Нет текущего кандидата для добавления.")
        return

    candidate = state['candidates'][current_index]
    candidate_name = f"{candidate['first_name']} {candidate['last_name']}"

    try:
        if db.is_favorite(user_id, candidate['id']):
            logger.info(f"Кандидат {candidate['id']} уже в избранном")
            write_msg(user_id, f"{candidate_name} уже в избранном!")
            return
    except Exception as e:
        logger.error(f"Ошибка проверки избранного: {e}")
        write_msg(user_id, "Ошибка при проверке избранного.")
        return

    try:
        photos = vk_client.get_top_3_photos(candidate['id'])
        photo_attachments = [p['attachment'] for p in photos] if photos else []
    except Exception as e:
        logger.error(f"Ошибка получения фото: {e}")
        photo_attachments = []

    try:
        if db.add_favorite(user_id, candidate, photo_attachments):
            logger.info(f"Кандидат {candidate['id']} добавлен в избранное")
            write_msg(user_id, f"{candidate_name} добавлен в избранное!")
        else:
            logger.error(f"Ошибка добавления в избранное")
            write_msg(user_id, "Ошибка при добавлении в избранное.")
    except Exception as e:
        logger.error(f"Ошибка сохранения в избранное: {e}")
        write_msg(user_id, "Ошибка при добавлении в избранное.")


def add_to_blacklist(user_id, state):
    """Добавляет текущего кандидата в черный список."""
    logger.info(f"Пользователь {user_id} добавляет в черный список")

    current_index = state['current_index'] - 1

    if current_index < 0 or not state['candidates']:
        logger.warning(f"Пользователь {user_id} попытался добавить в черный список без кандидата")
        write_msg(user_id, "Нет текущего кандидата.")
        return

    candidate = state['candidates'][current_index]
    candidate_name = f"{candidate['first_name']} {candidate['last_name']}"

    try:
        if db.is_blacklisted(user_id, candidate['id']):
            logger.info(f"Кандидат {candidate['id']} уже в черном списке")
            write_msg(user_id, f"{candidate_name} уже в черном списке!")
            return
    except Exception as e:
        logger.error(f"Ошибка проверки черного списка: {e}")
        write_msg(user_id, "Ошибка при проверке черного списка.")
        return

    try:
        if db.add_to_blacklist(user_id, candidate['id'], "Добавлен пользователем"):
            logger.info(f"Кандидат {candidate['id']} добавлен в черный список")
            write_msg(user_id, f"{candidate_name} добавлен в черный список.\n")
            state['current_index'] += 1
        else:
            logger.error(f"Ошибка добавления в черный список")
            write_msg(user_id, "Ошибка при добавлении в черный список.")
    except Exception as e:
        logger.error(f"Ошибка сохранения в черный список: {e}")
        write_msg(user_id, "Ошибка при добавлении в черный список.")


def show_favorites(user_id):
    """Показывает список избранных кандидатов."""
    logger.info(f"Пользователь {user_id} запросил избранное")

    try:
        favorites = db.get_favorites(user_id)
        logger.debug(f"Получено {len(favorites)} избранных")
    except Exception as e:
        logger.error(f"Ошибка получения избранных: {e}")
        write_msg(user_id, "Ошибка при получении избранных.")
        return

    if not favorites:
        logger.info(f"У пользователя {user_id} нет избранных")
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
            write_msg(
                user_id,
                f"Фото {fav['first_name']}:",
                attachment=','.join(photos)
            )

        message += f"Добавлен: {fav['added_date']}\n\n"

    write_msg(user_id, message)


def show_blacklist(user_id):
    """Показывает черный список пользователя."""
    logger.info(f"Пользователь {user_id} запросил черный список")

    try:
        blacklist = db.get_blacklist(user_id)
        logger.debug(f"Получено {len(blacklist)} записей в черном списке")
    except Exception as e:
        logger.error(f"Ошибка получения черного списка: {e}")
        write_msg(user_id, "Ошибка при получении черного списка.")
        return

    if not blacklist:
        logger.info(f"У пользователя {user_id} пустой черный список")
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
    """Запускает поиск кандидатов."""
    logger.info(f"Пользователь {user_id} начал поиск")

    if user_id not in user_states:
        logger.warning(f"Пользователь {user_id} не инициализирован")
        keyboard = {
            "one_time": False,
            "buttons": [
                [
                    {"action": {"type": "text", "label": "start"},
                     "color": "primary"}
                ]
            ]
        }
        write_msg(user_id, "Нажми на кнопку 'start'", keyboard=keyboard)
        return

    state = user_states[user_id]

    try:
        blacklist = db.get_blacklist(user_id)
        blacklist_id = [item['blacklisted_id'] for item in blacklist]
        viewed_users = db.get_viewed_users(user_id)
        logger.debug(f"Черный список: {len(blacklist_id)}, просмотренных: {len(viewed_users)}")
    except Exception as e:
        logger.error(f"Ошибка получения списков: {e}")
        write_msg(user_id, "Ошибка при получении данных.")
        return

    try:
        candidates = vk_client.find_partners_for_user(
            source_user_id=user_id,
            count=20,
            blacklist=blacklist_id,
            viewed_users=viewed_users
        )
        logger.info(f"Найдено {len(candidates)} кандидатов")
    except Exception as e:
        logger.error(f"Ошибка поиска кандидатов: {e}")
        write_msg(user_id, "Ошибка при поиске кандидатов.")
        return

    if not candidates:
        logger.info(f"Кандидаты не найдены")
        write_msg(user_id, "Не найдено кандидатов по твоим критериям.")
        return

    state['candidates'] = candidates
    state['current_index'] = 0

    send_candidate(user_id, candidates[0], state)


def start_bot():
    """
    Запускает бота и обрабатывает команды пользователя.
    Доступные команды: привет, начать поиск, дальше,
    в избранное, в черный список, показать избранное, показать черный список.
    """
    logger.info("=" * 50)
    logger.info("БОТ VKINDER ЗАПУЩЕН")
    logger.info("=" * 50)

    for event in longpoll.listen():
        try:
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                user_id = event.user_id
                text = event.text.lower()

                logger.debug(f"Получено сообщение от {user_id}: {text}")

                if text == "привет" or text == "start" or text == "начать":
                    logger.info(f"Команда 'привет' от пользователя {user_id}")
                    user_info = vk_client.get_users_info(user_id)
                    logger.info(f"Данные пользователя: {user_info}")

                    if not user_info:
                        logger.warning(f"Не удалось получить информацию о пользователе {user_id}")
                        keyboard = {
                            "one_time": False,
                            "buttons": [
                                [
                                    {"action": {"type": "text", "label": "start"},
                                     "color": "primary"}
                                ]
                            ]
                        }
                        write_msg(
                            user_id,
                            "Не удалось получить информацию. "
                            "Проверь настройки приватности и снова нажми кнопку "
                            "'start'",
                            keyboard=keyboard
                        )
                        continue

                    try:
                        db.add_user(user_info)
                        logger.info(f"Пользователь {user_id} сохранён в БД")
                    except Exception as e:
                        logger.error(f"Ошибка сохранения пользователя: {e}")

                    user_states[user_id] = {
                        'info': user_info,
                        'candidates': [],
                        'current_index': 0
                    }

                    greeting = (
                        f"Привет, {user_info['first_name']} "
                        f"{user_info['last_name']}!\n"
                        f"Твой возраст: {user_info['age']} лет\n"
                        f"Твой город: {user_info['city_title']}\n\n"
                        "Вы можете найти кандидатов противоположного пола\n"
                        "со статусом 'В активном поиске' +-5 лет от Вашего "
                        "возраста\n\n"
                        "Нажми 'Начать поиск', чтобы найти кандидатов."
                    )

                    keyboard = {
                        "one_time": False,
                        "buttons": [
                            [
                                {"action": {"type": "text",
                                            "label": "Начать поиск"},
                                 "color": "primary"}
                            ]
                        ]
                    }

                    write_msg(user_id, greeting, keyboard)

                elif text == "начать поиск":
                    start_search(user_id)

                elif text == "дальше":
                    if user_id not in user_states:
                        logger.warning(f"Пользователь {user_id} не инициализирован")
                        keyboard = {
                            "one_time": False,
                            "buttons": [
                                [
                                    {"action": {"type": "text", "label": "start"},
                                     "color": "primary"}
                                ]
                            ]
                        }
                        write_msg(
                            user_id,
                            "Нажми на кнопку 'start'",
                            keyboard=keyboard
                        )
                        continue

                    state = user_states[user_id]
                    candidates = state['candidates']
                    index = state['current_index']

                    if not candidates or index >= len(candidates):
                        logger.info(f"У пользователя {user_id} закончились кандидаты")
                        keyboard = {
                            "one_time": False,
                            "buttons": [
                                [
                                    {"action": {"type": "text",
                                                "label": "Начать поиск"},
                                     "color": "primary"}
                                ]
                            ]
                        }
                        write_msg(
                            user_id,
                            "Больше нет кандидатов. "
                            "Нажми 'Начать поиск' снова.",
                            keyboard=keyboard
                        )
                        continue

                    send_candidate(user_id, candidates[index], state)

                elif text == "в избранное":
                    if user_id not in user_states:
                        logger.warning(f"Пользователь {user_id} не инициализирован")
                        keyboard = {
                            "one_time": False,
                            "buttons": [
                                [
                                    {"action": {"type": "text",
                                                "label": "start"},
                                     "color": "primary"}
                                ]
                            ]
                        }
                        write_msg(
                            user_id,
                            "Нажми на кнопку 'start'",
                            keyboard=keyboard
                        )
                        continue

                    state = user_states[user_id]
                    add_to_favorites(user_id, state)

                elif text == "в черный список":
                    if user_id not in user_states:
                        logger.warning(f"Пользователь {user_id} не инициализирован")
                        keyboard = {
                            "one_time": False,
                            "buttons": [
                                [
                                    {"action": {"type": "text",
                                                "label": "start"},
                                     "color": "primary"}
                                ]
                            ]
                        }
                        write_msg(
                            user_id,
                            "Нажми на кнопку 'start'",
                            keyboard=keyboard
                        )
                        continue

                    state = user_states[user_id]
                    add_to_blacklist(user_id, state)

                elif text == "показать избранное":
                    show_favorites(user_id)

                elif text == "показать черный список":
                    show_blacklist(user_id)

                else:
                    logger.debug(f"Неизвестная команда от {user_id}: {text}")
                    keyboard = {
                        "one_time": False,
                        "buttons": [
                            [
                                {"action": {"type": "text",
                                            "label": "Дальше"},
                                 "color": "primary"},
                            ],
                            [
                                {"action": {"type": "text",
                                            "label": "В избранное"},
                                 "color": "positive"},
                                {"action": {"type": "text",
                                            "label": "В черный список"},
                                 "color": "negative"}

                            ],
                            [
                                {"action": {"type": "text",
                                            "label": "Показать избранное"},
                                 "color": "secondary"},
                                {"action": {"type": "text",
                                            "label": "Показать черный список"},
                                 "color": "secondary"}
                            ]
                        ]
                    }
                    write_msg(
                        user_id,
                        "Не понял команду. "
                        "Используй кнопки",
                        keyboard=keyboard
                    )
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}", exc_info=True)
            try:
                write_msg(user_id, "Произошла ошибка. Попробуйте снова.")
            except:
                pass

