from pprint import pprint
import requests
from config import Config


class VK:
    """
    Проверка работоспособности access_token
    """
    def __init__(self, access_token, user_id, version='5.199'):
        self.token = Config.access_token
        self.id = Config.user_id
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}

    def users_info(self):
        url = 'https://api.vk.com/method/users.get'
        params = {'user_ids': self.id}
        response = requests.get(url, params={**self.params, **params})
        return response.json()


access_token = 'access_token'
user_id = 'user_id'
vk = VK(access_token, user_id)

pprint(vk.users_info())
