# Virtual Personal Assistant

A Python-based voice-activated personal assistant that can handle various tasks through voice commands. This assistant uses speech recognition for input and provides voice responses, making it a hands-free solution for daily tasks.

## Features

### Voice Interaction
- Speech recognition for user commands
- Natural text-to-speech responses
- Adjustable voice settings (rate, volume, voice type)

### Core Functionalities
- **Weather Updates**: Get current weather for any location
- **News Headlines**: Fetch and read top news headlines
- **Time Information**: Current time and date queries
- **Application Control**: Launch system applications via voice
- **Web Searches**: Perform Google searches through voice commands
- **Reminders**: Set and manage voice-activated reminders

### System Integration
- SQLite database for persistent data storage
- Integration with OpenWeatherMap and News APIs
- Background task scheduling for reminders
- System application launching capabilities

## Prerequisites

- Python 3.8 or higher
- Working microphone
- Internet connection
- API keys for OpenWeatherMap and NewsAPI

## Installation

1. Clone the repository:
```bash
git clone https://github.com/stephenombuya/Virtual-Personal-Assistant
cd virtual-assistant
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
```

5. Edit the `.env` file with your API keys and preferences:
```
WEATHER_API_KEY=your_openweathermap_api_key
NEWS_API_KEY=your_newsapi_key
```

## Usage

1. Start the assistant:
```bash
python main.py
```

2. Wait for the greeting message and start speaking commands.

### Available Voice Commands

- Weather Information:
  ```
  "Weather in London"
  "What's the weather like in New York?"
  ```

- News Updates:
  ```
  "Tell me the news"
  "What's happening today?"
  ```

- Time Queries:
  ```
  "What time is it?"
  "What's the current time?"
  ```

- Reminders:
  ```
  "Reminder at 3 pm to call mom"
  "Set a reminder for 2 pm to take medicine"
  ```

- Application Control:
  ```
  "Open Chrome"
  "Open Notepad"
  ```

- Web Searches:
  ```
  "Search for Python tutorials"
  "Search how to make pasta"
  ```

- Exit Command:
  ```
  "Goodbye"
  "Exit"
  ```

## Project Structure

```
virtual-assistant/
├── main.py              # Main application file
├── config.py            # Configuration settings
├── requirements.txt     # Project dependencies
├── .env                 # Environment variables
├── .env.example         # Example environment file
└── assistant.db         # SQLite database
```

## Configuration

The assistant can be configured through the following files:

1. `.env` file for sensitive data:
   - API keys
   - Default settings

2. `config.py` for general settings:
   - Speech recognition parameters
   - Text-to-speech settings
   - Application defaults

## Dependencies

Major dependencies include:
- SpeechRecognition
- pyttsx3
- pyaudio
- requests
- python-dotenv
- schedule
- SQLite3

## Error Handling

The assistant includes error handling for:
- Speech recognition failures
- API connection issues
- Invalid commands
- Database operations
- Application launching errors

## Future Improvements

- Calendar integration
- Email functionality
- Music player control
- Smart home device integration
- Custom command creation
- Multi-language support
- GUI interface
- Voice authentication
- Natural language processing improvements

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/new-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature/new-feature`
5. Submit a pull request

## Troubleshooting

Common issues and solutions:

1. Microphone not working:
   - Check system microphone settings
   - Ensure PyAudio is properly installed
   - Grant microphone permissions to the application

2. API errors:
   - Verify API keys in .env file
   - Check internet connection
   - Confirm API service status

3. Command recognition issues:
   - Speak clearly and at a moderate pace
   - Reduce background noise
   - Check microphone volume levels

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## Acknowledgments

- OpenWeatherMap API for weather data
- NewsAPI for news headlines
- Python Speech Recognition community
- pyttsx3 developers
- Schedule library maintainers

## Contact

For questions and support:
- Create an issue in the repository

## Disclaimer

This assistant is for educational and personal use. Some features may require API keys or services that need separate subscriptions or registrations.
