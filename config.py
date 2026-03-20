import os
from dotenv import load_dotenv

# 1. This line tells Python to look for your .env file
load_dotenv()

class Config:
    # 2. This pulls the secret key from .env, or uses a fallback for safety
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # 3. This pulls the database link from your .env file
    db_url = os.environ.get("DATABASE_URL", "sqlite:///site.db")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    SQLALCHEMY_DATABASE_URI = db_url
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False