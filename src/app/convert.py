import subprocess

import speech_recognition as sr
import os


class Converter:

    def __init__(self, path_to_file: str, language: str = "ru-RU"):
        self.language = language
        self.path_to_file = path_to_file
        self.wav_file = path_to_file.replace(".ogg", ".wav")
        subprocess.run(['ffmpeg', '-v', 'quiet', '-i', self.path_to_file, self.wav_file])

    def audio_to_text(self) -> str:
        r = sr.Recognizer()

        with sr.AudioFile(self.wav_file) as source:
            audio = r.record(source)
            r.adjust_for_ambient_noise(source)

        return r.recognize_google(audio, language=self.language)

    def __del__(self):
        os.remove(self.wav_file)
