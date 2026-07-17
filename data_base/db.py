import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
from dotenv import load_dotenv
import logging
from logging_config import setup_logging



load_dotenv()

setup_logging(log_file="db.log", log_level=logging.INFO)

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных PostgreSQL"""

    def __init__(self):
        self.connection = None
        self.cursor = None
        self.connect()
        self.create_tables()

    def connect(self):
        """Установка соединения с БД"""
        try:
            # В РАБОЧЕЙ ВЕРСИИ УДАЛИТЬ ЛИШНЕЕ
            self.connection = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', 5432),
                dbname=os.getenv('DB_NAME', 'VKinder'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'postgres')
            )
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            logger.info("Подключение к БД установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            raise

    def create_tables(self):
        """Создание таблиц"""
        try:
            self.create_tables_programmatically()
        except Exception as e:
            logger.error(f"Ошибка создания таблиц: {e}")
            self.connection.rollback()

    def create_tables_programmatically(self):
        """Создание таблиц"""
        try:
            # БЛОК ОБНОВЛЕНИЯ ТАБЛИЦ, ПРИ РЕАЛЬНОЙ РАБОТЕ УДАЛИТЬ
            self.cursor.execute('DROP TABLE IF EXISTS favorites CASCADE')
            self.cursor.execute('DROP TABLE IF EXISTS blacklist CASCADE')
            self.cursor.execute('DROP TABLE IF EXISTS viewed_users CASCADE')
            self.cursor.execute('DROP TABLE IF EXISTS users CASCADE')
            self.cursor.execute('DROP TABLE IF EXISTS photo_likes CASCADE')
            self.cursor.execute('DROP TABLE IF EXISTS interests CASCADE')
            # Таблица пользователей
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    sex SMALLINT,
                    age INTEGER,
                    city_id INTEGER,
                    city_title VARCHAR(100),
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица избранных
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS favorites (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    favorite_id BIGINT,
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    profile_url VARCHAR(255),
                    photo1 VARCHAR(100),
                    photo2 VARCHAR(100),
                    photo3 VARCHAR(100),
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, favorite_id)
                )
            ''')

            # Таблица черного списка
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS blacklist (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    blacklisted_id BIGINT,
                    reason VARCHAR(255),
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, blacklisted_id)
                )
            ''')

            # Таблица просмотренных
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS viewed_users (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    viewed_id BIGINT,
                    viewed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, viewed_id)
                )
            ''')

            # Таблица лайков (доп)
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS photo_likes (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    photo_owner_id BIGINT NOT NULL,
                    photo_id VARCHAR(50) NOT NULL,
                    liked_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, photo_owner_id, photo_id)
                )
            ''')

            # Таблица интересов (доп)
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS interests (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    interest_type VARCHAR(50),
                    interest_id VARCHAR(100),
                    interest_name VARCHAR(255),
                    weight INTEGER DEFAULT 1,
                    UNIQUE(user_id, interest_type, interest_id)
                )
            ''')

            # Внешние ключи
            # favorites
            self.cursor.execute('''
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.table_constraints
                        WHERE constraint_name = 'fk_favorites_user') THEN
                        ALTER TABLE favorites
                        ADD CONSTRAINT fk_favorites_user
                        FOREIGN KEY (user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE;
                    END IF;
                END $$;
            ''')

            # blacklist
            self.cursor.execute('''
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.table_constraints
                        WHERE constraint_name = 'fk_blacklist_user') THEN
                        ALTER TABLE blacklist
                        ADD CONSTRAINT fk_blacklist_user
                        FOREIGN KEY (user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE;
                    END IF;
                END $$;
            ''')

            # viewed_users
            self.cursor.execute('''
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.table_constraints
                        WHERE constraint_name = 'fk_viewed_user') THEN
                        ALTER TABLE viewed_users
                        ADD CONSTRAINT fk_viewed_user
                        FOREIGN KEY (user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE;
                    END IF;
                END $$;
            ''')

            # photo_likes
            self.cursor.execute('''
             DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.table_constraints
                        WHERE constraint_name = 'fk_photo_likes_user'
                    ) THEN
                        ALTER TABLE photo_likes
                        ADD CONSTRAINT fk_photo_likes_user
                        FOREIGN KEY (user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE;
                    END IF;
                END $$;
             ''')

            # interests
            self.cursor.execute('''
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.table_constraints
                        WHERE constraint_name = 'fk_interests_user'
                    ) THEN
                        ALTER TABLE interests
                        ADD CONSTRAINT fk_interests_user
                        FOREIGN KEY (user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE;
                    END IF;
                END $$;
             ''')

            # Индексы
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_favorites_user_id
                ON favorites(user_id)
            ''')

            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_blacklist_user_id
                ON blacklist(user_id)
            ''')

            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_viewed_user_id
                ON viewed_users(user_id)
            ''')

            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_photo_likes_user
                ON photo_likes(user_id)
            ''')

            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_interests_user
                ON interests(user_id)
            ''')

            self.connection.commit()
            logger.info("Таблицы созданы успешно")

        except Exception as e:
            logger.error(f"Ошибка создания таблиц: {e}")
            self.connection.rollback()
            raise

    def add_user(self, user_data):
        """Добавление или обновление пользователя"""
        try:
            logger.debug(f"Добавление пользователя: {user_data['user_id']}")
            self.cursor.execute('''
                INSERT INTO users (user_id, first_name, last_name, sex,
                age, city_id, city_title)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    sex = EXCLUDED.sex,
                    age = EXCLUDED.age,
                    city_id = EXCLUDED.city_id,
                    city_title = EXCLUDED.city_title
            ''', (
                user_data['user_id'],
                user_data.get('first_name', ''),
                user_data.get('last_name', ''),
                user_data.get('sex', 0),
                user_data.get('age'),
                user_data.get('city_id'),
                user_data.get('city_title', '')
            ))
            self.connection.commit()
            logger.info(f"Пользователь {user_data['user_id']} добавлен/обновлен")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления пользователя: {e}")
            self.connection.rollback()
            return False

    def add_favorite(self, user_id, candidate_data, photos):
        """Добавление пользователя в избранное"""
        try:
            logger.debug(f"Добавление в избранное: user={user_id}, "
                         f"candidate={candidate_data['id']}")
            formatted_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute('''
                INSERT INTO favorites
                (user_id, favorite_id, first_name, last_name,
                profile_url, photo1, photo2, photo3, added_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, favorite_id) DO NOTHING
            ''', (
                user_id,
                candidate_data['id'],
                candidate_data.get('first_name', ''),
                candidate_data.get('last_name', ''),
                f"https://vk.com/id{candidate_data['id']}",
                photos[0] if len(photos) > 0 else None,
                photos[1] if len(photos) > 1 else None,
                photos[2] if len(photos) > 2 else None,
                formatted_date
            ))
            self.connection.commit()
            logger.info(f"Пользователь {candidate_data['id']} "
                        f"добавлен в избранное для {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления в избранное: {e}")
            self.connection.rollback()
            return False

    def get_favorites(self, user_id):
        """Получение списка избранных"""
        try:
            logger.debug(f"Получение избранных для пользователя: {user_id}")
            self.cursor.execute('''
                SELECT favorite_id, first_name, last_name, profile_url,
                photo1, photo2, photo3, added_date
                FROM favorites
                WHERE user_id = %s
                ORDER BY added_date DESC
            ''', (user_id,))
            result = self.cursor.fetchall()
            logger.info(f"Получено избранных: {len(result)} для пользователя {user_id}")
            return result
        except Exception as e:
            logger.error(f"Ошибка получения избранных: {e}")
            return []

    def is_favorite(self, user_id, candidate_id):
        """Есть ли в избранном"""
        self.cursor.execute('''
            SELECT COUNT(*) > 0 as is_favorite
            FROM favorites
            WHERE user_id = %s AND favorite_id = %s
        ''', (user_id, candidate_id))
        result = self.cursor.fetchone()
        is_fav = result['is_favorite'] if result else False
        logger.debug(f"Проверка избранного: user={user_id}, "
                     f"candidate={candidate_id}, result={is_fav}")
        return is_fav


    def add_to_blacklist(self, user_id, blacklisted_id, reason=None):
        """Добавление пользователя в черный список"""
        try:
            logger.debug(f"Добавление в черный список: user={user_id}, "
                         f"blacklisted={blacklisted_id}")
            formatted_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute('''
                INSERT INTO blacklist (user_id, blacklisted_id,
                reason, added_date)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, blacklisted_id) DO NOTHING
            ''', (user_id, blacklisted_id, reason, formatted_date))
            self.connection.commit()
            logger.info(f"Пользователь {blacklisted_id} добавлен в "
                        f"черный список для {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления в черный список: {e}")
            self.connection.rollback()
            return False

    def get_blacklist(self, user_id):
        """Получение черного списка"""
        try:
            logger.debug(f"Получение черного списка для пользователя: {user_id}")
            self.cursor.execute('''
                SELECT blacklisted_id, reason, added_date
                FROM blacklist
                WHERE user_id = %s
                ORDER BY added_date DESC
            ''', (user_id,))
            result = self.cursor.fetchall()
            logger.info(f"Получено в черном списке: {len(result)} для пользователя {user_id}")
            return result
        except Exception as e:
            logger.error(f"Ошибка получения черного списка: {e}")
            return []

    def is_blacklisted(self, user_id, candidate_id):
        self.cursor.execute('''
            SELECT COUNT(*) > 0 as is_blacklisted
            FROM blacklist
            WHERE user_id = %s AND blacklisted_id = %s
        ''', (user_id, candidate_id))
        result = self.cursor.fetchone()
        is_bl = result['is_blacklisted'] if result else False
        logger.debug(f"Проверка черного списка: user={user_id},"
                     f"candidate={candidate_id}, result={is_bl}")
        return is_bl

    def add_viewed_user(self, user_id, viewed_id):
        """Добавление просмотренного пользователя"""
        try:
            logger.debug(f"Добавление просмотренного: user={user_id}, viewed={viewed_id}")
            formatted_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute('''
                INSERT INTO viewed_users (user_id, viewed_id, viewed_date)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, viewed_id) DO NOTHING
            ''', (user_id, viewed_id, formatted_date))
            self.connection.commit()
            logger.info(f"Пользователь {viewed_id} добавлен в просмотренные для {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления просмотренного: {e}")
            self.connection.rollback()
            return False

    def get_viewed_users(self, user_id):
        """Получение списка просмотренных"""
        try:
            logger.debug(f"Получение просмотренных для пользователя: {user_id}")
            self.cursor.execute('''
                    SELECT viewed_id
                    FROM viewed_users
                    WHERE user_id = %s
                    ORDER BY viewed_date DESC
                ''', (user_id,))
            result = [row['viewed_id'] for row in self.cursor.fetchall()]
            logger.info(f"Получено просмотренных: {len(result)} для пользователя {user_id}")
            return result
        except Exception as e:
            logger.error(f"Ошибка получения просмотренных: {e}")
            return []

    def close(self):
        """Закрытие соединения с БД"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            logger.error("Соединение с БД закрыто")
