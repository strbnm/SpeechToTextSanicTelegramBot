import subprocess

import speech_recognition as sr
import os

from timer import Timer


class Converter:

    def __init__(self, path_to_file: str, language: str = "ru-RU"):
        self.timer = Timer('recognizer_timer')
        self.language = language
        self.path_to_file = path_to_file
        self.wav_file = path_to_file.replace(".ogg", ".wav")
        self.timer.start()
        subprocess.run(['ffmpeg', '-v', 'quiet', '-i', self.path_to_file, self.wav_file])
        self.timer.stop()

    def audio_to_text(self) -> str:
        r = sr.Recognizer()

        with sr.AudioFile(self.wav_file) as source:
            self.timer.start()
            audio = r.record(source)
            self.timer.stop()
            self.timer.start()
            r.adjust_for_ambient_noise(source)
            self.timer.stop()
        self.timer.start()
        result = r.recognize_google(audio, language=self.language)
        self.timer.stop()

        return result

    def __del__(self):
        os.remove(self.wav_file)
