import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    # Consul configuration
    CONSUL_HOST = os.getenv('CONSUL_HOST', 'localhost')
    CONSUL_PORT = os.getenv('CONSUL_PORT', '8500')
    CONSUL_SCHEME = os.getenv('CONSUL_SCHEME', 'http')
    CONSUL_TOKEN = os.getenv('CONSUL_TOKEN', '')

    # Refresh configuration
    REFRESH_INTERVAL = int(os.getenv('REFRESH_INTERVAL', '3600'))  # 1 hour in seconds
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('DEBUG', False)
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    SECRET_KEY = os.getenv('SECRET_KEY')
    # Oauth
    OAUTH_CLIENT_ID=os.getenv('OAUTH_CLIENT_ID', 'inventory')
    OAUTH_CLIENT_SECRET=os.getenv('OAUTH_CLIENT_SECRET')
    OAUTH_ISSUER=os.getenv('OAUTH_ISSUER')
    OAUTH_SCOPE=os.getenv('OAUTH_SCOPE','openid profile email roles')
