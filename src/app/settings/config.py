import os

from settings.dev import DevelopmentSettings
from settings.prod import ProductionSettings

runtime_settings = os.environ.get('SETTINGS', 'dev')

runtime_classes = {
    'dev': DevelopmentSettings,
    'prod': ProductionSettings,
}

if runtime_settings not in runtime_classes:
    expected = ', '.join(runtime_classes)
    raise ValueError(
        f'Неверное значение настроек окружения! Ожидаются {expected}, получено {runtime_settings}.'
    )

settings = runtime_classes[runtime_settings]()
