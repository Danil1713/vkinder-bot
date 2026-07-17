import logging
import vk_api

from config import Config

logger = logging.getLogger(__name__)


class VK_client:

    def __init__(self):

        # Для работы от имени группы/бота
        self.group_session = vk_api.VkApi(token=Config.group_token)
        self.group_api = self.group_session.get_api()

        # Для поиска людей
        self.search_session = vk_api.VkApi(token=Config.access_token)
        self.search_api = self.search_session.get_api()

        # Актуальная версия API
        self.version = Config.version
        logger.info("VK_client инициализирован")

    def get_users_info(self, user_id: int) -> dict | None:
        """
        Получение данных пользователя
        """
        try:
            response = self.group_api.users.get(
                user_ids=user_id,
                name_case='nom',
                fields='bdate,city,sex,relation,domain',
                v=self.version
            )

            if not response or response[0].get('is_closed'):
                logger.warning(f"Пользователь {user_id} не найден")
                return None

            data = response[0]
            logger.debug(f"Получены данные пользователя {user_id}: {data}")
            city_data = data.get('city')
            bdate_str = data.get('bdate')

            result = {
                'user_id': data['id'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'sex': data.get('sex'),
                'city_id': city_data.get('id') if city_data else None,
                'city_title': city_data.get('title') if city_data else None,
                'domain': data.get('domain'),
            }

            if bdate_str and '.' in bdate_str:
                parts = bdate_str.split('.')
                if len(parts) == 3:
                    from datetime import datetime
                    birth_year = int(parts[2])
                    current_year = datetime.now().year
                    result['age'] = current_year - birth_year
            else:
                result['age'] = None

            return result
        except vk_api.exceptions.ApiError as e:
            logger.error(f"[get_user_profile] Ошибка API для {user_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Неизвестная ошибка в get_users_info: {e}")
            return None

    def search_opposite(
            self,
            target_sex: int,
            city_id: int,
            age_from: int,
            age_to: int,
            count: int = 100
    ) -> list[dict]:
        """
        Ищет пользователей по заданным критериям.
        (возраст, пол, город)
        """
        try:
            response = self.search_api.users.search(
                sort=0,
                offset=0,
                count=min(count, 100),
                sex=target_sex,
                city=city_id,
                age_from=age_from,
                age_to=age_to,
                status=6,
                has_photo=1,
                is_closed=False,
                fields='is_closed,bdate,domain',
                v=self.version
            )

            items = response.get('items', [])
            results = []

            from datetime import datetime
            current_year = datetime.now().year

            for user in items:
                if not user.get('is_closed'):

                    bdate_str = user.get('bdate')

                    # Проверяем наличие даты и того,
                    # что в ней указан ГОД (3 части)
                    if bdate_str and len(bdate_str.split('.')) == 3:
                        parts = bdate_str.split('.')
                        birth_year = int(parts[2])
                        calculated_age = current_year - birth_year
                    else:
                        calculated_age = None

                    results.append({
                        'id': user['id'],
                        'first_name': user['first_name'],
                        'last_name': user['last_name'],
                        'age': calculated_age,
                        'domain': user.get('domain'),
                    })

            return results

        except vk_api.exceptions.ApiError as e:
            logger.error(f"[search_opposite] Ошибка API: {e}")
            return []

    def find_partners_for_user(
            self,
            source_user_id: int,
            age_range: tuple[int, int] = (18, 50),
            count: int = 50,
            blacklist: list = None,
            viewed_users: list = None
    ) -> list[dict]:
        """
        Главная функция: берет ID пользователя, определяет его параметры
        и ищет ему пару с противоположным полом.
        """
        profile = self.get_users_info(source_user_id)

        if not profile:
            logger.warning("Не удалось определить профиль-источник.")
            return []

        base_min_age, base_max_age = age_range

        # Если мы смогли вычислить возраст пользователя,
        # сузим диапазон вокруг него
        if profile['age']:
            range_center = profile['age']
            delta = 5
            min_age = max(range_center - delta, 18)
            max_age = min(range_center + delta, 99)
        else:
            min_age = base_min_age
            max_age = base_max_age

        opposite_sex = 1 if profile['sex'] == 2 else 2

        candidates = self.search_opposite(
            target_sex=opposite_sex,
            city_id=profile.get('city_id'),
            age_from=min_age,
            age_to=max_age,
            count=count
        )

        logger.info(f"Ищем пользователей пола {profile['sex']} "
                    f"в городе {profile['city_id']} "
                    f"возрастом от {min_age} до {max_age}")

        # Исключение пользователей из черного списка и просмотренных
        if blacklist:
            blacklist_set = set(blacklist)
            candidates = [c for c in candidates
                          if c['id'] not in blacklist_set]

        if viewed_users:
            viewed_set = set(viewed_users)
            candidates = [c for c in candidates if c['id'] not in viewed_set]

        return candidates

    def get_top_3_photos(self, user_id: int) -> list[dict]:
        """
        Собирает топ-3 фото из профиля, аватара и других альбомов.
        Корректно обрабатывает отсутствие альбомов у пользователя.
        """
        all_candidates = []

        try:
            # 1. Получаем аватарки и фото профиля (самый надежный источник)
            profile_photos = self.search_api.photos.getProfile(
                owner_id=user_id,
                count=100,
                photo_sizes=1,
                v=self.version
            )

            for item in profile_photos.get('items', []):
                sizes = item.get('sizes', [])
                if sizes:
                    best_size = max(
                        sizes,
                        key=lambda s: s['width'] * s['height']
                    )
                    likes = item.get('likes', {}).get('count', 0)
                    owner = item.get('owner_id', user_id)
                    all_candidates.append({
                        'id': item['id'],
                        'attachment': f"photo{owner}_{item['id']}",
                        'likes': likes
                    })

            # 2. Пытаемся получить фото из стандартного альбома
            # "Фото со страницы"
            # (вдруг там есть другие кадры, которых нет в профиле)
            try:
                wall_albums = self.search_api.photos.getAlbums(
                    owner_id=user_id,
                    need_system=1,
                    v=self.version
                )
                system_album_ids = [alb['id']
                                    for alb in wall_albums.get('items', [])
                                    if alb.get('is_system')]

                for aid in system_album_ids[:2]:
                    sys_photos = self.search_api.photos.get(
                        owner_id=user_id,
                        album_id=aid,
                        count=50,
                        photo_sizes=1,
                        v=self.version
                    )
                    for item in sys_photos.get('items', []):
                        sizes = item.get('sizes', [])
                        if sizes:
                            best_size = max(
                                sizes,
                                key=lambda s: s['width'] * s['height']
                            )
                            likes = item.get('likes', {}).get('count', 0)
                            owner = item.get('owner_id', user_id)
                            all_candidates.append({
                                'id': item['id'],
                                'attachment': f"photo{owner}_{item['id']}",
                                'likes': likes
                            })

            except vk_api.exceptions.ApiError:
                pass  # Если альбомов нет - просто идем дальше

            # 3. Сортируем всё найденное по лайкам
            sorted_photos = sorted(
                all_candidates,
                key=lambda x: x['likes'],
                reverse=True
            )

            return sorted_photos[:3]

        except vk_api.exceptions.ApiError as e:
            logger.error(f"[get_top_3_photos] Ошибка API для {user_id}: {e}")
            return []
