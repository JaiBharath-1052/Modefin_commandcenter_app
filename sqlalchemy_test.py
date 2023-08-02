from sqlalchemy import select
from sqlalchemy.orm import selectinload,joinedload
from sqlalchemy import and_, or_
from sqlalchemy import exc

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


from dotenv import load_dotenv
import settings
import asyncio
import os

from models import DefaultTeam, User,Company,AccountOptions

load_dotenv()

# Create Session 
DATABASE_URL = f"postgresql://{os.getenv('DBUSER')}:{os.getenv('DBPASS')}@{os.getenv('DBHOST')}:{os.getenv('DBPORT')}/{os.getenv('DBNAME')}"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = Session(engine, expire_on_commit = False, autoflush=True)

# app_id = "00bb01432dd840aebef0a76a22bae0ea"
app_id = "621373dad5fa46b9a32e1746c6fa16b8"
app_id = "9005c72eff0744149c294b187544f4a1"

bot_id = 4

with SessionLocal:
	with SessionLocal.begin_nested():
		try:
			account_option_query = select(AccountOptions).options(
				selectinload(AccountOptions.super_admin).options(
					selectinload(User.chat_widget_customization),
					selectinload(User.chat_widget_configuration),
					selectinload(User.default_team).options(
						selectinload(DefaultTeam.bots)))
				).where(AccountOptions.app_id==app_id)
			account_option_obj = SessionLocal.execute(account_option_query)
			account_option_obj = account_option_obj.scalars().first()
			# account_option_query = select(AccountOptions).options(
			# 	selectinload(AccountOptions.super_admin).options(
			# 		selectinload(User.chat_widget_customization),
			# 		selectinload(User.chat_widget_configuration),
			# 		selectinload(User.default_team).options(selectinload(DefaultTeam.bots)))).where(AccountOptions.app_id==app_id)
			# account_option_obj = SessionLocal.execute(account_option_query)
			# account_option_obj = account_option_obj.scalars().first()
			print(account_option_obj)
			print(account_option_obj.super_admin.default_team.bots)
		except Exception as e:
			print(e)
			print("Some Issue")


# Create Session 
# DATABASE_URL = f"postgresql+asyncpg://{os.getenv('DBUSER')}:{os.getenv('DBPASS')}@{os.getenv('DBHOST')}:{os.getenv('DBPORT')}/{os.getenv('DBNAME')}"
# engine = create_async_engine(DATABASE_URL, echo=DEBUG)
# SessionLocal = AsyncSession(engine, expire_on_commit = False, autoflush=True)


# async def getAccountDetails():
# 	async with settings.SessionLocal as SessionLocal:
# 		async with SessionLocal.begin_nested():
# 			try:
# 				account_option_query = select(AccountOptions).options(
# 					selectinload(AccountOptions.super_admin).options(
# 						selectinload(User.chat_widget_customization),
# 						selectinload(User.chat_widget_configuration),
# 						selectinload(User.default_team).options(selectinload(DefaultTeam.bots)))).where(AccountOptions.app_id==app_id)
# 				account_option_obj = await SessionLocal.execute(account_option_query)
# 				account_option_obj = account_option_obj.scalars().first()
# 				print(account_option_obj)
# 			except:
# 				print("Some Issue")

# asyncio.run(getAccountDetails)