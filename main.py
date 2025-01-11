# main.py
import speech_recognition as sr
import pyttsx3
import datetime
import sqlite3
import json
import requests
import webbrowser
import os
import subprocess
import schedule
import time
from threading import Thread
from config import WEATHER_API_KEY, NEWS_API_KEY
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os.path
import pickle




class CalendarAPI:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.credentials = None
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Authenticate with Google Calendar API"""
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.credentials = pickle.load(token)
        
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                self.credentials = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.credentials, token)
        
        self.service = build('calendar', 'v3', credentials=self.credentials)

    def list_events(self):
        """List the next 5 events from the calendar"""
        events_result = self.service.events().list(
            calendarId='primary', maxResults=5, singleEvents=True,
            orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        event_list = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            event_list.append(f"{start}: {event['summary']}")
        return event_list

    def add_event(self, summary, start_time, end_time, description=''):
        """Add an event to the calendar"""
        event = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': start_time, 'timeZone': 'UTC'},
            'end': {'dateTime': end_time, 'timeZone': 'UTC'}
        }
        created_event = self.service.events().insert(calendarId='primary', body=event).execute()
        return created_event['htmlLink']

class VirtualAssistant:
    def __init__(self):
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()

        # Initialize CalendarAPI
        self.calendar = CalendarAPI()
        
        # Initialize text-to-speech engine
        self.speaker = pyttsx3.init()
        
        # Set voice properties
        voices = self.speaker.getProperty('voices')
        self.speaker.setProperty('voice', voices[1].id)  # Index 1 for female voice
        self.speaker.setProperty('rate', 175)  # Speed of speech
        
        # Initialize database connection
        self.db = Database()
        
        # Initialize API handlers
        self.weather = WeatherAPI(WEATHER_API_KEY)
        self.news = NewsAPI(NEWS_API_KEY)
        
        # Start scheduler thread
        self.scheduler_thread = Thread(target=self.run_scheduler, daemon=True)
        self.scheduler_thread.start()

    def speak(self, text):
        """Convert text to speech"""
        print(f"Assistant: {text}")
        self.speaker.say(text)
        self.speaker.runAndWait()

    def listen(self):
        """Listen for voice input and convert to text"""
        with sr.Microphone() as source:
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source)
            
        try:
            command = self.recognizer.recognize_google(audio).lower()
            print(f"User: {command}")
            return command
        except sr.UnknownValueError:
            return "none"
        except sr.RequestError:
            self.speak("Sorry, there was an error with the speech recognition service.")
            return "none"

    def process_command(self, command):
        """Process voice commands and execute appropriate actions"""
        if "weather" in command:
            location = command.replace("weather", "").strip()
            weather_data = self.weather.get_weather(location)
            self.speak(f"The weather in {location} is {weather_data['description']} "
                      f"with a temperature of {weather_data['temperature']}°C")

        elif "news" in command:
            news_headlines = self.news.get_headlines()
            self.speak("Here are today's top headlines:")
            for headline in news_headlines[:3]:
                self.speak(headline)

        elif "reminder" in command:
            self.set_reminder(command)

        elif "open" in command:
            app_name = command.replace("open", "").strip()
            self.open_application(app_name)

        elif "search" in command:
            query = command.replace("search", "").strip()
            webbrowser.open(f"https://www.google.com/search?q={query}")
            self.speak(f"Searching for {query}")

        elif "time" in command:
            current_time = datetime.datetime.now().strftime("%I:%M %p")
            self.speak(f"The current time is {current_time}")

        elif "exit" in command or "goodbye" in command:
            self.speak("Goodbye!")
            return False

        elif "calendar" in command:
            if "events" in command:
                events = self.calendar.list_events()
                if events:
                    self.speak("Here are your upcoming events:")
                    for event in events:
                        self.speak(event)
                else:
                    self.speak("You have no upcoming events.")
                    
        elif "add event" in command:
            self.speak("What is the event title?")
            title = self.listen()
            self.speak("What is the start time? (e.g., 2025-01-12T10:00:00)")
            start_time = self.listen()
            self.speak("What is the end time? (e.g., 2025-01-12T11:00:00)")
            end_time = self.listen()
            link = self.calendar.add_event(title, start_time, end_time)
            self.speak(f"Event added. You can view it here: {link}")
            
        return True

    def set_reminder(self, command):
        """Set a reminder from voice command"""
        try:
            # Extract time and message from command
            # Example: "reminder at 3 pm to call mom"
            parts = command.split("to", 1)
            time_str = parts[0].replace("reminder at", "").strip()
            message = parts[1].strip()
            
            # Schedule the reminder
            schedule.every().day.at(time_str).do(self.remind, message)
            self.db.add_reminder(time_str, message)
            
            self.speak(f"I'll remind you to {message} at {time_str}")
        except Exception as e:
            self.speak("Sorry, I couldn't set that reminder. Please try again.")

    def remind(self, message):
        """Execute reminder"""
        self.speak(f"Reminder: {message}")

    def open_application(self, app_name):
        """Open system applications"""
        app_mappings = {
            "chrome": "google-chrome",
            "firefox": "firefox",
            "word": "winword",
            "excel": "excel",
            "notepad": "notepad"
        }
        
        try:
            if app_name in app_mappings:
                subprocess.Popen(app_mappings[app_name])
                self.speak(f"Opening {app_name}")
            else:
                self.speak("Sorry, I don't know how to open that application")
        except Exception as e:
            self.speak("Sorry, I couldn't open that application")

    def run_scheduler(self):
        """Run scheduled tasks"""
        while True:
            schedule.run_pending()
            time.sleep(1)

    def run(self):
        """Main loop for the virtual assistant"""
        self.speak("Hello! How can I help you today?")
        
        while True:
            command = self.listen()
            if command != "none":
                if not self.process_command(command):
                    break

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('assistant.db')
        self.create_tables()

    def create_tables(self):
        """Create necessary database tables"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders
            (id INTEGER PRIMARY KEY,
             time TEXT NOT NULL,
             message TEXT NOT NULL,
             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
        ''')
        self.conn.commit()

    def add_reminder(self, time, message):
        """Add a new reminder to the database"""
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO reminders (time, message) VALUES (?, ?)',
                      (time, message))
        self.conn.commit()

class WeatherAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"

    def get_weather(self, location):
        """Get weather data for a location"""
        try:
            params = {
                'q': location,
                'appid': self.api_key,
                'units': 'metric'
            }
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            return {
                'temperature': data['main']['temp'],
                'description': data['weather'][0]['description']
            }
        except Exception as e:
            return {
                'temperature': 'unknown',
                'description': 'unavailable'
            }

class NewsAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2/top-headlines"

    def get_headlines(self):
        """Get top news headlines"""
        try:
            params = {
                'country': 'us',
                'apiKey': self.api_key
            }
            response = requests.get(self.base_url, params=params)
            data = response.json()
            
            return [article['title'] for article in data['articles'][:5]]
        except Exception as e:
            return ["Unable to fetch news headlines"]

if __name__ == "__main__":
    assistant = VirtualAssistant()
    assistant.run()
