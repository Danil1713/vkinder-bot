import os
from dotenv import load_dotenv


load_dotenv()


class Config:
    """Базовый класс конфигурации."""

    # --- Настройки ВКонтакте ---
    group_token: str = os.getenv('VK_TOKEN')
    access_token: str = os.getenv('SEARCH_TOKEN')
    user_id: int = int(os.getenv('USER_ID'))
    version: str = os.getenv('VK_API_VERSION')

    # --- Настройки Базы Данных PostgreSQL ---
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_PORT: str = os.getenv('DB_PORT', '5432')
    DB_NAME: str = os.getenv('DB_NAME')
    DB_USER: str = os.getenv('DB_USER')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD')



