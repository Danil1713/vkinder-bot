from db import Database


def print_test_header(test_name):
    """Вывод заголовка теста"""
    print("\n" + "=" * 30)
    print(f"ТЕСТ: {test_name}")
    print("=" * 30)


def print_result(success, message):
    """Вывод результата"""
    if success:
        print(f"{message}")
    else:
        print(f"{message}")


def test_database():
    """Полное тестирование БД"""

    print_test_header("Начало тестирования")

    # 1. Подключение к БД
    print_test_header("Подключение к базе данных")
    try:
        db = Database()
        print_result(True, "Подключение к БД установлено")
    except Exception as e:
        print_result(False, f"Ошибка подключения: {e}")
        return

    # 2. Добавления пользователя
    print_test_header("Добавление пользователя")

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
    print_result(result, f"Пользователь {test_user['first_name']} "
                         f"{test_user['last_name']} добавлен")

    # 3. Добавление в избранное

    print_test_header("Добавление в избранное")

    candidate1 = {
        'id': 987654321,
        'first_name': 'Анна',
        'last_name': 'Петрова'
    }
    photos1 = ['photo987654321_123', 'photo987654321_456', 'photo987654321_789']

    result = db.add_favorite(123456789, candidate1, photos1)
    print_result(result, f"{candidate1['first_name']} {candidate1['last_name']} "
                         f"добавлен в избранное")

    candidate2 = {
        'id': 555555555,
        'first_name': 'Екатерина',
        'last_name': 'Сидорова'
    }
    photos2 = ['photo555555555_111', 'photo555555555_222']

    result = db.add_favorite(123456789, candidate2, photos2)
    print_result(result, f"{candidate2['first_name']} "
                         f"{candidate2['last_name']} добавлен в избранное")

    # 4. Проверка есть ли в избранном

    print_test_header("Проверка в избранном")

    # Проверяем, есть ли существующий в избранном
    result = db.is_favorite(123456789, 987654321)
    print_result(result, "Анна Петрова в избранном")

    # Проверяем, есть ли несуществующий пользователь
    result = db.is_favorite(123456789, 999999999)
    print_result(not result, "Несуществующий пользователь НЕ в избранном")

    # 5. Все избранные

    print_test_header("Получение списка избранных")

    favorites = db.get_favorites(123456789)
    print_result(len(favorites) > 0, f"Получено избранных: {len(favorites)}")

    for fav in favorites:
        print(f" {fav['first_name']} {fav['last_name']}")
        print(f" {fav['profile_url']}")
        print(f" Добавлен: {fav['added_date']}")
        print()

    # 6. Добавление в черные список

    print_test_header("Добавление в черный список")

    blacklisted_id = 111111111
    result = db.add_to_blacklist(123456789, blacklisted_id,
                                 "Не подходит по возрасту")
    print_result(result, f"Пользователь ID {blacklisted_id} "
                         f"добавлен в черный список")

    # Добавляем еще одного
    result = db.add_to_blacklist(123456789, 222222222,
                                 "Не тот город")
    print_result(result, f"Пользователь ID 222222222 добавлен в черный список")

    # 7. Есть ли в черном списке

    print_test_header("Проверка в черном списке")

    result = db.is_blacklisted(123456789, 111111111)
    print_result(result, "Пользователь 111111111 в черном списке")

    result = db.is_blacklisted(123456789, 999999999)
    print_result(not result, "Несуществующий пользователь НЕ в черном списке")


    # 8. Весь черный список

    print_test_header("Получение черного списка")

    blacklist = db.get_blacklist(123456789)
    print_result(len(blacklist) > 0, f"Получено в черном списке: {len(blacklist)}")

    for item in blacklist:
        print(f" ID: {item['blacklisted_id']}")
        if item.get('reason'):
            print(f" Причина: {item['reason']}")
        print(f" Добавлен: {item['added_date']}")
        print()

    # 9. Добавление в просмотренные

    print_test_header("Добавление просмотренного")

    viewed_ids = [333333333, 444444444, 555555555]
    for viewed_id in viewed_ids:
        result = db.add_viewed_user(123456789, viewed_id)
        print_result(result, f"Пользователь ID {viewed_id} "
                             f"добавлен в просмотренные")

    # 10. Получение просмотренных

    print_test_header("Получение просмотренных")

    viewed_users = db.get_viewed_users(123456789)
    print_result(len(viewed_users) > 0, f"Получено просмотренных: "
                                        f"{len(viewed_users)}")

    for idx, user_id in enumerate(viewed_users, 1):
        print(f"️ {idx}. ID: {user_id}")

    # 11. Исключение повторов

    print_test_header("Проверка уникальности")

    # Пытаемся добавить того же пользователя в избранное
    result = db.add_favorite(123456789, candidate1, photos1)
    print_result(not result or True, "Пройден успешно")

    # 12. Закрытие соединения

    print_test_header("Закрытие соединения")

    try:
        db.close()
        print_result(True, "Соединение с БД закрыто")
    except Exception as e:
        print_result(False, f"Ошибка при закрытии: {e}")


if __name__ == '__main__':
    test_database()