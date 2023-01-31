"""
Модуль приложения асинхронного телеграм-бота для преобразования голосовых сообщений в текстовые.
"""
import logging
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


@app.after_server_stop
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
    log.info('Handled command /start')
    welcome_mess = 'Привет! Отправляй голосовое, я расшифрую!'
    await bot.send_message(message.chat.id, welcome_mess)
    log.info('Quit from handler start command')


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
    log.info('Handled content types %s', message.content_type)
    file_id = None
    match message.content_type:
        case 'voice':
            file_id = message.voice.file_id
        case 'audio':
            file_id = message.audio.file_id
        case 'video_note':
            file_id = message.video_note.file_id
    log.info('File_id = %s', file_id)
    if file_id is not None:
        file_info = await bot.get_file(file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        file_name = str(message.message_id) + '.ogg'

        with open(file_name, 'wb') as new_file:
            new_file.write(downloaded_file)
        converter = Converter(file_name)
        os.remove(file_name)
        audio = converter.prepare_audio()
        log.info('Prepared audio for recognize')
        try:
            message_text = await converter.recognize_google(
                session=app.ctx.client_session, audio_data=audio, language='ru-RU'
            )
            log.info('Get message from audio: %s', message_text)
        except sr.UnknownValueError as err:
            message_text = 'Сообщение не может быть распознано, так как речь не разборчива'
            log.error('Error during recognize audio: %s', err, exc_info=True)
        except aiohttp.ClientError as err:
            message_text = 'Сообщение не может быть распознано. Попробуйте еще раз через несколько секунд'
            log.error('Error during recognize audio: %s', err, exc_info=True)
        finally:
            del converter

        await bot.send_message(message.chat.id, message_text, reply_to_message_id=message.message_id)
        log.info('Quit from handler content types %s', message.content_type)


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
    log.info('Get web-hook request: %s', json_string)
    update = telebot.types.Update.de_json(json_string)
    request.app.add_task(bot.process_new_updates([update]))
    log.info('Added background task with update: %s', update)
    return text('!')


if __name__ == '__main__':
    log = logging.getLogger('speech_to_text_async')
    log.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    sh.setFormatter(formatter)
    log.addHandler(sh)

    app.run(host=settings.APP.HOST, port=int(os.environ.get('PORT', 5000)), workers=settings.APP.workers,
            debug=settings.DEBUG, access_log=True)
