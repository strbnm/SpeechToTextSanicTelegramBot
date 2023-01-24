import os

import telebot
from telebot.async_telebot import AsyncTeleBot
from sanic import Sanic, Blueprint, Request, text
from telebot import types

from convert import Converter
from settings.config import settings

app = Sanic(settings.SANIC_APP_NAME)


TOKEN = settings.SECURITY.TOKEN
bot = AsyncTeleBot(TOKEN)

v1 = Blueprint('speach_to_text')
app.blueprint(v1)


@bot.message_handler(commands=['start'])
async def start(message: types.Message):
    welcome_mess = 'Привет! Отправляй голосовое, я расшифрую!'
    await bot.send_message(message.chat.id, welcome_mess)


@bot.message_handler(content_types=['voice', 'video_note', 'audio'])
async def get_audio_messages(message: types.Message):
    match message.content_type:
        case 'voice':
            file_id = message.voice.file_id
        case 'audio':
            file_id = message.audio.file_id
        case 'video_note':
            file_id = message.video_note.file_id
    file_info = await bot.get_file(file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    file_name = str(message.message_id) + '.ogg'

    with open(file_name, 'wb') as new_file:
        new_file.write(downloaded_file)
    converter = Converter(file_name)
    os.remove(file_name)
    message_text = converter.audio_to_text()
    del converter

    await bot.send_message(message.chat.id, message_text, reply_to_message_id=message.message_id)


@v1.post('/')
async def handler_post(request: Request):
    json_string = request.body.decode(encoding='utf-8')
    update = telebot.types.Update.de_json(json_string)
    await bot.process_new_updates([update])
    return text('!')


if __name__ == '__main__':
    app.run(host=settings.APP.HOST, port=int(os.environ.get('PORT', 5000)), workers=settings.APP.workers,
            debug=settings.DEBUG)
