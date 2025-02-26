# AI-Powered Debate Generator

An interactive web application that generates AI-powered debates using Llama models through Ollama.

## Features
- Real-time AI debate generation
- Interactive debate continuation
- Compromise generation
- Message-bubble style interface
- Local AI processing (no API costs)

## Requirements
- Python 3.8+
- Ollama
- Flask

## Installation

1. Clone the repository:
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Ollama from [ollama.ai](https://ollama.ai)

4. Pull the Llama model:
```bash
ollama pull llama2
```

5. Run the application:
```bash
python app.py
```

6. Open your browser and navigate to:
```
http://127.0.0.1:5000
```

## Usage
1. Enter a debate topic (optional) or let the system generate one
2. Click "Generate Debate" to start
3. Use "Continue Debate" to extend the discussion
4. Generate a compromise when ready

## Project Structure
```
ai-debate-generator/
├── app.py              # Main Flask application
├── templates/          # HTML templates
│   └── index.html     # Main page template
├── requirements.txt    # Python dependencies
└── README.md          # Project documentation
```

## License
MIT License

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.