import os

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database configuration
DB_NAME = 'shop_details.db'
DB_PATH = os.path.join(BASE_DIR, DB_NAME)
SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_PATH}'

# Search model artifacts directory
MODELS_DIR = os.path.join(BASE_DIR, 'python', 'classifire')

# Uploads directory
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'shop_img')

# Ensure directories exist
for d in [MODELS_DIR, UPLOAD_FOLDER]:
    if not os.path.exists(d):
        os.makedirs(d)
