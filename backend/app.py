from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

# CORS configuration - allow all origins in development, restrict in production
# Update origins list with your frontend URL when deploying
allowed_origins = os.getenv('CORS_ORIGINS', '*').split(',')
CORS(app, origins=allowed_origins if allowed_origins != ['*'] else ['*'])

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return {'status': 'ok', 'message': 'Flask backend is running'}, 200

@app.route('/api/test', methods=['GET'])
def test():
    """Test endpoint"""
    return {'message': 'Backend is working!'}, 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])


