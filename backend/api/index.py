"""
Vercel serverless function wrapper for Flask app
"""
import sys
import os

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app

# Vercel Python runtime automatically detects the 'app' variable
# and uses it as the WSGI application

