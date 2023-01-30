"""
Модуль приложения асинхронного телеграм-бота для преобразования голосовых сообщений в текстовые.
"""

import os

import aiohttp
import speech_recognition as sr
import telebot
from sanic import Sanic, Blueprint, Request, text
from telebot import types
from telebot.async_telebot import AsyncTeleBot

from convert import Converter
from settings.config import settings

app = Sanic(settings.SANIC_APP_NAME)


@app.before_server_start
async def setup_client_session(app, _):
    app.ctx.client_session = aiohttp.ClientSession()


@app.before_server_stop
async def close_client_session(app, _):
    await app.ctx.client_session.close()


TOKEN = settings.SECURITY.TOKEN
bot = AsyncTeleBot(TOKEN)

v1 = Blueprint('speach_to_text')
app.blueprint(v1)


@bot.message_handler(commands=['start'])
async def start(message: types.Message):
    """
    Метод обработчика команды /start

    :param message: объект сообщения Telegram
    :return: None
    """

    welcome_mess = 'Привет! Отправляй голосовое, я расшифрую!'
    await bot.send_message(message.chat.id, welcome_mess)


@bot.message_handler(content_types=['voice', 'video_note', 'audio'])
async def get_audio_messages(message: types.Message):
    """
    Метод обработчика сообщений с контентом типа голосовое сообщение, аудио или видеосообщение.

    Получает аудио или видео файл с голосовым сообщением, осуществляет его преобразование к виду, необходимому
    для его распознавания с помощью Google Speech Recognition API v2 и отправляет распознанный текст в
    ответном сообщении Telegram.

    :param message: Объект сообщения Telegram
    :return: None
    """
    file_id = None
    match message.content_type:
        case 'voice':
            file_id = message.voice.file_id
        case 'audio':
            file_id = message.audio.file_id
        case 'video_note':
            file_id = message.video_note.file_id
    if file_id is not None:
        file_info = await bot.get_file(file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        file_name = str(message.message_id) + '.ogg'

        with open(file_name, 'wb') as new_file:
            new_file.write(downloaded_file)
        converter = Converter(file_name)
        os.remove(file_name)
        audio = converter.prepare_audio()
        try:
            message_text = await converter.recognize_google(
                session=app.ctx.client_session, audio_data=audio, language='ru-RU'
            )
        except sr.UnknownValueError:
            message_text = 'Сообщение не может быть распознано, так как речь не разборчива'
        except aiohttp.ClientError:
            message_text = 'Сообщение не может быть распознано. Попробуйте еще раз через несколько секунд'
        finally:
            del converter

        await bot.send_message(message.chat.id, message_text, reply_to_message_id=message.message_id)


@v1.post('/')
async def handler_post(request: Request):
    """
    Метод обработчика веб-хук запросов от Telegram

    Осуществляет обработку поступающих веб-хук запросов к боту.
    Поскольку Telegram не отправляет следующий запрос до получения ответа о получении ранее отправленного,
    для исключения поведения, когда несколько голосовых сообщений обрабатываются последовательно, задачи на обработку
    голосовых сообщений добавляются как background task и ответ Telegram возвращается немедленно. Это позволяет
    обрабатывать параллельно несколько голосовых сообщений, отправленных одновременно или с небольшой задержкой между
    сообщениями.

    :param request: Экземпляр запроса
    :return: Экземпляр ответа с текстом '!' в теле ответа
    """
    json_string = request.body.decode(encoding='utf-8')
    update = telebot.types.Update.de_json(json_string)
    request.app.add_task(bot.process_new_updates([update]))
    return text('!')


if __name__ == '__main__':
    app.run(host=settings.APP.HOST, port=int(os.environ.get('PORT', 5000)), workers=settings.APP.workers,
            debug=settings.DEBUG, access_log=True)
