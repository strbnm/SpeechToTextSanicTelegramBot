from pydantic import BaseSettings, Field


class SecuritySettings(BaseSettings):
    SECRET_KEY: str = Field(..., description='Секретный ключ приложения')
    TOKEN: str = Field(..., description='Токен телеграм-бота')

    class Config:
        env_prefix = 'SECURITY_'
        env_file = '.env'


class AppSettings(BaseSettings):
    HOST: str = Field('0.0.0.0', description='Адрес хоста')
    PORT: int = Field(8088, description='Номер сетевого порта')
    workers: int = 4

    class Config:
        env_prefix = 'APP_'
        env_file = '.env'


class CommonSettings(BaseSettings):
    SANIC_APP_NAME: str = 'MySpeachToTextBot'
    DEBUG: bool = Field(False, description='Флаг режима отладки')
    TESTING: bool = Field(False, description='Флаг режима тестирования')
    LOG_LEVEL: str = Field('DEBUG', description='Уровень сообщений лога')
    SECURITY: SecuritySettings = SecuritySettings()
    APP: AppSettings = AppSettings()
