"""
Модуль класса конвертера аудио в текст
"""

import json
import logging
import os
import subprocess
from typing import Any
from urllib.parse import urlencode

import aiohttp
import speech_recognition as sr

log = logging.getLogger('speech_to_text_async')


class Converter:
    """Класс конвертера аудио в текст"""

    def __init__(self, path_to_file: str, language: str = 'ru-RU'):
        self.language = language
        self.path_to_file = path_to_file
        self.wav_file = path_to_file.replace('.ogg', '.wav')
        subprocess.run(['ffmpeg', '-v', 'quiet', '-i', self.path_to_file, self.wav_file], check=True)


    def prepare_audio(self) -> sr.AudioData:
        """
        Метод подготовки аудио к дальнейшему распознаванию

        :return: AudioData
        """
        log.info('Start prepared audio')
        recognizer = sr.Recognizer()
        with sr.AudioFile(self.wav_file) as source:
            audio = recognizer.record(source)
            recognizer.adjust_for_ambient_noise(source)
        return audio

    @staticmethod
    async def recognize_google(
            session: aiohttp.ClientSession,
            audio_data: sr.AudioData,
            key: str | None = None,
            language: str = 'ru-RU',
            pfilter: int = 0,
            show_all: bool = False,
    ) -> list[Any] | tuple[Any, Any] | Any:
        """
        Асинхронная адаптация метода распознавания recognize_google с использованием Google Speech Recognition API

        :param session: Экземпляр ClientSession aiohttp

        :param audio_data: Экземпляр AudioData, представляющий моно аудио данные для распознавания

        :param key: API-Key для запроса к Google Speech Recognition API v2. Взят из библиотеки speech_recognition. Не
        гарантируется что будет работать всегда. Желательно использовать собственный API-Key. Как его получить описано
        на: `API Keys <http://www.chromium.org/developers/how-tos/api-keys>` page at the Chromium Developers site.
        In the Google Developers Console, Google Speech Recognition is listed as "Speech API".

        :param language: язык распознавания. Перечень поддерживаемых языков можно найти на `StackOverflow answer
        <http://stackoverflow.com/a/14302134>`

        :param pfilter: Уровень фильтрации ненормативной лексики. 0 -нет фильтрации, 1 - показывается первая буква,
        остальные буквы заменяются звездочками.

        :param show_all: флаг, задающий что возвращать в ответе. По умолчанию - False.

        :return: Возвращает наиболее вероятную транскрипцию, если значение `show_all` равно False (по умолчанию).
        В противном случае возвращает необработанный ответ API в виде словаря JSON.
        Вызывает исключение `speech_recognition.UnknownValueError`, если речь неразборчива.
        """
        log.info('Start recognize audio')
        assert isinstance(audio_data, sr.AudioData), '``audio_data`` must be audio data'
        assert key is None or isinstance(key, str), '``key`` must be ``None`` or a string'
        assert isinstance(language, str), '``language`` must be a string'

        flac_data = audio_data.get_flac_data(
            convert_rate=None if audio_data.sample_rate >= 8000 else 8000,  # audio samples must be at least 8 kHz
            convert_width=2  # audio samples must be 16-bit
        )
        if key is None:
            key = 'AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw'
        url_params = urlencode({'client': 'chromium', 'lang': language, 'key': key, 'pFilter': pfilter})
        url = f'https://www.google.com/speech-api/v2/recognize?{url_params}'
        async with session.post(
                url,
                data=flac_data,
                headers={'Content-Type': f'audio/x-flac; rate={audio_data.sample_rate}'},
        ) as response:
            response_text = await response.text(encoding='utf-8')
            log.info('Get response from Google Speech Recognition API: %s, status: %s',
                     response_text.replace('\n', ' '), response.status)

        # ignore any blank blocks
        actual_result = []
        for line in response_text.split('\n'):
            if not line:
                continue
            result = json.loads(line)['result']
            if len(result) != 0:
                actual_result = result[0]
                break

        # return results
        if show_all:
            return actual_result
        if not isinstance(actual_result, dict) or len(actual_result.get('alternative', [])) == 0:
            raise sr.UnknownValueError()
        if 'confidence' in actual_result['alternative']:
            # return alternative with the highest confidence score
            best_hypothesis = max(actual_result['alternative'], key=lambda alternative: alternative['confidence'])
        else:
            # when there is no confidence available, we arbitrarily choose the first hypothesis.
            best_hypothesis = actual_result['alternative'][0]
        if 'transcript' not in best_hypothesis:
            raise sr.UnknownValueError()
        log.info('Get result text: %s', best_hypothesis['transcript'])
        return best_hypothesis['transcript']

    def __del__(self):
        os.remove(self.wav_file)
        log.info('Remove file: %s', self.wav_file)
