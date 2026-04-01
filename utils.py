import time
import logging
import functools
from random import uniform


def retry(
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        exceptions: tuple = (Exception,),
        logger=None,
):
    """
    Декоратор для повторения функции в случае возникновения исключения.
    Использует экспоненциальную задержку с добавлением случайного шума (jitter).

    :param max_retries: Максимальное количество повторов (не считая первую попытку).
    :param initial_delay: Задержка перед первым повтором (в секундах).
    :param backoff_factor: Множитель для увеличения задержки.
    :param exceptions: Кортеж исключений, которые нужно обрабатывать.
    :param logger: Экземпляр логгера.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            # Если логгер не передан, используем логгер модуля функции
            log = logger or logging.getLogger(func.__module__)

            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        log.error(
                            f"Операция '{func.__name__}' провалилась после {max_retries} попыток. "
                            f"Последняя ошибка: {e}",
                            extra={"error_code": "RETRY_LIMIT_REACHED", "attempt": retries}
                        )
                        raise  # Пробрасываем исключение после исчерпания попыток

                    # Добавляем небольшой случайный шум, чтобы избежать "штормовых" повторов
                    jitter = uniform(0, delay * 0.3)
                    sleep_time = delay + jitter

                    log.warning(
                        f"Попытка {retries}/{max_retries} для '{func.__name__}' провалилась. "
                        f"Повтор через {sleep_time:.1f} сек... (Ошибка: {e})",
                        extra={"error_code": "RETRYING", "attempt": retries}
                    )
                    time.sleep(sleep_time)
                    delay *= backoff_factor  # Экспоненциальный рост задержки

        return wrapper

    return decorator