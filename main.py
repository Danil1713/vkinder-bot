import sys
import logging
from bot.vk_bot import start_bot
from logging_config import setup_logging

# Настраиваем логирование
setup_logging(log_file="vkinder.log", log_level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        logger.info("=" * 50)
        logger.info("ЗАПУСК БОТА VKINDER")
        logger.info("=" * 50)
        start_bot()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)