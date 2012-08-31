DEBUG = True
SECRET_KEY = 'development key'
DB_URL = "postgresql://kozupload@localhost/kozupload"
SQLALCHEMY_DATABASE_URI = DB_URL
SQLALCHEMY_ECHO = True
MAX_CONTENT_LENGTH = 200 * 1024 * 1024
