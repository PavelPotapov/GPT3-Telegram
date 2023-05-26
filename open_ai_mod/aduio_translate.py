from dotenv import load_dotenv
import openai
import os

load_dotenv()
openai.api_key = os.getenv('CHATGPT_API_KEY')

def create_text_from_audio(filepath):
    audio_file = open(filepath, "rb")
    transcription = openai.Audio.transcribe("whisper-1", audio_file)
    return transcription["text"]