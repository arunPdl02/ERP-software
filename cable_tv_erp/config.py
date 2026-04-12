import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'cable_tv_erp')
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
