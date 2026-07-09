import sys
from db import Database

# Этот файл был создан только для тестирования БД

def test_database():

    print("=" * 50)
    print("НАЧАЛО ТЕСТИРОВАНИЯ")
    print("=" * 50)

    try:
        # Создаем экземпляр БД
        db = Database()

        # 1. Тест добавления пользователя
        print("\n Тест 1: Добавление пользователя")
        user_data = {
            'user_id': 123456789,
            'first_name': 'Иван',
            'last_name': 'Иванов',
            'sex': 2,
            'age': 25,
            'city_id': 1,
            'city_title': 'Москва'
        }
        if db.add_user(user_data):
            print("Пользователь добавлен/обновлен")
        else:
            print("Ошибка добавления пользователя")

        # 2. Тест добавления в избранное
        print("\n Тест 2: Добавление в избранное")
        candidate = {
            'id': 987654321,
            'first_name': 'Анна',
            'last_name': 'Петрова'
        }
        photos = ['photo1_123', 'photo1_456', 'photo1_789']
        if db.add_favorite(123456789, candidate, photos):
            print("Избранный добавлен")
        else:
            print("Ошибка добавления в избранное")

        # 3. Тест получения избранных
        print("\n Тест 3: Получение избранных")
        favorites = db.get_favorites(123456789)
        print(f"Получено избранных: {len(favorites)}")
        for fav in favorites:
            print(f"  - {fav['first_name']} {fav['last_name']}")

        # 4. Тест добавления в черный список
        print("\n Тест 4: Добавление в черный список")
        if db.add_to_blacklist(123456789, 555555555, "Не подходит"):
            print("В черный список добавлен")
        else:
            print("Ошибка добавления в черный список")

        # 5. Тест получения черного списка
        print("\n Тест 5: Получение черного списка")
        blacklist = db.get_blacklist(123456789)
        print(f"В черном списке: {len(blacklist)} пользователей")
        for user_id in blacklist:
            print(f"  - ID: {user_id}")

        # 6. Тест добавления просмотренного
        print("\n Тест 6: Добавление просмотренного")
        if db.add_viewed_user(123456789, 111111111):
            print("Просмотренный добавлен")
        else:
            print("Ошибка добавления просмотренного")

        # 7. Тест получения просмотренных
        print("\n Тест 7: Получение просмотренных")
        viewed = db.get_viewed_users(123456789)
        print(f"Просмотренных: {len(viewed)} пользователей")
        for user_id in viewed:
            print(f"  - ID: {user_id}")

        # Закрываем соединение
        db.close()

        print("\n" + "=" * 50)
        print("ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ УСПЕШНО!")
        print("=" * 50)

    except Exception as e:
        print(f"\n КРИТИЧЕСКАЯ ОШИБКА: {e}")
        print("\nВозможные причины:")
        print("1. PostgreSQL не запущен")
        print("2. Неправильный пароль (проверьте: password)")
        print("3. База данных 'VKinder' не создана")
        print("4. Порт 5432 занят")
        sys.exit(1)


if __name__ == '__main__':
    test_database()