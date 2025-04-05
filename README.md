# Eldercare Application

A Flask-based web application for elderly care management.

## Features
- Health monitoring
- User data management
- AI-powered assistance

## Setup
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   - Create a `.env` file
   - Add your GEMINI_API_KEY

## Running the Application
```bash
python Eldercare.py
```

## Deployment
The application is configured for deployment on Render:
- Uses gunicorn as the WSGI server
- Configured with render.yaml
- Environment variables managed through Render dashboard

## Project Structure
- `Eldercare.py` - Main application file
- `templates/` - HTML templates
- `requirements.txt` - Python dependencies
- `render.yaml` - Render deployment configuration
- `Procfile` - Process configuration for Render

## License
[Add your license information here] 