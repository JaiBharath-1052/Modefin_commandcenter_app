import os
import asyncio
import settings
from dotenv import load_dotenv
from celery import Celery
from utils.helpers import *
from fastapi_mail import FastMail, MessageSchema

load_dotenv()

broker=f"redis://{os.getenv('REDISUSER')}:{os.getenv('REDISPASS')}@{os.getenv('REDISHOST')}:{os.getenv('REDISPORT')}/0"
backend=f"redis://{os.getenv('REDISUSER')}:{os.getenv('REDISPASS')}@{os.getenv('REDISHOST')}:{os.getenv('REDISPORT')}/0"
print("broker:", broker)
celery = Celery(
    __name__,
    broker=broker,
    backend=backend
)

mail = FastMail(settings.conf)



@celery.task
def sendEmailNotificationTask(conv_id):
    asyncio.run(sendEmailNotification(conv_id))
    
    
@celery.task
def sendFallbackEmailTask(conversation_id,email_to):
    asyncio.run(sendFallbackEmail(conversation_id,email_to))
    

@celery.task
def sendEmails(subject,recipients,body):
    message = MessageSchema(
    subject=subject,
    recipients=recipients,  # List of recipients, as many as you can pass
    body=body,
    subtype="html"
    )
    asyncio.run(mail.send_message(message))
