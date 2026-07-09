import requests
from config import USER_TOKEN, VK_API_VERSION
import datetime

class VKClient(object):
    def __init__(self, token=USER_TOKEN, version=VK_API_VERSION):
        self.token = token
        self.version = version
        self.base_url = "https://api.vk.com/method/"

    def _get(self, method, params):
        params['access_token'] = self.token
        params['v'] = self.version

        url = f"{self.base_url}{method}"

        response = requests.get(url, params=params)

        data = response.json()

        return data.get('response')

    def get_user_info(self, user_id):
        params = {
            'user_ids': user_id,
            'fields': 'bdate,sex,city,domain'
        }

        data = self._get("users.get", params)

        if not data or len(data) == 0:
            print(f"Пользователь с ID {user_id} не найден.")
            return None

        user_data = data[0]

        result = {
            'first_name': user_data.get('first_name'),
            'last_name': user_data.get('last_name'),
            'domain': user_data.get('domain'),
            'sex': user_data.get('sex'),
            'city': user_data.get('city', {}).get('id') if user_data.get('city') else None,
            'age': self._calculate_age(user_data.get('bdate'))
        }

        return result

    def _calculate_age(self, bdate):
        if not bdate:
            return None

        parts = bdate.split('.')

        if len(parts) < 3:
            return None

        try:
            day, month, year = map(int, parts)
        except ValueError:
            return None

        today = datetime.date.today()
        age = today.year - year

        if (today.month, today.day) < (month, day):
            age -= 1

        return age

    def search_users(self, city_id, age, sex, count=50, offset=0):

        age_from = age - 5
        age_to = age + 5

        if age_from < 18:
            age_from = 18
        if age_to > 100:
            age_to = 100

        params = {
            'city': city_id,
            'sex': sex,
            'age_from': age_from,
            'age_to': age_to,
            'has_photo': 1,
            'count': count,
            'offset': offset,
            'fields': 'domain,photo_id'
        }

        data = self._get('users.search', params)

        if data and 'items' in data:
            return data['items']
        else:
            return []

    def get_user_photos(self, user_id, count=50):
        params = {
            'owner_id': user_id,
            'album_id': 'profile',
            'extended': 1,
            'count': count
        }

        data = self._get('photos.get', params)

        if not data or 'items' not in data:
            return []

        sorted_photos = sorted(
            data['items'],
            key=lambda x: x.get('likes', {}).get('count', 0),
            reverse=True
        )

        top_photos = []
        for photo in sorted_photos[:3]:
            attachment = f"photo{photo['owner_id']}_{photo['id']}"
            top_photos.append({
                'attachment': attachment,
                'likes': photo.get('likes', {}).get('count', 0)
            })

        return top_photos



