"""
Модуль тестирования бота VKinder.

Содержит тесты для проверки:
- Отправки сообщений
- Поиска кандидатов
- Добавления в избранное и черный список
- Работы с базой данных
"""

import sys
import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from vk_api.longpoll import VkEventType

# Добавляем путь к корневой папке проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.vk_bot import (
    write_msg,
    send_candidate,
    add_to_favorites,
    add_to_blacklist,
    show_favorites,
    show_blacklist,
    start_search,
    start_bot,
    user_states,
    db,
    vk_client,
    vk
)


@pytest.fixture
def mock_vk():
    """Фикстура для мока VK API."""
    with patch('bot.vk_bot.vk') as mock:
        # Мокаем messages.send, чтобы не отправлять реальные сообщения
        mock.messages.send.return_value = {'response': 1}
        yield mock


@pytest.fixture
def mock_db():
    """Фикстура для мока базы данных."""
    with patch('bot.vk_bot.db') as mock:
        yield mock


@pytest.fixture
def mock_vk_client():
    """Фикстура для мока VK клиента."""
    with patch('bot.vk_bot.vk_client') as mock:
        yield mock


@pytest.fixture
def sample_user():
    """Фикстура с данными тестового пользователя."""
    return {
        'user_id': 123456789,
        'first_name': 'Иван',
        'last_name': 'Иванов',
        'age': 25,
        'sex': 2,
        'city_id': 1,
        'city_title': 'Москва',
        'domain': 'ivan_ivanov'
    }


@pytest.fixture
def sample_candidate():
    """Фикстура с данными тестового кандидата."""
    return {
        'id': 987654321,
        'first_name': 'Анна',
        'last_name': 'Петрова',
        'age': 24,
        'domain': 'anna_petrova',
        'bdate': '15.03.1999'
    }


@pytest.fixture
def sample_photos():
    """Фикстура с данными тестовых фото."""
    return [
        {'attachment': 'photo123_456', 'likes': 15},
        {'attachment': 'photo123_457', 'likes': 10},
        {'attachment': 'photo123_458', 'likes': 5}
    ]


def test_write_msg_without_attachment(mock_vk):
    """
    Тест отправки сообщения без вложений и клавиатуры.
    """
    # Arrange
    user_id = 123456789
    message = "Тестовое сообщение"

    # Act
    write_msg(user_id, message)

    # Assert
    mock_vk.messages.send.assert_called_once()
    call_args = mock_vk.messages.send.call_args[1]
    assert call_args['user_id'] == user_id
    assert call_args['message'] == message
    assert 'random_id' in call_args
    assert 'keyboard' not in call_args
    assert 'attachment' not in call_args


def test_write_msg_with_keyboard(mock_vk):
    """
    Тест отправки сообщения с клавиатурой.
    """
    # Arrange
    user_id = 123456789
    message = "Выберите действие"
    keyboard = {
        "one_time": False,
        "buttons": [
            [
                {"action": {"type": "text", "label": "Дальше"},
                 "color": "primary"}
            ]
        ]
    }

    # Act
    write_msg(user_id, message, keyboard=keyboard)

    # Assert
    mock_vk.messages.send.assert_called_once()
    call_args = mock_vk.messages.send.call_args[1]
    assert call_args['keyboard'] == json.dumps(keyboard)


def test_write_msg_with_attachment(mock_vk):
    """
    Тест отправки сообщения с вложением (фото).
    """
    # Arrange
    user_id = 123456789
    message = "Фото профиля"
    attachment = "photo123_456"

    # Act
    write_msg(user_id, message, attachment=attachment)

    # Assert
    mock_vk.messages.send.assert_called_once()
    call_args = mock_vk.messages.send.call_args[1]
    assert call_args['attachment'] == attachment


def test_send_candidate_success(
    mock_vk,
    mock_vk_client,
    mock_db,
    sample_candidate,
    sample_photos
):
    """
    Тест успешной отправки кандидата.
    """
    # Arrange
    user_id = 123456789
    state = {'current_index': 0}
    mock_vk_client.get_top_3_photos.return_value = sample_photos
    mock_db.add_viewed_user.return_value = True

    # Act
    send_candidate(user_id, sample_candidate, state)

    # Assert
    mock_vk_client.get_top_3_photos.assert_called_once_with(
        sample_candidate['id']
    )
    mock_db.add_viewed_user.assert_called_once_with(
        user_id, sample_candidate['id']
    )
    assert state['current_index'] == 1


def test_send_candidate_without_photos(
    mock_vk,
    mock_vk_client,
    mock_db,
    sample_candidate
):
    """
    Тест отправки кандидата без фотографий.
    """
    # Arrange
    user_id = 123456789
    state = {'current_index': 0}
    mock_vk_client.get_top_3_photos.return_value = []

    # Act
    send_candidate(user_id, sample_candidate, state)

    # Assert
    mock_vk_client.get_top_3_photos.assert_called_once()
    mock_db.add_viewed_user.assert_called_once_with(
        user_id, sample_candidate['id']
    )
    assert state['current_index'] == 1


def test_send_candidate_message_format(
    mock_vk,
    mock_vk_client,
    mock_db,
    sample_candidate,
    sample_photos
):
    """
    Тест формата сообщения с кандидатом.
    """
    # Arrange
    user_id = 123456789
    state = {'current_index': 0}
    mock_vk_client.get_top_3_photos.return_value = sample_photos

    with patch('bot.vk_bot.write_msg') as mock_write_msg:
        # Act
        send_candidate(user_id, sample_candidate, state)

        # Assert
        mock_write_msg.assert_called_once()
        call_args = mock_write_msg.call_args[0]
        message = call_args[1]
        assert sample_candidate['first_name'] in message
        assert sample_candidate['last_name'] in message
        assert f"https://vk.com/{sample_candidate['domain']}" in message
        assert f"Возраст: {sample_candidate['age']}" in message


def test_add_to_favorites_success(
    mock_db,
    mock_vk_client,
    sample_candidate,
    sample_photos
):
    """
    Тест успешного добавления в избранное.
    """
    # Arrange
    user_id = 123456789
    state = {
        'candidates': [sample_candidate],
        'current_index': 1
    }
    mock_db.is_favorite.return_value = False
    mock_vk_client.get_top_3_photos.return_value = sample_photos
    mock_db.add_favorite.return_value = True

    with patch('bot.vk_bot.write_msg') as mock_write_msg:
        # Act
        add_to_favorites(user_id, state)

        # Assert
        mock_db.is_favorite.assert_called_once_with(
            user_id, sample_candidate['id']
        )
        mock_vk_client.get_top_3_photos.assert_called_once_with(
            sample_candidate['id']
        )
        mock_db.add_favorite.assert_called_once()
        mock_write_msg.assert_called_once()
        assert "добавлен в избранное" in mock_write_msg.call_args[0][1]


def test_add_to_favorites_already_exists(mock_db, sample_candidate):
    """
    Тест попытки добавить уже существующего в избранном.
    """
    # Arrange
    user_id = 123456789
    state = {
        'candidates': [sample_candidate],
        'current_index': 1
    }
    mock_db.is_favorite.return_value = True

    with patch('bot.vk_bot.write_msg') as mock_write_msg:
        # Act
        add_to_favorites(user_id, state)

        # Assert
        mock_db.is_favorite.assert_called_once()
        mock_db.add_favorite.assert_not_called()
        mock_write_msg.assert_called_once()
        assert "уже в избранном" in mock_write_msg.call_args[0][1]


def test_add_to_favorites_no_candidate(mock_db):
    """
    Тест добавления в избранное без текущего кандидата.
    """
    # Arrange
    user_id = 123456789
    state = {
        'candidates': [],
        'current_index': 0
    }

    with patch('bot.vk_bot.write_msg') as mock_write_msg:
        # Act
        add_to_favorites(user_id, state)

        # Assert
        mock_db.is_favorite.assert_not_called()
        mock_write_msg.assert_called_once()
        assert "Нет текущего кандидата" in mock_write_msg.call_args[0][1]


def test_add_to_blacklist_success(mock_db, sample_candidate):
    """
    Тест успешного добавления в черный список.
    """
    # Arrange
    user_id = 123456789
    state = {
        'candidates': [sample_candidate],
        'current_index': 1
    }
    mock_db.is_blacklisted.return_value = False
    mock_db.add_to_blacklist.return_value = True

    with patch('bot.vk_bot.write_msg') as mock_write_msg:
        # Act
        add_to_blacklist(user_id, state)

        # Assert
        mock_db.is_blacklisted.assert_called_once_with(
            user_id, sample_candidate['id']
        )
        mock_db.add_to_blacklist.assert_called_once()
        mock_write_msg.assert_called_once()
        assert "добавлен в черный список" in mock_write_msg.call_args[0][1]
        assert state['current_index'] == 2


def test_add_to_blacklist_already_exists(mock_db, sample_candidate):
    """
    Тест попытки добавить уже существующего в черном списке.
    """
    # Arrange
    user_id = 123456789
    state = {
        'candidates': [sample_candidate],
        'current_index': 1
    }
    mock_db.is_blacklisted.return_value = True

    with patch('bot.vk_bot.write_msg') as mock_write_msg:
        # Act
        add_to_blacklist(user_id, state)

        # Assert
        mock_db.is_blacklisted.assert_called_once()
        mock_db.add_to_blacklist.assert_not_called()
        mock_write_msg.assert_called_once()
        assert "уже в черном списке" in mock_write_msg.call_args[0][1]


def test_show_favorites_success(mock_db):
    """
    Тест успешного отображения избранных.
    """
    # Arrange
    user_id = 123456789
    favorites = [
        {
            'first_name': 'Анна',
            'last_name': 'Петрова',
            'profile_url': 'https://vk.com/anna',
            'photo1': 'photo1',
            'photo2': 'photo2',
            'photo3': 'photo3',
            'added_date': '2024-01-01'
        }
    ]
    mock_db.get_favorites.return_value = favorites

    with patch('bot.vk_bot.write_msg') as mock_write_msg:
        # Act
        show_favorites(user_id)

        # Assert
        mock_db.get_favorites.assert_called_once_with(user_id)
        mock_write_msg.assert_called()
        call_args = mock_write_msg.call_args_list
        assert any("Анна Петрова" in str(call) for call in call_args)


def test_show_favorites_empty(mock_db):
    """
    Тест отображения пустого списка избранных.
    """
    # Arrange
    user_id = 123456789
    mock_db.get_favorites.return_value = []

    with patch('bot.vk_bot.write_msg') as mock_write_msg:
        # Act
        show_favorites(user_id)

        # Assert
        mock_db.get_favorites.assert_called_once_with(user_id)
        mock_write_msg.assert_called_once()
        assert "Избранных пока нет" in mock_write_msg.call_args[0][1]


def test_show_blacklist_success(mock_db):
    """
    Тест успешного отображения черного списка.
    """
    # Arrange
    user_id = 123456789
    blacklist = [
        {
            'blacklisted_id': 987654321,
            'reason': 'Не подходит по возрасту',
            'added_date': '2024-01-01'
        }
    ]
    mock_db.get_blacklist.return_value = blacklist

    with patch('bot.vk_bot.write_msg') as mock_write_msg:
        # Act
        show_blacklist(user_id)

        # Assert
        mock_db.get_blacklist.assert_called_once_with(user_id)
        mock_write_msg.assert_called_once()
        message = mock_write_msg.call_args[0][1]
        assert "987654321" in message
        assert "Не подходит по возрасту" in message


def test_show_blacklist_empty(mock_db):
    """
    Тест отображения пустого черного списка.
    """
    # Arrange
    user_id = 123456789
    mock_db.get_blacklist.return_value = []

    with patch('bot.vk_bot.write_msg') as mock_write_msg:
        # Act
        show_blacklist(user_id)

        # Assert
        mock_db.get_blacklist.assert_called_once_with(user_id)
        mock_write_msg.assert_called_once()
        assert "Черный список пуст" in mock_write_msg.call_args[0][1]


def test_start_search_success(
    mock_db,
    mock_vk_client,
    sample_candidate
):
    """
    Тест успешного начала поиска.
    """
    # Arrange
    user_id = 123456789
    user_states[user_id] = {
        'info': {'user_id': user_id},
        'candidates': [],
        'current_index': 0
    }
    mock_db.get_blacklist.return_value = []
    mock_db.get_viewed_users.return_value = []
    mock_vk_client.find_partners_for_user.return_value = [sample_candidate]

    with patch('bot.vk_bot.send_candidate') as mock_send_candidate:
        # Act
        start_search(user_id)

        # Assert
        mock_db.get_blacklist.assert_called_once_with(user_id)
        mock_db.get_viewed_users.assert_called_once_with(user_id)
        mock_vk_client.find_partners_for_user.assert_called_once()
        assert len(user_states[user_id]['candidates']) == 1
        mock_send_candidate.assert_called_once_with(
            user_id, sample_candidate, user_states[user_id]
        )


def test_start_search_no_candidates(mock_db, mock_vk_client):
    """
    Тест поиска без результатов.
    """
    # Arrange
    user_id = 123456789
    user_states[user_id] = {
        'info': {'user_id': user_id},
        'candidates': [],
        'current_index': 0
    }
    mock_db.get_blacklist.return_value = []
    mock_db.get_viewed_users.return_value = []
    mock_vk_client.find_partners_for_user.return_value = []

    with patch('bot.vk_bot.write_msg') as mock_write_msg:
        # Act
        start_search(user_id)

        # Assert
        mock_write_msg.assert_called_once()
        assert "Не найдено кандидатов" in mock_write_msg.call_args[0][1]


def test_start_search_user_not_initialized():
    """
    Тест поиска для неинициализированного пользователя.
    """
    # Arrange
    user_id = 999999999
    if user_id in user_states:
        del user_states[user_id]

    with patch('bot.vk_bot.write_msg') as mock_write_msg:
        # Act
        start_search(user_id)

        # Assert
        mock_write_msg.assert_called_once()
        assert "start" in mock_write_msg.call_args[0][1]


def test_start_bot_hello_command(mock_db, mock_vk_client, sample_user):
    """
    Тест обработки команды 'привет'.

    Проверяет, что при получении сообщения "привет" бот:
    - Получает информацию о пользователе через VK API
    - Сохраняет пользователя в БД
    - Инициализирует состояние
    - Отправляет приветственное сообщение
    """
    # Arrange
    user_id = 123456789
    mock_vk_client.get_users_info.return_value = sample_user

    # Создаем мок события
    mock_event = Mock()
    mock_event.type = VkEventType.MESSAGE_NEW
    mock_event.to_me = True
    mock_event.user_id = user_id
    mock_event.text = "привет"

    # Мокаем longpoll целиком
    with patch('bot.vk_bot.longpoll') as mock_longpoll, \
         patch('bot.vk_bot.write_msg') as mock_write_msg:
        mock_longpoll.listen.return_value = [mock_event]

        # Act
        start_bot()

        # Assert
        mock_vk_client.get_users_info.assert_called_once_with(user_id)
        mock_db.add_user.assert_called_once_with(sample_user)
        mock_write_msg.assert_called()
        # Проверяем, что приветствие содержит имя пользователя
        call_args = mock_write_msg.call_args[0]
        assert sample_user['first_name'] in call_args[1]
        assert sample_user['last_name'] in call_args[1]
