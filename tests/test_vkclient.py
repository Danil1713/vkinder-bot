from unittest.mock import Mock, patch
import pytest
from datetime import datetime
from vk_api_client.vk_client import VK_client


@pytest.fixture
def mock_vk_session():
    """
    Подменяет конструктор VkApi, чтобы он возвращал моки
    вместо реальных сессий
    """
    with patch('vk_api.VkApi') as MockVkApi:
        # Создаем инстансы-моки для group и search сессий
        mock_group_session = Mock()
        mock_search_session = Mock()

        # Метод get_api() должен возвращать разные моки для разных сессий
        mock_group_session.get_api.return_value = Mock(name='group_api')
        mock_search_session.get_api.return_value = Mock(name='search_api')

        # Конструктор VkApi будет поочередно возвращать эти два мока
        MockVkApi.side_effect = [mock_group_session, mock_search_session]

        yield {
            'group_api': mock_group_session.get_api(),
            'search_api': mock_search_session.get_api()
        }


@pytest.fixture
def client(mock_vk_session):
    """Создает экземпляр клиента с заmockанными зависимостями"""
    return VK_client()


def test_get_users_info_success(client, mock_vk_session):
    """
    Проверяем успешное получение данных.
    """
    current_year = datetime.now().year

    # Настраиваем ответ от API
    mock_vk_session['group_api'].users.get.return_value = [{
        'id': 1,
        'first_name': 'Иван',
        'last_name': 'Иванов',
        'sex': 2,
        'is_closed': False,
        'city': {'id': 10, 'title': 'Москва'},
        'bdate': f"15.05.1995"
    }]

    result = client.get_users_info(1)

    assert result == {
        'user_id': 1,
        'first_name': 'Иван',
        'last_name': 'Иванов',
        'sex': 2,
        'city_id': 10,
        'city_title': 'Москва',
        'age': current_year - 1995,
        'domain': None
    }


def test_get_users_info_closed_profile(client, mock_vk_session):
    """
    Проверяем обработку закрытого профиля.
    """
    mock_vk_session['group_api'].users.get.return_value = [{
        'id': 2,
        'is_closed': True
    }]

    result = client.get_users_info(2)
    assert result is None


def test_get_users_info_no_bdate(client, mock_vk_session):
    """
    Проверяем отсутствие города и расчет возраста.
    """
    mock_vk_session['group_api'].users.get.return_value = [{
        'id': 3,
        'first_name': 'Петр',
        'last_name': 'Петров',
        'sex': 2,
        'is_closed': False,
        'city': None,
        # bdate отсутствует
    }]

    result = client.get_users_info(3)
    assert result['age'] is None
    assert result['city_id'] is None


def test_search_opposite_filters_and_age(client, mock_vk_session):
    """
    Проверяем фильтрацию закрытых профилей, корректный расчет возраста
     при наличии года и отсутствие года в дате рождения.
    """
    current_year = datetime.now().year

    mock_vk_session['search_api'].users.search.return_value = {
        'items': [
            {
                'id': 10,
                'first_name': 'Анна',
                'last_name': 'Сидорова',
                'is_closed': False,
                'bdate': "20.06.1998"
            },
            {
                'id': 11,
                'first_name': 'Мария',
                'last_name': 'Кузнецова',
                'is_closed': True,  # Должна быть отфильтрована
                'bdate': "01.01.2000"
            },
            {
                'id': 12,
                'first_name': 'Елена',
                'last_name': 'Новикова',
                'is_closed': False,
                'bdate': "10.10"  # Год скрыт, age должен быть None
            }
        ]
    }

    results = client.search_opposite(target_sex=1, city_id=10, age_from=20, age_to=30, count=10)

    assert len(results) == 2
    assert results[0]['id'] == 10
    assert results[0]['age'] == current_year - 1998
    assert results[1]['id'] == 12
    assert results[1]['age'] is None


def test_search_opposite_api_error(client, mock_vk_session):
    """
    Проверяет обработку исключений (exception handling)
    """
    from vk_api.exceptions import ApiError

    mock_vk_session['search_api'].users.search.side_effect = ApiError(
        method="users.search",
        values={},
        raw=None,
        error={"error_code": 6, "error_msg": "Rate limit"},  # Обычно ВК возвращает и код, и сообщение
        vk=client  # Ссылка на инстанс вашего тестируемого клиента
    )

    results = client.search_opposite(1, 10, 18, 25)
    assert results == []


def test_find_partners_calculates_range_explicit(client, mock_vk_session):
    """
    Проверяем корректность преобразования сырых данных API
    в параметры поиска.
    (пол, город, вычисленный интервал возраста для поиска)
    """
    # 1. Подменяем получение профиля через мок сессии (как у вас уже настроено)
    mock_vk_session['group_api'].users.get.return_value = [{
        'id': 1,
        'first_name': 'Алексей',
        'last_name': 'Петров',
        'sex': 2,
        'city': {'id': 50, 'title': 'Москва'},
        'bdate': '01.01.2001'
    }]

    search_mock = Mock(return_value=[])

    client.search_opposite = search_mock

    client.find_partners_for_user(source_user_id=1, age_range=(18, 40), count=10)

    assert search_mock.called
    kwargs = search_mock.call_args.kwargs

    assert kwargs['target_sex'] == 1
    assert kwargs['city_id'] == 50
    assert kwargs['age_from'] == 20
    assert kwargs['age_to'] == 30


def test_find_partners_no_age_in_profile(client, mock_vk_session):
    """
    Проверяем корректность интервал возраста для поиска
    если возраст пользователя не указан.
    """
    mock_vk_session['group_api'].users.get.return_value = [{
        'id': 2,
        'first_name': 'Борис',
        'last_name': 'Сидоров',
        'sex': 2,
        'city': {'id': 60, 'title': 'СПб'},
        # bdate отсутствует – возраст не вычисляется
    }]

    mock_vk_session['search_api'].users.search.return_value = {'items': []}

    client.find_partners_for_user(source_user_id=2, age_range=(18, 40))

    args, kwargs = mock_vk_session['search_api'].users.search.call_args
    # Проверяем правильные имена параметров
    assert kwargs['age_from'] == 18
    assert kwargs['age_to'] == 40


def test_get_top_3_photos_aggregation_and_sorting(client, mock_vk_session):
    """
    Проверяет сбор фотографий из профиля и альбомов, а также их сортировку по лайкам.

    Тест имитирует ситуацию, когда у пользователя есть фото на аватарке
    и фотографии в системном альбоме. Ожидается, что метод соберет все снимки
    в один список, отсортирует по убыванию популярности и вернет топ-3.
    """
    user_id = 100

    # Фото из профиля (аватарки)
    mock_vk_session['search_api'].photos.getProfile.return_value = {
        'items': [
            {'id': 1, 'likes': {'count': 5}, 'sizes': [{'url': 'u1.jpg', 'width': 100, 'height': 100}]},
            {'id': 2, 'likes': {'count': 15}, 'sizes': [{'url': 'u2.jpg', 'width': 200, 'height': 200}]}
        ]
    }

    # Системные альбомы
    mock_vk_session['search_api'].photos.getAlbums.return_value = {
        'items': [{'id': 999, 'is_system': True}]
    }

    # Фото из альбома со страницы
    mock_vk_session['search_api'].photos.get.return_value = {
        'items': [
            {'id': 3, 'likes': {'count': 25}, 'sizes': [{'url': 'a1.jpg', 'width': 300, 'height': 300}]},
            {'id': 4, 'likes': {'count': 2}, 'sizes': [{'url': 'a2.jpg', 'width': 50, 'height': 50}]}
        ]
    }

    result = client.get_top_3_photos(user_id)

    # Ожидаем топ-3 по лайкам: id 3 (25), id 2 (15), id 1 (5)
    assert len(result) == 3
    assert [item['id'] for item in result] == [3, 2, 1]



def test_get_top_3_photos_handles_empty_albums(client, mock_vk_session):
    """
    Проверяет поведение метода, когда у пользователя полностью отсутствуют фотографии.

    Сценарий: профиль пуст, альбомов нет.
    Ожидаемый результат: метод должен вернуть пустой список []
    без возникновения ошибок или исключений.
    """
    user_id = 200
    mock_vk_session['search_api'].photos.getProfile.return_value = {'items': []}
    mock_vk_session['search_api'].photos.getAlbums.return_value = {'items': []}  # Альбомов нет вообще

    result = client.get_top_3_photos(user_id)
    assert result == []


def test_get_top_3_photos_skips_photos_without_sizes(client, mock_vk_session):
    """
    Проверяет фильтрацию фотографий без доступных размеров ('sizes').

    Даже если у снимка много лайков, он должен быть исключен из топа,
    если в ответе API отсутствует информация о его URL или разрешении.
    """
    user_id = 300
    mock_vk_session['search_api'].photos.getProfile.return_value = {
        'items': [
            {'id': 10, 'likes': {'count': 100}, 'sizes': []},  # Пропускается
            {'id': 11, 'likes': {'count': 50}, 'sizes': [{'url': 'valid.jpg', 'width': 100, 'height': 100}]}
        ]
    }
    mock_vk_session['search_api'].photos.getAlbums.return_value = {'items': []}

    result = client.get_top_3_photos(user_id)
    assert len(result) == 1
    assert result[0]['id'] == 11
