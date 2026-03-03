# DataChat AI API

AI-powered data analysis and chat assistant with RAG (Retrieval-Augmented Generation) capabilities.

## Features

- FastAPI-based REST API
- RAG knowledge base integration
- Rate limiting and security middleware
- CORS support for web applications
- Health monitoring endpoints

## Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/prashanthCannyfore/rag-application.git
cd rag-application
```

2. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
copy .env.example .env
# Edit .env with your API keys and configuration
```

5. Run the application:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Environment Variables

Create a `.env` file with:

```
# Add your environment variables here
# See .env.example for required variables
```

## Project Structure

```
app/
├── middleware/          # Custom middleware
├── routers/            # API route handlers
├── services/           # Business logic services
└── main.py            # FastAPI application entry point
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License