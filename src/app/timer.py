import time
from dataclasses import dataclass, field
from typing import Callable, ClassVar, Dict, Optional


class TimerError(Exception):
    """Пользовательское исключение, используемое для сообщения об ошибках при использовании класса Timer"""


@dataclass
class Timer:
    timers: ClassVar[Dict[str, float]] = dict()
    name: Optional[str] = None
    text: str = 'Вычисление заняло {:0.4f} секунд'
    logger: Optional[Callable[[str], None]] = print
    _start_time: Optional[float] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Добавить таймер к dict таймеров после инициализации"""
        if self.name is not None:
            self.timers.setdefault(self.name, 0)

    def start(self) -> None:
        """Начать новый таймер"""
        if self._start_time is not None:
            raise TimerError('Таймер работает. Используйте .stop(), чтобы остановить его')

        self._start_time = time.perf_counter()

    def stop(self) -> float:
        """Остановить таймер и сообщить истекшее время"""
        if self._start_time is None:
            raise TimerError('Таймер не работает. Используйте .start(), чтобы запустить его')

        # Рассчитать прошедшее время
        elapsed_time = time.perf_counter() - self._start_time
        self._start_time = None

        # Сообщить о прошедшем времени
        if self.logger:
            self.logger(self.text.format(elapsed_time))
        if self.name:
            self.timers[self.name] += elapsed_time

        return elapsed_time
