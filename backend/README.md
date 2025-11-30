# Backend - Flask API

This is the Flask backend for the Plan It Ahead application.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```

5. Update the `.env` file with your configuration.

## Running the Server

```bash
python app.py
```

The server will run on `http://localhost:5000` by default.

## API Endpoints

- `GET /api/health` - Health check endpoint
- `GET /api/test` - Test endpoint


