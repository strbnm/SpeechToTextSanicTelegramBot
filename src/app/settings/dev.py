from settings.base import CommonSettings


class DevelopmentSettings(CommonSettings):
    LOG_LEVEL: str = 'INFO'
    TESTING: bool = True
    DEBUG: bool = True
