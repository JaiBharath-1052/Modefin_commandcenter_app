from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from default_image_blob import default_profile
from fastapi_mail import ConnectionConfig
from datetime import datetime,timedelta
from dotenv import load_dotenv
import asyncio
import os

#from app_log.logModule import log_message

load_dotenv()

# from .. import settings
DEBUG = False #os.getenv("DEBUG")
# DATABASE_URL = "postgresql+psycopg2://postgres:54321@mode@localhost:5432/chatapi"
# DATABASE_URL = "postgresql+asyncpg://postgres:M0defin@0107@localhost:5432/chatapi"
# DATABASE_URL = f"postgresql+asyncpg://postgres:M0defin0107@127.0.0.1:5432/chatapi"
DATABASE_URL = f"postgresql+asyncpg://{os.getenv('DBUSER')}:{os.getenv('DBPASS')}@{os.getenv('DBHOST')}:{os.getenv('DBPORT')}/{os.getenv('DBNAME')}"
#log_message("Database url testing:" ,  DATABASE_URL)
engine = create_async_engine(DATABASE_URL, echo=DEBUG)
SessionLocal = AsyncSession(engine, expire_on_commit = False, autoflush=True)


# DEFAULT PROFILE PICTURE BLOB DATA 
default_profile_pic =default_profile.encode("utf-8")
REDIS_HOST = f"{os.getenv('REDISHOST')}"
REDIS_PORT = os.getenv("REDISPORT")

# Redis config
CHANNEL_LAYERS = {
    "default": {
        "CONFIG": {
            # "hosts": [(f"192.168.145.75", 6379)],
            "hosts" : [(REDIS_HOST, REDIS_PORT)]
        },
    },
}



# JWT
JWT_SETTINGS = {
    "SECRET_KEY": os.getenv("JWTSALT"),
    "ALGORITHM": os.getenv("JWTALGO"), 
    "TOKEN_LOCATION": ['headers'],
    "ACCESS_TOKEN_EXPIRE_MINUTES": timedelta(minutes=1440),
    "ACCESS_TOKEN_REFRESH_EXPIRE_MINUTES": timedelta(minutes=1440),
}


# MAIL
conf = ConnectionConfig(
   MAIL_USERNAME="python0555@gmail.com",
   MAIL_FROM="python0555@gmail.com",
   MAIL_PASSWORD="54321@python0555",
   MAIL_FROM_NAME="Modefin",
   MAIL_PORT=587,
   MAIL_SERVER="smtp.gmail.com",
   MAIL_TLS=True,
   MAIL_SSL=False
)


domain_name = 'http://192.168.145.75/api'


# JWT TOKEN EMAIL INVITATION
token_expiry_time = 500  #this is in seconds

#CONVERSATION OF NUMBER OF DAYS
conversation_time = thirty_days_ago = datetime.today() - timedelta(days=30)
