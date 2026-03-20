import os
from dotenv import load_dotenv

# 1. This line tells Python to look for your .env file
load_dotenv()

class Config:
    # 2. This pulls the secret key from .env, or uses a fallback for safety
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # 3. This pulls the database link from your .env file
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False