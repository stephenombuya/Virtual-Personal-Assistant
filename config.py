# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

# Speech Recognition Settings
LANGUAGE = 'en-US'
RECOGNITION_TIMEOUT = 5

# Text-to-Speech Settings
VOICE_RATE = 175
VOICE_VOLUME = 1.0

# Application Settings
DEFAULT_LOCATION = 'New York'
NEWS_COUNTRY = 'us'
NEWS_CATEGORY = 'general'
MAX_HEADLINES = 5

# Database Settings
DATABASE_PATH = 'assistant.db'
