import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-to-a-random-secret-key-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://root:your_password@localhost/ai_chat?charset=utf8mb4'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ZHIPU_API_KEY = os.environ.get('ZHIPU_API_KEY', 'your-zhipu-api-key-here')
