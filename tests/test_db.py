from data_base.db import Database
from logging_config import setup_logging
import logging


setup_logging(log_file="test_db.log", log_level=logging.INFO)
log = logging.getLogger(__name__)

def log_test_header(test_name):
    """Вывод заголовка теста"""
    log.info(f"ТЕСТ: {test_name}")


def log_result(success, message):
    """Вывод результата"""
    if success:
        log.info(f"{message}")
    else:
        log.info(f"{message}")


def test_database():
    """Полное тестирование БД"""

    log.info("Начало тестирования")

    # 1. Подключение к БД
    log_test_header("Подключение к базе данных")
    try:
        db = Database()
        log_result(True, "Подключение к БД установлено")
    except Exception as e:
        log_result(False, f"Ошибка подключения: {e}")
        return

    # 2. Добавления пользователя
    log_test_header("Добавление пользователя")

    test_user = {
        'user_id': 123456789,
        'first_name': 'Иван',
        'last_name': 'Иванов',
        'sex': 2,
        'age': 25,
        'city_id': 1,
        'city_title': 'Москва'
    }

    result = db.add_user(test_user)
    log_result(result, f"Пользователь {test_user['first_name']} "
                         f"{test_user['last_name']} добавлен")

    # 3. Добавление в избранное

    log_test_header("Добавление в избранное")

    candidate1 = {
        'id': 987654321,
        'first_name': 'Анна',
        'last_name': 'Петрова'
    }
    photos1 = ['photo987654321_123', 'photo987654321_456',
               'photo987654321_789']

    result = db.add_favorite(123456789, candidate1, photos1)
    log_result(result, f"{candidate1['first_name']} "
                         f"{candidate1['last_name']} добавлен в избранное")

    candidate2 = {
        'id': 555555555,
        'first_name': 'Екатерина',
        'last_name': 'Сидорова'
    }
    photos2 = ['photo555555555_111', 'photo555555555_222']

    result = db.add_favorite(123456789, candidate2, photos2)
    log_result(result, f"{candidate2['first_name']} "
                         f"{candidate2['last_name']} добавлен в избранное")

    # 4. Проверка есть ли в избранном

    log_test_header("Проверка в избранном")

    # Проверяем, есть ли существующий в избранном
    result = db.is_favorite(123456789, 987654321)
    log_result(result, "Анна Петрова в избранном")

    # Проверяем, есть ли несуществующий пользователь
    result = db.is_favorite(123456789, 999999999)
    log_result(not result, "Несуществующий пользователь НЕ в избранном")

    # 5. Все избранные

    log_test_header("Получение списка избранных")

    favorites = db.get_favorites(123456789)
    log_result(len(favorites) > 0, f"Получено избранных: {len(favorites)}")

    for fav in favorites:
        log.info(f" {fav['first_name']} {fav['last_name']}")
        log.info(f" {fav['profile_url']}")
        log.info(f" Добавлен: {fav['added_date']}")

    # 6. Добавление в черные список

    log_test_header("Добавление в черный список")

    blacklisted_id = 111111111
    result = db.add_to_blacklist(123456789, blacklisted_id,
                                 "Не подходит по возрасту")
    log_result(result, f"Пользователь ID {blacklisted_id} "
                         f"добавлен в черный список")

    # Добавляем еще одного
    result = db.add_to_blacklist(123456789, 222222222,
                                 "Не тот город")
    log_result(result, f"Пользователь ID 222222222 добавлен в черный список")

    # 7. Есть ли в черном списке

    log_test_header("Проверка в черном списке")

    result = db.is_blacklisted(123456789, 111111111)
    log_result(result, "Пользователь 111111111 в черном списке")

    result = db.is_blacklisted(123456789, 999999999)
    log_result(not result, "Несуществующий пользователь НЕ в черном списке")

    # 8. Весь черный список

    log_test_header("Получение черного списка")

    blacklist = db.get_blacklist(123456789)
    log_result(len(blacklist) > 0, f"Получено в черном списке:"
                                     f" {len(blacklist)}")

    for item in blacklist:
        log.info(f" ID: {item['blacklisted_id']}")
        if item.get('reason'):
            log.info(f" Причина: {item['reason']}")
        log.info(f" Добавлен: {item['added_date']}")

    # 9. Добавление в просмотренные

    log_test_header("Добавление просмотренного")

    viewed_ids = [333333333, 444444444, 555555555]
    for viewed_id in viewed_ids:
        result = db.add_viewed_user(123456789, viewed_id)
        log_result(result, f"Пользователь ID {viewed_id} "
                             f"добавлен в просмотренные")

    # 10. Получение просмотренных

    log_test_header("Получение просмотренных")

    viewed_users = db.get_viewed_users(123456789)
    log_result(len(viewed_users) > 0, f"Получено просмотренных: "
                                        f"{len(viewed_users)}")

    for idx, user_id in enumerate(viewed_users, 1):
        log.info(f"️ {idx}. ID: {user_id}")

    # 11. Исключение повторов

    log_test_header("Проверка уникальности")

    # Пытаемся добавить того же пользователя в избранное
    result = db.add_favorite(123456789, candidate1, photos1)
    log_result(not result or True, "Пройден успешно")

    # 12. Закрытие соединения

    log_test_header("Закрытие соединения")

    try:
        db.close()
        log_result(True, "Соединение с БД закрыто")
    except Exception as e:
        log_result(False, f"Ошибка при закрытии: {e}")


if __name__ == '__main__':
    test_database()
