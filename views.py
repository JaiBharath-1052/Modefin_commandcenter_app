from fastapi import Header, Request, Response,Query,Cookie,BackgroundTasks

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.exceptions import RequestValidationError



# Typing
from typing import Optional,Dict
import json
# Error
import sys

#os
from os import listdir
from os.path import isfile, join

# Password hashing
import bcrypt

import uuid
import operator #user for sorting objects

from serializers import UserInSerializer, TokenCreateInSerializer, TokenRefreshInSerializer
from serializers import ProfileDataSerializer,ProfilePhotoSerializer,EmailUpdationSerializer,PasswordUpdationSerializer
from serializers import EmailNotificationSerializer, BrowserNotificationSerializer, CompanyDetailsSerializer
from serializers import DomainUrlSeriializer,ChangeRoleSerializer,DeleteTeammateSerializer,TeammateInvitationSerializer
from serializers import ResendInvitationSerializer,DeleteInvitationSerializer,RegisterInvitationSerializer
from serializers import CreateTeamSerializer,EditTeamSerializer,DeleteTeamSerializer,AddTeammembersSerializer
from serializers import RemoveTeammateSerializer, AddBotToTeamSerializer,RemoveBotSerializer,CsatRatingsSerializer
from serializers import FallbackEmailSerializer,AssignConversationSerializer,BotRoutingRulesSerializer
from serializers import HumanRoutingRulesSerializer,ConvReassignmentSerializer,UnassignedBotReplySerializer
from serializers import WaitingQueueSerializer,MaxConcurrentChatsSerializer,AutoResolveSerilaizer
from serializers import ConvTranscriptCompanySerilaizer,ConvTranscriptUserSerilaizer,AddQuickReplySerilaizer
from serializers import EditQuickReplySerilaizer,DeleteQuickReplySerilaizer, PseudonymSerilaizer
from serializers import WidgetStyleSerializer,WidgetBrandingSerializer,NotificationSoundSerializer
from serializers import SecureChatWidgetSerializer,BotReplyDelaySerializer,SingleThreadConvSerializer
from serializers import DisableChatWidgetSerializer,DomainRestrictionSerializer,TextToSpeechSerializer
from serializers import SpeechToTextSerializer,HideAttachmentSerializer,GreetingMessageSerializer
from serializers import WelcomeMessageSerializer,EditGreetingMessageSerializer,EnablePreChatLeadCollectionSerializer
from serializers import PreChatHeadingSerializer,AddPreChatFieldSerializer,EditPreChatFieldSerializer
from serializers import DeletePreChatFieldSerializer,AwayMessageSerializer,CollectEmailSerializer
from serializers import KnownUsersAwayMessageSerializer,UnknownUsersAwayMessageSerializer,AddWcMsgCategorySerializer
from serializers import DeleteWcMsgCategorySerializer,AddWcMsgSerializer,EditWcMsgSerializer,DeleteWcMsgSerializer
from serializers import AwayModeSerializer,AddHelpCenterCategorySerializer,EditHelpCenterCategorySerializer
from serializers import DeleteHelpCenterCategorySerializer,AddHelpCenterArticleSerializer
from serializers import EditHelpCenterArticleSerializer,DeleteHelpCenterArticleSerializer
from serializers import ShowHelpCenterArticleSerializer,HelpCenterCustomizationSerializer,HelpCenterDomainUrlSerializer,AddTagSerializer
from serializers import DialogFlowESSerializer,EditBotProfileSerializer,EditBotHumanHandoffSerializer
from serializers import DialogFlowESUpdateSerializer,DialogFlowCXSerializer,DialogFlowCXUpdateSerializer
from serializers import CustomPlatformSerializer,CustomPlatformUpdateSerializer,AddNewConversationSerializer
from serializers import DeleteCustomerSerializer,BlockCustomerSerializer,AddCustomerEmailSerializer
from serializers import AddCustomerRealnameSerializer,AddCustomerPhoneSerializer,AddConversationTagSerializer
from serializers import RemoveConversationTagSerializer,ConversationStatusSerializer,TagSerializer
from serializers import ConversationAssignmmentSerializer,AllCustomersSerializer,TakeOverConversationSerilaizer
from serializers import SendTranscriptSerilaizer,ConversationFilterSerializer,ForgotPasswordSerializer
from serializers import ResetPasswordSerializer,EditTagSerializer,CsatRatingSerilaizer,WcMsgCrudSerializer
from serializers import OpPermissionTeammateSerializer, OpPermissionBotSerializer, OpPermissionTeamSerializer
from serializers import ChangeAvailablitySerializer,ChangeConvOpenedSerializer,AutoResolveMessageSerilaizer


 


from models import DefaultTeam, User,Company,Team,Bot,DialogFlowES,DialogFlowCX,AccountOptions,ConversationTags
from models import ConversationRules,QuickReply,ChatWidgetCustomization,ChatWidgetConfiguration,GreetingMessage
from models import WelcomeMessages,AwayMessage,HelpCenterCategory,HelpCenterArticle,HelpCenterCustomization
from models import Customers,Conversation,PreChatLeadCollection,WelcomeMessageConfiguration,CustomBotPlatform
from models import Tags,CsatRatings,OperatorPermissions,AgentPunchRecord


from random import randint

# Sqlalchemy
from sqlalchemy import select
from sqlalchemy.orm import selectinload,joinedload
from sqlalchemy import and_, or_
from sqlalchemy import exc


# JWT
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import JWTDecodeError,MissingTokenError

import random

from datetime import datetime, timedelta
import jwt
import settings

from tasks import sendEmails
from app_log.logModule import log_message

from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

templates = Jinja2Templates(directory="templates")


def strip(text):
    if isinstance(text, str):
        return text.strip()
    else:
        return None
    
def checkImageSize(base64data,size_limit):
    if base64data.endswith("=="):
        padding = 2
    elif base64data.endswith("="):
        padding = 1
    else:
        padding = 1
            
    base64string = base64data.split(',')[1][:-padding]
    size = ((len(base64string)*(3/4)) - base64string.count('='))/1000
    if size > size_limit:
        return False
    else:
        return True
    
        
  
from tasks import *
# {"conv_id":"task_id"}
task_container = {}
    
#some changes
async def home():
    log_message(10,f"Just checking log")
    # await addEmailTemplates()
    return JSONResponse(content={"Home": "API", "DB": "Connected"})



#---------------------------------------- USER SIGNUP & LOGIN START ---------------------------------------

async def generateVerificationCode(n):
    range_start = 10**(n - 1)
    range_end = (10**n) - 1   
    return str(randint(range_start, range_end))


async def createUser(request_data: UserInSerializer):
    try:
        log_message(10,f"User trying to register his account! INPUT:{{'first_name':{request_data.first_name},'last_name':{request_data.last_name},'email':{request_data.email}}}")
        
        if request_data.password == request_data.password2:
            db_user = User(first_name=request_data.first_name, last_name=request_data.last_name, role='SuperAdmin')
            if db_user.is_valid_email(strip(request_data.email))==True:
                db_user.email = strip(request_data.email)
            else:
                log_message(20,f"Invalid email address while registering a new account! INPUT:{{'first_name':{request_data.first_name},'last_name':{request_data.last_name},'email':{request_data.email}}}")
                return JSONResponse(content={"Error": "Invalid email address!"})
                
            db_user.pass_hasher(request_data.password)
            db_user.unique_id = str(uuid.uuid4().hex)
            db_user.email_invitation_status = 0
            db_user.company = Company()
            db_user.chat_widget_customization = ChatWidgetCustomization()
            db_user.chat_widget_configuration = ChatWidgetConfiguration()
            db_user.greeting_message = GreetingMessage()
            db_user.away_message = AwayMessage()
            db_user.pre_chat_lead_collection = PreChatLeadCollection()
            db_user.welcome_msg_configuration = WelcomeMessageConfiguration()
            db_user.help_center_customization =  HelpCenterCustomization()
        else:
            log_message(20,f"Passwords did not match while registering a new account! INPUT:{{'first_name':{request_data.first_name},'last_name':{request_data.last_name},'email':{request_data.email}}}")
            return JSONResponse(content={"Error": "Password didn't match!"})
        
        # Check if email exist
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).filter_by(email=request_data.email)
                        user_obj = await SessionLocal.execute(user_obj_query)
                        user_obj = user_obj.scalars().first()
                        log_message(10,f" user_obj = {user_obj}")
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch user_obj_query while creating the new user! INPUT:{{'first_name':{request_data.first_name},'last_name':{request_data.last_name},'email':{request_data.email}}} ")
                        return JSONResponse(content={"Error": "Error creating a user!"})
                    
                    if user_obj is None:
                        db_user.email_verification_code = await generateVerificationCode(30)
                        SessionLocal.add(db_user)
                        await SessionLocal.flush()
                        db_user.super_admin_id = db_user.id
                        
                        df_team=DefaultTeam(super_admin_id = db_user.id, assign_new_conv_to_bot=False, notify_everybody=True, initial_assignment_id=db_user.id, user_assigned_when_noone_is_online_id= db_user.id)
                        
                        SessionLocal.add(df_team)
                        await SessionLocal.flush()
                        
                        acc_option = AccountOptions(super_admin_id = db_user.id, first_conversation_assignment_id=df_team.id, app_id=uuid.uuid4().hex)
                        SessionLocal.add(acc_option)
                        await SessionLocal.flush()
                        
                        operator_permissions = OperatorPermissions(account_options_id = acc_option.id)
                        SessionLocal.add(operator_permissions)
                        
                    else:
                        log_message(20,f"User already exists error while creating new user! INPUT:{{'first_name':{request_data.first_name},'last_name':{request_data.last_name},'email':{request_data.email}}}")
                        return JSONResponse(content={"Error": "User exist!"})
                    
                    try:
                        email_query = select(EmailTemplates).filter(EmailTemplates.template_name=='user_verification_template')
                        log_message(10,f" email_query in views.py ={email_query}")
                        mail_data_obj = await SessionLocal.execute(email_query)
                        mail_data_obj = mail_data_obj.scalars().first()
                        log_message(10,f" mail_data_obj in views.py ={mail_data_obj}")
                    except:
                        log_message(40,str(sys.exc_info())+f"Error fetching email query while creating new user! INPUT:{{'first_name':{request_data.first_name},'last_name':{request_data.last_name},'email':{request_data.email}}}")
                        return JSONResponse(content={"Error":"Error creating a user!"})
                    
                    try:
                        verification_url = settings.domain_name + "/api/user/verification/" + str(db_user.email_verification_code)
                        log_message(10,f" verification_url in views.py ={verification_url}")
                        sendEmails.delay(mail_data_obj.message_subject,[request_data.email],mail_data_obj.message_template.format(verification_url))
                        
                    except:
                        log_message(40,str(sys.exc_info())+f"Error sending verification email while creating new user! INPUT:{{'first_name':{request_data.first_name},'last_name':{request_data.last_name},'email':{request_data.email}}}")
                        return JSONResponse(content={"Error": "Error creating a user!"})
                    
                await SessionLocal.commit()
                log_message(20,f"User created successfully. User has to verify through email! INPUT:{{'first_name':{request_data.first_name},'last_name':{request_data.last_name},'email':{request_data.email}}}")
                return JSONResponse(content={"message":"User created successfully, Please verify through your email!"})
        except:
            log_message(40,str(sys.exc_info())+f"Some unknown error while creating a new user1! INPUT:{{'first_name':{request_data.first_name},'last_name':{request_data.last_name},'email':{request_data.email}}}")
            return JSONResponse(content={"Error": "Error creating a user!"})
    except:
        log_message(40,str(sys.exc_info())+f"Some unknown error while creating a new user2! INPUT:{{'first_name':{request_data.first_name},'last_name':{request_data.last_name},'email':{request_data.email}}}")
        return JSONResponse(content={"Error": "Error creating a user!"})




async def emailVerification(code: str):
    try:
        log_message(10,f"A user is trying to verify through his email! {{'Code':{code}}}")
        async with settings.SessionLocal as SessionLocal:
            async with SessionLocal.begin_nested():
                try:
                    user_query = select(User).filter_by(email_verification_code=code)
                    user_obj = await SessionLocal.execute(user_query)
                    user_obj = user_obj.scalars().first()
                except:
                    log_message(20,str(sys.exc_info())+f"Couldn't fetch the user_query while making email verification! {{'Code':{code}}}")
                    return JSONResponse(content={"Error": "Email already verified."}) # to deceive hacking attempts
                
                if user_obj is not None:
                    if user_obj.email_verified is False:
                        user_obj.email_verified = True
                    else:
                        log_message(20,f"Email already verified error while making email verification! {{'Code':{code} 'User':{user_obj.email}}}")
                        return JSONResponse(content={"Error": "Email already verified"})  
                else:
                    log_message(20,f"Invalid verification code error while making email verification! {{'Code':{code} 'User':'None'}}")
                    return JSONResponse(content={"Error": "Invalid verification code"})  
                
            await SessionLocal.commit()
            log_message(20,f"Email verified successfully! {{'Code':{code} 'User':{user_obj.email}}}")
            return JSONResponse(content={"message": "Email verified successfully"})
    except:
        log_message(40,str(sys.exc_info())+f"Unown error while making email verification! {{'Code':{code},'User':None}}")
        return JSONResponse(content={"Error": "Error verifying the code"}) 
    
    

  
async def forgotPassword(request_data: ForgotPasswordSerializer):
    try:
        async with settings.SessionLocal as SessionLocal:
            async with SessionLocal.begin_nested():
                try:
                    user_query = select(User).filter_by(email=request_data.email)
                    user_obj = await SessionLocal.execute(user_query)
                    user_obj = user_obj.scalars().first()  
                    log_message(20,f"User trying to access forgot password api! INPUT:{request_data.dict()}")
                except:
                    log_message(40,str(sys.exc_info())+f"Couldn't fetch user_query while accessing the forgot password api! INPUT:{request_data.dict()}")
                    
                    return JSONResponse(content={"Error": "Couldn't fetch user_query while sending email for forgot password"})
                    
                if user_obj is not None:
                    key = settings.JWT_SETTINGS["SECRET_KEY"]
                    payload = {
                        "email" : user_obj.email,
                        "exp":datetime.utcnow() + timedelta(seconds=settings.token_expiry_time) #can be minutes, days
                    }
                    encoded_token = jwt.encode(payload, key, algorithm="HS256")
                    
                    try:
                        email_query = select(EmailTemplates).filter(EmailTemplates.template_name=='password_reset_template')
                        mail_data_obj = await SessionLocal.execute(email_query)
                        mail_data_obj = mail_data_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch email_query while accessing the forgot password api! INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Couldn't fetch user_query while sending email for forgot password!"})
                    
                    try:
                        verification_url = settings.domain_name +"/reset-password/" + encoded_token.decode('utf-8')
                        sendEmails.delay(mail_data_obj.message_subject,[request_data.email],mail_data_obj.message_template.format(verification_url,verification_url))
                    except:
                        log_message(40,str(sys.exc_info())+f"Error sending email while accessing the forgot password api! INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error": "Unknown error"})
                else:
                    log_message(40,str(sys.exc_info())+f"User does not exist for the requested email id while accessing the forgot password api! INPUT:{request_data.dict()}")
                    return JSONResponse(content={"Error": "User does not exist for this email id"}) 
                
            log_message(20,f"Password reset link has been sent successfully while accessing the forgot password api! INPUT:{request_data.dict()}")
            return JSONResponse(content={"message": "Email has been sent to your account. Please reset he password to login again!"})
    except:
        log_message(40,str(sys.exc_info())+f"Unknown error while accessing the forgot password api! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Unknown error"})

  

async def resetForgotPassword(request_data:ResetPasswordSerializer, token:str):
    try:
        async with settings.SessionLocal as SessionLocal:
            async with SessionLocal.begin_nested():
                try:
                    decoded_token_data = jwt.decode(token, settings.JWT_SETTINGS["SECRET_KEY"], algorithms=['HS256'])
                    email = decoded_token_data["email"]
                    log_message(20,f"User trying to reset the forgot password! EMAIL:{email}")
                    try:
                        user_query = select(User).filter_by(email=email)
                        user_obj = await SessionLocal.execute(user_query)
                        user_obj = user_obj.scalars().first()  
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch user_query while resetting the forgot password! EMAIL:{email}")
                        return JSONResponse(content={"Error": "Error resetting password"})
                    
                    
                    if request_data.new_password != request_data.confirm_password:
                        log_message(30,f"Passwords didn't match while resetting the password! EMAIL:{email}")
                        return JSONResponse(content={"Error": "Couldn't fetch user_query while resetting the forgot password"})
                    
                    
                    try:
                        user_obj.pass_hasher(request_data.new_password)
                        SessionLocal.add(user_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add user_obj to session while resetting the password! EMAIL:{email}")
                        
                        return JSONResponse(content={"Error":"Error resetting the password"})
                          
                except jwt.ExpiredSignatureError:
                    log_message(30,str(sys.exc_info())+f"Registration link expired while resetting the forgot password!")
                    
                    return JSONResponse(content={"Error" : "Registration link expired"})
                
                except jwt.InvalidTokenError:
                    log_message(40,str(sys.exc_info())+f"Invalid registration link while resetting the forgot password! TOKEN:{token}")
                    
                    return JSONResponse(content={"Error" : "Invalid registration link"})

            await SessionLocal.commit()   
            log_message(20,f"Forgot password reset successfully! EMAIL:{email}")
            return JSONResponse(content={"message": "Password reset successfully! Please login!"})
    except:
        log_message(40,str(sys.exc_info())+f"Unknown error while resetting the forgot password!")
        return JSONResponse(content={"Error": "Error resetting password"})
    
    
    
    
    
    
    
#-------------------------------------------JWT START----------------------------------------------------
# https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
# protect endpoint with function jwt_required(), which requires
# a valid access token in the request headers to access.

# API Functions
async def createToken(request_data: TokenCreateInSerializer, Authorize: AuthJWT=Depends()):
    try:
        log_message(20,f"User trying to access the access token! INPUT:{request_data.email}")
        async with settings.SessionLocal as SessionLocal:
            async with SessionLocal.begin_nested():
                try:
                    user_query = select(User).filter(User.email==request_data.email)
                    user_obj = await SessionLocal.execute(user_query)
                    user_obj = user_obj.scalars().first()
                except:
                    log_message(40,str(sys.exc_info())+"Couldn't fetch the user_query while accessing access token.")
                    return JSONResponse(content={"Error": "Unknown error"})
                
                if user_obj is not None:
                    if user_obj.pass_validator(request_data.password):
                        if user_obj.email_verified:
                            user_obj.last_login = datetime.utcnow()
                            additional_claim = {
                                "name": strip(user_obj.first_name + " "+user_obj.last_name),
                                "role": strip(user_obj.role),
                                "ws":strip(user_obj.unique_id)
                            }
                            access_token = Authorize.create_access_token(subject=user_obj.email.strip(), user_claims=additional_claim)
                            refresh_token = Authorize.create_refresh_token(subject=user_obj.email.strip())
                        else:
                            log_message(20,f"Email not verified error while accessing access token! INPUT:{request_data.email}")
                            
                            return JSONResponse(content={"Error": "Verify your email first"})  
                    else:
                        log_message(20,f"Wrong credentilas error while accessing access token. INPUT:{request_data.email}")
                        
                        return JSONResponse(content={"Error": "Wrong credentials"})  
                else:
                    log_message(20,f"Email doesnot exist error while accessing access token! INPUT:{request_data.email}")
                    
                    return JSONResponse(content={"Error": "Email does not exist"})  
            await SessionLocal.commit()
            log_message(20,f"User successfully accessed the access token! INPUT:{request_data.email}")
            return JSONResponse(content={"access_token": access_token, 'refresh_token': refresh_token})
    except:
        log_message(50,str(sys.exc_info())+"Unknown error while accessing access token")
        return JSONResponse(content={"Error": "Unknown error"})



async def refreshToken(Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_required()
        current_user = Authorize.get_jwt_subject()
        refresh_token = Authorize.create_refresh_token(subject=current_user)
        log_message(20,f"User successfully accessed the refresh token! User:{current_user}")
        return JSONResponse(content={"refresh_token": refresh_token})
    except:
        log_message(40,str(sys.exc_info())+"Unknown error while accessing the refresh token!")
        return JSONResponse(content={"Error": "Unknown Error"})


## Logout API
# - DB Entry
# - If required invalidate the JWT here & a check in createToken 
async def logout(Authorize: AuthJWT=Depends()):
    Authorize.jwt_required()
    current_user = Authorize.get_jwt_subject()
    
    pass


#-------------------------------------------USER SIGNUP & LOGIN END------------------------------------------


#-------------------------------- SETTINGS / PERSONAL / PROFILE ---------------------------------

async def showProfile(Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view the profile data! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).where(User.email==current_user_email,User.email_verified==True)
                        user_obj = await SessionLocal.execute(user_obj_query)
                        user_obj = user_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch user_obj_query while viewing profile data! USER:{current_user_email}")
                        return JSONResponse(content={'Error':"Couldn't fetch requested resource!"})
                    user_info =  user_obj.serialize()
                    log_message(20,'User successfully viewed the profile!'+f" USER:{current_user_email}")
                    
                    return JSONResponse(content={'user_details':user_info})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing profile data! USER:{current_user_email}")
            return JSONResponse(content={'Error':"Couldn't fetch requested resource"}) 
    except:
        log_message(40,str(sys.exc_info())+"Invalid token error while viewing profile data!")
        return JSONResponse(content={"Error":"Invalid Token"})
    


async def profileDataUpdation(request_data : ProfileDataSerializer, Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,"User trying to update the profile data"+f"USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).where(User.email==current_user_email,User.email_verified==True)
                        user_obj = await SessionLocal.execute(user_obj_query)
                        user_obj = user_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch user_obj_query while viewing profile data! USER:{current_user_email} INPUT:{request_data.dict()}")
                        
                        return JSONResponse(content={"Error":"Error updating profile data"})
                    try:
                        user_obj.first_name=request_data.first_name
                        user_obj.last_name = request_data.last_name
                        user_obj.designation=request_data.designation
                        user_obj.country_code=request_data.country_code
                        user_obj.contact_number=request_data.contact_number
                        SessionLocal.add(user_obj)
                    except:
                        log_message(30,str(sys.exc_info())+f"Error adding user_obj to session while updating profile data! USER:{current_user_email} INPUT:{request_data.dict()}")
                        
                        return JSONResponse(content={"Error":"Error updating profile data"})
                await SessionLocal.commit()
                log_message(20,f"Profile data updated! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Profile data updated"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating profile data USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={'Error':'Error updating profile data'}) 
    except Exception as e:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating profile data INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



async def profilePhotoUpdation(request_data : ProfilePhotoSerializer, Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update the profile picture USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).where(User.email==current_user_email,User.email_verified==True)
                        user_obj = await SessionLocal.execute(user_obj_query)
                        user_obj = user_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch the user_obj_query while updating the profile picture! USER:{current_user_email} ")
                        
                        return JSONResponse(content={"Error":"Error updating profile picture"})
                    try:
                        blob_data = request_data.pic
                        if checkImageSize(blob_data,500) == True:
                            blob_data_encoded = blob_data.encode("utf-8")
                            user_obj.profile_photo=blob_data_encoded
                            SessionLocal.add(user_obj)
                        else:
                            log_message(40,f"Image size cannot be more than 500kb while updating the profile picture! USER:{current_user_email}")
                            
                            return JSONResponse(content={"Error":"Image size cannot be more than 500kb"}) 
                    except:
                        log_message(30,str(sys.exc_info())+f"Cannot add the user_obj to session while updating the profile picture! USER:{current_user_email} ")
                        
                        return JSONResponse(content={"Error":"Error updating profile picture"})
                await SessionLocal.commit()
                log_message(20,f"Profile picture updated! USER:{current_user_email}")
                return JSONResponse(content={"message":"Profile picture updated"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating the profile picture! USER:{current_user_email}")
            return JSONResponse(content={'Error':'Error updating profile picture'}) 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating the profile picture!")
        return JSONResponse(content={"Error": "Invalid token"})



async def emailUpdation(request_data : EmailUpdationSerializer, Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(20,f"User trying to update the email. USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).where(User.email==current_user_email,User.email_verified==True)
                        user_obj = await SessionLocal.execute(user_obj_query)
                        user_obj = user_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch the user_obj_query while updating the email! USER:{current_user_email} INPUT:{request_data.dict()}")
                        
                        return JSONResponse(content={"Error":"Error updating the email"})  
                    try:
                        new_email = strip(request_data.new_email)
                        if new_email =="":
                            log_message(20, f"Email cannot be empty string error while updating email! USER:{current_user_email} INPUT:{request_data.dict()}")
                            
                            return JSONResponse(content={'Error':'Error updating the email'})
                        
                        if user_obj.is_valid_email(new_email)==True:
                                user_obj.email =new_email
                        else:
                            log_message(20,f"Invalid email address while updating email! USER:{current_user_email} INPUT:{request_data.dict()}")
                            
                            return JSONResponse(content={"Error": "Invalid email address!"})
                        
                        SessionLocal.add(user_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add user_obj to session while updating the email! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the email"})  
                await SessionLocal.commit()
                log_message(20,f"User email updated! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"User email updated! Login again"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating email. USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={'Error':'Error updating the email'}) 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating email. INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})




async def passwordUpdation(request_data : PasswordUpdationSerializer, Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update the password USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).where(User.email==current_user_email)
                        user_obj = await SessionLocal.execute(user_obj_query)
                        user_obj = user_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch the user_obj_query while updating password! USER:{current_user_email}")
                        
                        return JSONResponse(content={'Error':'Error updating the password'})
                    
                    if request_data.new_password != request_data.confirm_password:
                        log_message(20,f"Passwords do not match error while updating password! USER:{current_user_email}")  
                        
                        return JSONResponse(content={'Error':'Passwords do not match'})
                    
                    if user_obj.pass_validator(request_data.current_password)==False:
                        log_message(20,f"Password incorrect error while updating password! USER:{current_user_email}") 
                        
                        return JSONResponse(content={"message": "Password incorrect"})
                    try:
                        user_obj.pass_hasher(request_data.new_password)
                        SessionLocal.add(user_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add user_obj to session while updating the password! USER:{current_user_email}")
                        
                        return JSONResponse(content={"Error":"Error updating the password"})
                await SessionLocal.commit()   
                log_message(20,f"User password updated! USER:{current_user_email}")                       
                return JSONResponse(content={'message': "User password updated successfully"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating password! USER:{current_user_email}")
            return JSONResponse(content={'Error':'Error updating the password'}) 
    except:
        log_message(40,str(sys.exc_info())+"Invalid token error while updating password!")
        return JSONResponse(content={"Error": "Invalid token"})




#----------------------------------  SETTINGS / PERSONAL/ NOTIFICATION PREFERENCES ------------------------------------

async def notificationPreferences( Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view notification preferences! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).where(User.email==current_user_email)
                        user_obj = await SessionLocal.execute(user_obj_query)
                        user_obj = user_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch user_obj query while viewing notification preferences! USER:{current_user_email}")
                        
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"}) #Data base fetching error
        
                    result_dict = user_obj.notification_preferences()
        
                    log_message(20,f"User viewed notification preferences! USER:{current_user_email}")
                    
                    return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing notification preferences! USER:{current_user_email}")
            return JSONResponse(content={'Error':'Error updating the password'})
    except:
        log_message(40,str(sys.exc_info())+"Invalid token error while viewing notification preferences!")
        return JSONResponse(content={"Error": "Invalid token"})



async def emailNotificationUpdation(request_data : EmailNotificationSerializer, Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update email notification! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).where(User.email==current_user_email)
                        user_obj = await SessionLocal.execute(user_obj_query)
                        user_obj = user_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Coulldn't fetch the user_obj_query while updating email notification! USER:{current_user_email} INPUT:{request_data.dict()}")
                        
                        return {"Error":"Error updating email notification"}
                    try:
                        user_obj.email_notification = request_data.email_notification
                        SessionLocal.add(user_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add user_obj to session while updating email notification! USER:{current_user_email} INPUT:{request_data.dict()}")
                        
                        return {"Error":"Error updating email notification"} 
                await SessionLocal.commit()
                log_message(20,f"User updated email notification! USER:{current_user_email} INPUT:{request_data.dict()}")
                return {"message": "Email notification updated"}
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating email notification! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={'Error':'Error updating email notification'}) 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating email notification! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



async def browserNotificationUpdation(request_data : BrowserNotificationSerializer, Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update browser notification! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).where(User.email==current_user_email)
                        user_obj = await SessionLocal.execute(user_obj_query)
                        user_obj = user_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch the user_obj_query while updating browser notification. USER:{current_user_email} INPUT:{request_data.dict()}")
                        
                        return {"Error":"Error updating browser notification"}
                    try:
                        user_obj.browser_notification_volume=request_data.notification_volume
                        user_obj.browser_notification_sound=request_data.notification_sound
                        SessionLocal.add(user_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add user_obj to session while updating browser notification! USER:{current_user_email} INPUT:{request_data.dict()}")
                        
                        return {"Error":"Error updating browser notification"} #Database insertion error
                await SessionLocal.commit()
                log_message(20,f"User updated browser notification! USER:{current_user_email} INPUT:{request_data.dict()}")
                return {"message": "Sound notification updated"}
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating browser notification! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={'Error':"Error updating browser notification"}) #'Data base fetching error'
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating browser notification! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



#--------------------- SETTINGS/ COMPANY /GENERAL ------------------------------------------



async def companyDetails( Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view company details! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    user_obj_query = select(User).options(joinedload(User.company)).where(User.email==current_user_email)
                    user_obj = await SessionLocal.execute(user_obj_query)
                    user_obj = user_obj.scalars().first()
        except:
            log_message(40,str(sys.exc_info())+f"Couldn't fetch user_obj_query while viewing company details! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"}) #Data base fetching error
        result_dict = user_obj.company.serialize()
        log_message(20,f"User viewed company details! USER:{current_user_email}")
        return JSONResponse(content=result_dict)
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing company details.")
        return JSONResponse(content={"Error": "Invalid token"})



async def companyDetailsUpdation(request_data : CompanyDetailsSerializer, Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update company details! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).options(joinedload(User.company)).where(User.email==current_user_email)
                        user_obj = await SessionLocal.execute(user_obj_query)
                        user_obj = user_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch user_obj_query while updating company details!. USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating company details!"})
                    try:
                        user_obj.company.company_name=request_data.company_name
                        user_obj.company.company_url = request_data.company_url
                        SessionLocal.add(user_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add user_obj to session while updating company details!. USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating company details!"})
                await SessionLocal.commit()
                log_message(20,f"User updated company details! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message": "Company details updated!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating company details! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={'Error':'Error updating company details!'}) 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating company details! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



async def domainUrlUpdation(request_data : DomainUrlSeriializer, Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update company domain url! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).options(joinedload(User.company)).where(User.email==current_user_email)
                        user_obj = await SessionLocal.execute(user_obj_query)
                        user_obj = user_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch the user_obj_query while updating company domain url! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating company domain url"})
                    try:
                        user_obj.company.custom_domain_url=request_data.custom_domain_url
                        SessionLocal.add(user_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add the user_obj while updating company domain url! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating company domain url"})
                await SessionLocal.commit()
                log_message(20,f"User updated company domain url! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message": "Custom domain url updated"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating company domain url! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={'Error':'Error updating company domain url'})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating company domain url! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



#------------------------ SETTINGS / COMPANY / TEAM_MATES ---------------------------------------------
async def teammates( Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to fetch teammates details! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).options(selectinload(User.default_team).options(selectinload(DefaultTeam.bots))).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing teammates details! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                    
                    if current_user.role == "SuperAdmin":
                        super_admin = current_user
                        log_message(10,f"SSSSSSSSSSSSSSSsuper_admin in if! USER:{super_admin}")
                    else:
                        super_admin_id = current_user.super_admin_id
                        try:
                            super_admin_query = select(User).options(
                                joinedload(User.default_team).options(
                                    joinedload(DefaultTeam.super_admin),
                                    joinedload(DefaultTeam.bots).options(
                                        joinedload(Bot.integration_platform))
                                            )).filter(User.id==super_admin_id)
                            super_admin = await SessionLocal.execute(super_admin_query)
                            super_admin = super_admin.scalars().first()
                            log_message(10,f"SSSSSSSSSSSSSSSsuper_admin in else ! USER:{super_admin}")
                        except:
                            log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing teammates details! USER:{current_user_email}")
                            return JSONResponse(content={"Error":"Couldn't fetch requested resource2"}) 

                    
                    result_dict = {}
                    result_dict["default_team"]={}
                    result_dict["default_team"]["team_name"]="Default Team"
                    result_dict["default_team"]["team_id"]=super_admin.default_team.id
                    result_dict["default_team"]["team_lead"]=super_admin.first_name +" "+ super_admin.last_name
                    
                    try:
                        df_users_query = select(User).options(selectinload(User.teams)).filter(User.super_admin_id==super_admin.id)
                        df_team_users = await SessionLocal.execute(df_users_query)
                        df_team_users = df_team_users.scalars().all() #all users including accepted users, invited users
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch df_users_query while fetching teammates details! USER:{current_user_email}")
                        JSONResponse(content={"Error":"Couldn't fetch requested resource"})  #Data base fetching error
                    
                    default_teammates = list(filter(lambda x: x.email_invitation_status == 2 , df_team_users)) #accepted users 
                    default_teammates.append(super_admin) #accepted users + super_admin
                    
                    try:
                        teams_query = select(Team).options(
                            selectinload(Team.team_members).options(selectinload(User.teams)),
                            selectinload(Team.bots),
                            selectinload(Team.team_lead)).filter(Team.default_team_id==super_admin.default_team.id)
                        teams_of_df_team = await SessionLocal.execute(teams_query)
                        teams_of_df_team = teams_of_df_team.scalars().all() #all users including accepted users, invited users
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch teams_query while fetching teammates details! USER:{current_user_email}")
                        JSONResponse(content={"Error":"Couldn't fetch requested resource"})  #Data base fetching error
                        
                    result_dict["default_team"]["team_members"]=[
                        {
                            "member_id":df_team_user.id,
                            "member_first_name":df_team_user.first_name,
                            "member_last_name":df_team_user.last_name,
                            "member_email":df_team_user.email,
                            "enrolled_teams":[team.team_name for team in teams_of_df_team]+["Default Team"],
                            "member_role":df_team_user.role,
                            "is_online":df_team_user.is_online,
                            "last_seen":str(df_team_user.last_seen)
                        }
                        for df_team_user in default_teammates]
                    
                    
                    default_team_bots = super_admin.default_team.bots #all bots present in default team

                    result_dict["default_team"]["bots"]=[{
                        "bit_id":bot.id,
                        "bot_name":bot.bot_name,
                        "bot_image":str(bot.bot_photo.decode('utf-8')) if bot.bot_photo!=None else None,
                        "bot_id":"bot.integration.bot_id", #should be modified
                        "bot_platform":bot.integration_platform #should be modified
                        } for bot in default_team_bots if bot.is_active==True]

                    invited_df_team_users = list(filter(lambda x: x.email_invitation_status == 1 , df_team_users))

                    result_dict["default_team"]["invited_users"]=[{
                                                            "invitation_id":invited_user.id,
                                                            "invited_email":invited_user.email,
                                                            "invited_role":invited_user.role} for invited_user in invited_df_team_users]
                    result_dict["teams"]=[]
                    for team in teams_of_df_team:
                        team_dict={}
                        team_dict["id"]=team.id
                        team_dict["team_name"]=team.team_name
                        team_dict["team_lead_first_name"]=team.team_lead.first_name 
                        team_dict["team_lead_last_name"]=team.team_lead.last_name 
                        team_dict["team_members"]=[]
                        for team_member in team.team_members:
                            team_member_dict={}
                            team_member_dict["id"]=team_member.id
                            team_member_dict["member_first_name"]=team_member.first_name 
                            team_member_dict["member_last_name"]=team_member.last_name 
                            team_member_dict["member_email"]=team_member.email
                            team_member_dict["enrolled_teams"]=[team.team_name for team in team_member.teams]+["Default Team"]
                            team_member_dict["member_role"]=team_member.role
                            team_member_dict["is_online"]=team_member.is_online
                            team_member_dict["last_seen"]=str(team_member.last_seen)
                            team_dict["team_members"].append(team_member_dict)
                        team_dict["bots"]=[]
                        for bot in team.bots:
                            if bot.is_active==True:
                                team_bot_dict={}
                                team_bot_dict["id"]=bot.id
                                team_bot_dict["bot_name"]=bot.bot_name
                                team_bot_dict["bot_image"]=str(bot.bot_photo.decode('utf-8')) if bot.bot_photo!=None else None
                                team_bot_dict["bot_id"]="bot.integrattiom bot id"
                                team_bot_dict["bot_platform"]="bot.integration_platform.integration_name"
                                team_dict["bots"].append(team_bot_dict)
                        result_dict["teams"].append(team_dict)
                    log_message(20,f"User viewed teammates details! USER:{current_user_email}")
                    return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while fetching teammates details! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource5"}) #Data base fetching error # commented by me
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while fetching teammates details!")
        return JSONResponse(content={"Error": "Invalid token"})




async def changeRole(request_data:ChangeRoleSerializer, Authorize:AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to change the role! USER:{current_user_email} INPUT: {request_data}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Could not fetch current user while changing role! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error updating the role!"}) #Data base fetching error
                    
                    if request_data.role == 'SuperAdmin':
                        log_message(20,f"Input role cannot be Superadmin while changing role! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error updating the role!"}) #Cannot make any user super admin
                        
                    if request_data.user_id ==current_user.super_admin_id or request_data.user_id == current_user.id: 
                        log_message(20,f"Cannot change superadmins or self role! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error updating the role!"}) #self edition and superuser edition is denied
                    else:
                        if current_user.role == "SuperAdmin":
                            super_admin_id = current_user.id
                        else:
                            super_admin_id = current_user.super_admin_id
                        try:
                            user_query = select(User).filter(and_(User.super_admin_id==super_admin_id, User.id==request_data.user_id, User.email_invitation_status==2)) #get accepted user, user with requested id , and user related with the superadmin
                            user_obj = await SessionLocal.execute(user_query)
                            user_obj = user_obj.scalars().first()
                        except:
                            log_message(40,str(sys.exc_info())+f"Could not fetch user while changing role! USER:{current_user_email} INPUT: {request_data}")
                            return JSONResponse(content={"Error":"Error updating the role"}) #Data base fetching error
                        
                        if user_obj == None:
                            log_message(20,f"User obj cannot be none while changing role! USER:{current_user_email} INPUT: {request_data}")
                            return JSONResponse(content={"Error": "Error updating the role"}) #User is not present
                        else:
                            try:
                                user_obj.role=request_data.role
                                SessionLocal.add(user_obj)
                            except:
                                log_message(40,str(sys.exc_info())+f"Error adding user obj to session while changing role! USER:{current_user_email} INPUT: {request_data}")
                                return JSONResponse(content={"Error":"Error updating the role"}) #database updation error
                await SessionLocal.commit()
                log_message(20,f"User changed the role! USER:{current_user_email} INPUT: {request_data}")
                return JSONResponse(content={"message":"User role updated"})
                    
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while changing user role! USER:{current_user_email} INPUT: {request_data}")
            return JSONResponse(content={"Error":"Error updating the role"}) #Data base fetching error
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while changing user role! INPUT: {request_data}")
        return JSONResponse(content={"Error": "Invalid token"})



async def deleteTeammate(request_data:DeleteTeammateSerializer,  Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to delete the teammate! USER:{current_user_email} INPUT: {request_data}")
        try: #fetch the current user
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while deleting teammate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error deleting the teammate"}) 
                        
                    if request_data.user_id ==current_user.super_admin_id or request_data.user_id == current_user.id: 
                        log_message(20,f"Cannot delete self or super_admin while deleting teammate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error deleting the teammate"}) #self edition and superuser edition is denied
                    else:
                        if current_user.role == "SuperAdmin":
                            super_admin_id = current_user.id
                        else:
                            super_admin_id = current_user.super_admin_id
                        try:
                            user_query = select(User).filter(and_(User.super_admin_id==super_admin_id, User.id==request_data.user_id, User.email_invitation_status==2)) #get accepted user, user with requested id , and user related with the superadmin
                            user_obj = await SessionLocal.execute(user_query)
                            user_obj = user_obj.scalars().first()
                        except:
                            log_message(40,str(sys.exc_info())+f"Couldn't fetch user_query while deleting teammate! USER:{current_user_email} INPUT: {request_data}")
                            return JSONResponse(content={"Error":"Error deleting the teammate"}) #Data base fetching error  
                                
                        if user_obj == None:
                            log_message(40,str(sys.exc_info())+f"user_obj cannot be None while deleting teammate! USER:{current_user_email} INPUT: {request_data}")
                            return JSONResponse(content={"Error": "Error deleting the teammate"}) #User is not present
                        else:
                            try:
                                #check default team assigneee option
                                try:
                                    df_team_query = select(DefaultTeam).filter(DefaultTeam.super_admin_id==super_admin_id)
                                    df_team = await SessionLocal.execute(df_team_query)
                                    df_team = df_team.scalars().first()
                                except:
                                    return JSONResponse(content={"Error":"Error deleting the teammate"})
                                
                                if df_team.initial_assignment_id == user_obj.id or df_team.user_assigned_when_noone_is_online_id == user_obj.id:
                                    return JSONResponse(content={"Error":"This user is selected as assignee in Default Team. Please change the assignee in conversation rules before deleting!"})
                                await SessionLocal.delete(user_obj)
                            except:
                                return JSONResponse(content={"Error":"Error deleting the teammate"}) 
                await SessionLocal.commit()
                log_message(20,f"Team mate deleted successfuly! USER:{current_user_email} INPUT: {request_data}")
                return JSONResponse(content={"message":"Teammate deleted"})
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while deleting teammate! USER:{current_user_email} INPUT: {request_data}")
            return JSONResponse(content={"Error":"Error deleting the teammate"}) #Data base fetching error
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while deleting teammate! INPUT: {request_data}")
        return JSONResponse(content={"Error": "Invalid token"})





async def inviteTeammate(request_data:TeammateInvitationSerializer, Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to invite a teammate! USER:{current_user_email} INPUT: {request_data}")
        
        if request_data.role == "SuperAdmin":
            log_message(20,f"Inviting for Super-Admin role error while inviting teammate! USER:{current_user_email} INPUT: {request_data}")
            return JSONResponse(content={"Error":"Error sending the email"}) #Superadmin cannot be invited
        
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first() 
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while inviting teammate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error sending the email"})
                    
                    if current_user.role == "SuperAdmin":
                        super_admin_id = current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                        
                    key = settings.JWT_SETTINGS["SECRET_KEY"]
                    payload = {
                        "invitation_email" : request_data.email,
                        "invitation_role" : request_data.role,
                        "invitor_id" :current_user.id,
                        "exp":datetime.utcnow() + timedelta(seconds=settings.token_expiry_time) #can be minutes, days
                    }

                    encoded_token = jwt.encode(payload, key, algorithm="HS256")
                    
                    url_for_rigistration = settings.domain_name +"/home/register-invited-teammate/" + encoded_token.decode('utf-8')

                    #check for invited user presence
                    try:
                        invited_user_query = select(User).filter(User.email==request_data.email)
                        invited_user = await SessionLocal.execute(invited_user_query)
                        invited_user = invited_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch invited_user_query while inviting teammate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error sending the email"}) #Data base fetching error
                    
                    
                    
                    if invited_user != None and invited_user.email_invitation_status!=3:
                        log_message(20,f"Invitation user is not present or invitation deleted error while inviting teammate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Invitation already sent!"}) 
                
                    if invited_user:
                        if invited_user.email_invitation_status==3:
                            invited_user.email_invitation_status = 1
                            invitation_user_obj = invited_user
                    else:
                        invitation_user_obj = User(email=request_data.email,role=request_data.role,is_invited=True, email_invitor_id=current_user.id, email_invitation_status = 1 ,super_admin_id=super_admin_id, company_id = current_user.company_id,unique_id=str(uuid.uuid4().hex)) #1 means not accepted but sent
                    
                    try:
                        email_query = select(EmailTemplates).filter(EmailTemplates.template_name=='invitation_link_template')
                        mail_data_obj = await SessionLocal.execute(email_query)
                        mail_data_obj = mail_data_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch email_query while while inviting teammate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error sending email"})
                     
                    try:
                        SessionLocal.add(invitation_user_obj)
                        sendEmails.delay(mail_data_obj.message_subject,[request_data.email],mail_data_obj.message_template.format(request_data.role,url_for_rigistration,url_for_rigistration))
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add the invitation_user_obj to session or error in sending email  while inviting teammate! USER:{current_user_email} INPUT: {request_data}")
                        # return JSONResponse(content={"message":"Error sending the email"}) #database insertion error / email ending error
                await SessionLocal.commit()
                log_message(20,f"Team-mate invited successfuly! USER:{current_user_email} INPUT: {request_data}")
                return JSONResponse(content={"message": "Invitation sent. Please check the email"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while inviting teammate! USER:{current_user_email} INPUT: {request_data}")
            return JSONResponse(content={"Error":"Error sending the email "})         
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while inviting teammate! INPUT: {request_data}")
        return JSONResponse(content={"Error": "Invalid token"})


async def resendInvitation(request_data:ResendInvitationSerializer, Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to resend invite to a teammate! USER:{current_user_email} INPUT: {request_data}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first() 
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while reinviting teammate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error resending the email"}) 
                    
                    try:
                        invitation_user_query = select(User).filter(User.email==request_data.email)
                        invitation_user = await SessionLocal.execute(invitation_user_query)
                        invitation_user = invitation_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch invitation_user_query while reinviting teammate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error resending the email"}) 
                    
                    
                    if invitation_user is None:
                        log_message(20,f"invitation_user cannot be None while reinviting teammate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error resending the email"}) #no invited user with this email id
                    
                    
                    key = settings.JWT_SETTINGS["SECRET_KEY"]
                    
                    payload = {
                        "invitation_email" : invitation_user.email,
                        "invitation_role" : invitation_user.role,
                        "invitor_id" :current_user.id,
                        "exp":datetime.utcnow() + timedelta(seconds=settings.token_expiry_time) #can be minutes, days
                    }

                    encoded_token = jwt.encode(payload, key, algorithm="HS256")
                    
                    url_for_rigistration = settings.domain_name + "/home/register-invited-teammate/" + encoded_token.decode('utf-8')
                    
                    try:
                        email_query = select(EmailTemplates).filter(EmailTemplates.template_name=='invitation_link_template')
                        mail_data_obj = await SessionLocal.execute(email_query)
                        mail_data_obj = mail_data_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch email_query while while reinviting teammate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error resending the email"})
                    
                    try:
                        invitation_user.email_invitor_id=current_user.id #current users id must be changed when resend invitation happens
                        invitation_user.email_invitation_status = 1 #He will be able to register and not deleted invitation
                        SessionLocal.add(invitation_user)
                        sendEmails.delay(mail_data_obj.message_subject,[invitation_user.email],mail_data_obj.message_template.format(invitation_user.role,url_for_rigistration,url_for_rigistration))
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add the invitation_user to session or Error in sending email while reinviting teammate! USER:{current_user_email} INPUT: {request_data}")
                        # return JSONResponse(content={"message":"Error sending the email "})
                await SessionLocal.commit()
                log_message(20,f"Team-mate reinvited successfuly! USER:{current_user_email} INPUT: {request_data}")
                return JSONResponse(content={"message": "Resent invitation successfully!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while reinviting teammate! USER:{current_user_email} INPUT: {request_data}")
            return JSONResponse(content={"Error":"Error resending the email"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while reinviting teammate! INPUT: {request_data}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    
    
async def invitedTeammateDeletion(request_data : DeleteInvitationSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to delete invitation of a teammate! USER:{current_user_email} INPUT: {request_data}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        invitation_user_query = select(User).filter(User.email==request_data.email)
                        invitation_user = await SessionLocal.execute(invitation_user_query)
                        invitation_user = invitation_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch invitation_user_query while deleting invitation of a teammate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error deleting the invited user"})
                    
                    try:
                        invitation_user.email_invitation_status=3
                        SessionLocal.add(invitation_user)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add the invitation_user to session while deleting invitation of a teammate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error deleting the invited user"}) #database insertion error
                await SessionLocal.commit()
                log_message(20,f"Invitation deleted successfuly! USER:{current_user_email} INPUT: {request_data}")
                return JSONResponse(content={"message": "The user invitation is deleted."}) #The user will not be able to register with the link already sent
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while deleting invitation of teammate! USER:{current_user_email} INPUT: {request_data}")
            return JSONResponse(content={"Error":"Error deleting the invited user"}) #Data base fetching error        
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while deleting invitation of teammate! INPUT: {request_data}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    
    
async def registerInvitedTeammate(token:str, request_data: RegisterInvitationSerializer):
    log_message(10,f"Teammate trying to register through invitation! INPUT: {request_data} TOKEN:{token}")
    recieved_token =token
    try:
        decoded_token_data = jwt.decode(recieved_token, settings.JWT_SETTINGS["SECRET_KEY"], algorithms=['HS256'])
        email = decoded_token_data["invitation_email"]
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        invitation_user_obj_query = select(User).filter(User.email==email)
                        invitation_user = await SessionLocal.execute(invitation_user_obj_query)
                        invitation_user = invitation_user.scalars().first() 
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch invitation_user_obj_query while registering invited teammate! USER:{email} INPUT: {request_data} TOKEN:{token}")
                        return JSONResponse(content={"Error":"Error registering the user"})
                    
                    #check for invitation status should not be 2  because the user must not be able to use same link after registering again.
                    if invitation_user.email_invitation_status == 2:
                        log_message(20,f"Cannot register already registered user error while registering invited teammate! USER:{email} INPUT: {request_data} TOKEN:{token}")
                        return JSONResponse(content={"Error":"You are already registered"})

                    #check for invitation status should not be 3 # which means invitation denied condition
                    if invitation_user.email_invitation_status == 3:
                        log_message(20,f"Invitation deleted user cannot register error while registering invited teammate! USER:{email} INPUT: {request_data} TOKEN:{token}")
                        return JSONResponse(content={"Error":"Sorry. Your email invitation has been deleted. You will not be able to register"})

                    try:
                        invitation_user.first_name = request_data.first_name
                        invitation_user.last_name = request_data.last_name
                        invitation_user.pass_hasher(request_data.password)
                        invitation_user.email_invitation_status=2 #accepted
                        invitation_user.email_verified = True
                        SessionLocal.add(invitation_user)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add invitation_userto session while registering invited teammate! USER:{email} INPUT: {request_data} TOKEN:{token}")
                        return JSONResponse(content={"Error":"Error registering the user"}) #database insertion error
                await SessionLocal.commit()
                log_message(20,f"Invitation deleted successfuly! USER:{email} INPUT: {request_data} TOKEN:{token}")
                return JSONResponse(content={"message": "Registration Successful! Please Login."})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while registering invited teammate! USER:{email} INPUT: {request_data} TOKEN:{token}")
            return JSONResponse(content={"Error":"Error in registering"}) #Data base fetching error 
    except jwt.ExpiredSignatureError:
        log_message(40,str(sys.exc_info())+f"Registration link expired while registering invited teammate! INPUT: {request_data} TOKEN:{token}")
        return JSONResponse(content={"Error" : "Registration link expired"})
    except jwt.InvalidTokenError:
        log_message(40,str(sys.exc_info())+f"Invalid registration link while registering invited teammate! INPUT: {request_data} TOKEN:{token}")
        return JSONResponse(content={"Error" : "Invalid registration link"})






async def createTeam(request_data:CreateTeamSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to create a team! USER:{current_user_email} INPUT: {request_data}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while creating a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error creating the team"})
                    
                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try: 
                        super_admin_query = select(User).options(selectinload(User.default_team).options(joinedload(DefaultTeam.teams))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()   
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while creating a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error creating the team"}) 
                    
                    all_teams = super_admin.default_team.teams
                    all_team_names =  [team.team_name for team in all_teams]
                    
                    if request_data.team_name in all_team_names:
                        log_message(20,f"Unique team name not given while creating a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error creating the team"}) #Team with same name cannot be created
                    
                    try:
                        all_members_query = select(User).filter(User.super_admin_id==super_admin_id)
                        all_df_teammembers = await SessionLocal.execute(all_members_query)
                        all_df_teammembers = all_df_teammembers.scalars().all() 
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch all_members_query while creating a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error creating the team"})
                    
                    all_df_teammembers.append(super_admin) 
                    all_df_teammember_ids = [member.id for member in all_df_teammembers]
                
                    #if List1 has List2 elements, check=True
                    check =  all(item in all_df_teammember_ids for item in list(set(request_data.team_members)))
                    if check == False:
                        log_message(20,f"Team id requested is not present within this account while creating a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error creating the team"}) #requested team contains other ids not present
                    
                    team_members = list(filter(lambda x:x.id in list(set(request_data.team_members)),all_df_teammembers))
                    
                    if request_data.team_lead in all_df_teammember_ids:
                        team_lead = list(filter(lambda x:x.id == request_data.team_lead , all_df_teammembers))[0]
                    else:
                        log_message(20,f"Team-lead id requested is not present within this account while creating a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error creating the team"}) #Requested team lead id not present in df team
                    try:
                        new_team = Team(team_name=request_data.team_name,team_lead=team_lead, team_members = team_members,default_team_id=super_admin.default_team.id)
                        conv_rules_obj = ConversationRules(team=new_team, initial_assignment_id=team_lead.id,user_assigned_when_noone_is_online_id =team_lead.id)
                        SessionLocal.add_all([new_team,conv_rules_obj])             
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add the created objects to the session while creating a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error creating the team"})
                await SessionLocal.commit() 
                log_message(20,f"Team created successfully! USER:{current_user_email} INPUT: {request_data}")
                return JSONResponse(content={"message":"Team created!"})   
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while creating a team! USER:{current_user_email} INPUT: {request_data}")
            return JSONResponse(content={"Error":"Error creating the team"}) 
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while creating a team! INPUT: {request_data}")
        return JSONResponse(content={"Error": "Invalid token"})   
    
    
    
    
    
    

async def editTeam( request_data : EditTeamSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to edit the team! USER:{current_user_email} INPUT: {request_data}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while editing a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error editing the team"})
                    
                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                      
                    try:        
                        super_admin_query = select(User).options(selectinload(User.default_team).options(joinedload(DefaultTeam.teams))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while editing a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error editing the team"})
                    
                    all_teams = super_admin.default_team.teams
                    
                    #check whether this team id is present under the superadmin teams
                    if request_data.team_id not in [team.id for team in all_teams]:
                        log_message(20,f"Team id requested is not present within this account while editing a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error editing the team"}) #There is no team for this team_id under superadmin

                    #get team and update the team
                    team_obj=list(filter(lambda x: x.id == request_data.team_id, all_teams))[0]
                    
                    #check whether the team with same name is present
                    team_names_without_team_obj = [team.team_name for team in all_teams]
                    team_names_without_team_obj.remove(team_obj.team_name)   #same team can be edited with same name
                    
                    if request_data.team_name in team_names_without_team_obj:
                        log_message(20,f"Team name should be unique while editing a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error editing the team"}) #team with this name already present
                    try:
                        team_obj.team_name=request_data.team_name
                        SessionLocal.add(team_obj) 
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add team_obj to session while editing a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error editing the team"})
                await SessionLocal.commit() 
                log_message(20,f"Team edited successfully! USER:{current_user_email} INPUT: {request_data}")
                return JSONResponse(content={"message":"Team edited!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while editing a team! USER:{current_user_email} INPUT: {request_data}")
            return JSONResponse(content={"Error":"Error editing the team"}) 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while editing a team! INPUT: {request_data}")
        return JSONResponse(content={"Error": "Invalid token"})









async def deleteTeam( request_data: DeleteTeamSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to delete the team! USER:{current_user_email} INPUT: {request_data}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while deleting a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error deleting the team"}) 
                    
                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:    
                        super_admin_query = select(User).options(selectinload(User.default_team).options(joinedload(DefaultTeam.teams))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while deleting a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error deleting the team"})
                    
                    all_teams = super_admin.default_team.teams #all teams under default team
                    
                    #check whether this team id is present under the superadmin teams
                    if request_data.team_id not in [team.id for team in all_teams]:
                        log_message(20,f"Team not present under the account while deleting a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error deleting the team"}) #There is no team for this team_id under superadmin
                    try:
                        #get team and update the team
                        team_obj=list(filter(lambda x: x.id == request_data.team_id, all_teams))[0]
                        await SessionLocal.delete(team_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot delete the team_obj in session while deleting a team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error deleting the team"})
                await SessionLocal.commit() 
                log_message(20,f"Team deleted successfully! USER:{current_user_email} INPUT: {request_data}")
                return JSONResponse(content={"message":"Team deleted!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while deleting a team! USER:{current_user_email} INPUT: {request_data}")
            return JSONResponse(content={"Error":"Error deleting the team"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while deleting a team! INPUT: {request_data}")
        return JSONResponse(content={"Error": "Invalid token"})





async def addTeamMembers( request_data : AddTeammembersSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update team-members! USER:{current_user_email} INPUT: {request_data}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating team-members! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error updating team members"})
                    
                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:     
                        super_admin_query = select(User).options(selectinload(User.default_team).options(joinedload(DefaultTeam.teams))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating team-members! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error updating team members"})
                    
                    all_teams = super_admin.default_team.teams #all teams under default team
                    log_message(10,f"all_teams =============:{all_teams}")
                    # check whether this team id is present under the superadmin teams
                    if request_data.team_id not in [team.id for team in all_teams]:
                        log_message(20,f"There is no team for this team id under super_admin while updating team-members! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error updating team members 9"}) #There is no team for this team_id under superadmin
                    try:
                        team_obj_query=select(Team).options(selectinload(Team.team_members)).filter(Team.id == request_data.team_id) #requested team
                        team = await SessionLocal.execute(team_obj_query)
                        team = team.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch team_obj_query while updating team-members! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error updating team members "})
                    
                    
                    present_team_member_ids = [team_member.id for team_member in team.team_members] #current team members id for this team
                    
                    if request_data.team_members == []:
                        log_message(20,f"Team members list cannot be empty while updating team-members! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error updating team members"})  #Cannot add empty
                        
                    #If requested list contains any number which is already present in present list. Check becomes true
                    #Already added team members cannot be added again
                    check=any(item in present_team_member_ids for item in request_data.team_members)
                    # print("ANY :",check)
                    if check==True:
                        log_message(20,f"Team members already present in default team while updating team-members! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error updating team members "}) #One of the user already exists in the same team
                    
                    #if requested list contains element not present in present list, check becomes false
                    #requested team contains other ids not present
                    try:
                        all_members_query = select(User).filter(User.super_admin_id==super_admin_id)
                        all_df_teammembers = await SessionLocal.execute(all_members_query)
                        all_df_teammembers = all_df_teammembers.scalars().all() 
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch all_members_query while updating team-members! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error updating team members "})
                    
                    all_df_teammembers.append(super_admin)
                    all_df_teammember_ids = [member.id for member in all_df_teammembers]
                    
                    check =  all(item in all_df_teammember_ids for item in list(set(request_data.team_members)))
                    # print("All :",check) 
                    if check == False:
                        log_message(20,f"Team members list contains the ids not present in default team while updating team-members! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error updating team mambers"}) #Contains other ids which is not present 
                    
                    team_members = list(filter(lambda x:x.id in list(set(request_data.team_members)), all_df_teammembers))
                    
                    try:
                        for team_member in team_members:
                            team.team_members.append(team_member)
                        SessionLocal.add(team)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add team object to session while updating team-members! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error updating team members"})
                await SessionLocal.commit() 
                log_message(20,f"Team-members updated successfully! USER:{current_user_email} INPUT: {request_data}")
                return JSONResponse(content={"message":"Team members updated!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating team-members! USER:{current_user_email} INPUT: {request_data}")
            return JSONResponse(content={"Error":"Error updating team mambers "})
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while updating team-members! INPUT: {request_data}")
        return JSONResponse(content={"Error": "Invalid token"})




async def removeTeammate(request_data: RemoveTeammateSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to remove team-mmate! USER:{current_user_email} INPUT: {request_data}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while removing team-mate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error removing team member"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.default_team).options(joinedload(DefaultTeam.teams))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while removing team-mate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error removing team member"})
                    
                    all_teams = super_admin.default_team.teams #all teams under default team
                    
                    # check whether this team id is present under the superadmin teams
                    if request_data.team_id not in [team.id for team in all_teams]:
                        log_message(20,f"There is no team for this team_id under superadmin while removing teammate! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error removing team member"}) #There is no team for this team_id under superadmin
                    try:
                        team_obj_query=select(Team).options(selectinload(Team.team_members), 
                                                            selectinload(Team.conv_rules)).filter(Team.id == request_data.team_id) #requested team
                        team = await SessionLocal.execute(team_obj_query)
                        team = team.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch team_obj_query while removing team-mate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error removing team member"})
                    
                    present_team_member_ids = [team_member.id for team_member in team.team_members] #current team members id for this team
                    if request_data.user_id not in present_team_member_ids:
                        log_message(20,f"There is no user for this user_id under superadmin while removing teammate! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error removing team member"}) #user id not present in this team
                    
                    user_obj = list(filter(lambda x:x.id == request_data.user_id, [team_member for team_member in team.team_members]))[0]
                    
                    if team.conv_rules[0].initial_assignment_id == user_obj.id or team.conv_rules[0].user_assigned_when_noone_is_online_id == user_obj.id:
                        log_message(20,f"User cannot be removed as user is selected as assignee for this team while removing teammate! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"This user is selected as assignee for this Team. Please change the assignee in conversation rules before deleting!"})
                    try:
                        team.team_members.remove(user_obj)
                        SessionLocal.add(team)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add the team object to session while removing team-mate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error removing team member"})
                await SessionLocal.commit() 
                log_message(20,f"Team-member removed successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Team member removed!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating team-members! USER:{current_user_email} INPUT: {request_data}")
            return JSONResponse(content={"Error":"Error removing team member"})
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while updating team-members! INPUT: {request_data}")
        return JSONResponse(content={"Error": "Invalid token"})

            
        
                
    



async def addBotToTeam(request_data: AddBotToTeamSerializer,  Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to add bot to team! USER:{current_user_email} INPUT: {request_data}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while adding bot to team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error adding bots"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.default_team).options(joinedload(DefaultTeam.teams))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while adding bot to team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error adding bots"})
                    
                    all_teams = super_admin.default_team.teams #all teams under default team
                    
                    # check whether this team id is present under the superadmin teams
                    if request_data.team_id not in [team.id for team in all_teams]:
                        log_message(20,f"There is no team for this team_id under superadmin while adding bot to team! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding bots"}) #There is no team for this team_id under superadmin
                    try:
                        team_obj_query=select(Team).options(selectinload(Team.bots)).filter(Team.id == request_data.team_id) #requested team
                        team = await SessionLocal.execute(team_obj_query)
                        team = team.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch team_obj_query while adding bot to team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error adding bots"})
                    
                    present_team_bot_ids = [bot.id for bot in team.bots]

                    if request_data.bot_ids == []:
                        log_message(20,f"Bot id list cannot be empty while adding bot to team! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding bots"})  #Cannot add empty
                        
                    #If requested list contains any number which is already present in present list. Check becomes true
                    #Already added team members cannot be added again
                    check=any(item in present_team_bot_ids for item in request_data.bot_ids)
                    
                    if check==True:
                        log_message(20,f"One of the bot id in the list already exists in the team while adding bot to team! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Bot already exists"}) #One of the bot already exists in the same team
                    
                    #if requested list contains element not present in present list, check becomes false
                    #requested team contains other ids not present
                    try:
                        all_df_bots_query = select(Bot).filter(Bot.default_team_id==super_admin.default_team.id)
                        all_df_bots = await SessionLocal.execute(all_df_bots_query)
                        all_df_bots = all_df_bots.scalars().all()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch all_df_bots_query while adding bot to team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error adding bots"})
                    
                    all_df_bot_ids = [bot.id for bot in all_df_bots]

                    check =  all(item in all_df_bot_ids for item in list(set(request_data.bot_ids)))
                    if check == False:
                        log_message(20,f"Input bot id list contains the id which is not present in the team-bots while adding bot to team! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding bots"}) #Contains other ids which is not present 
                    
                    bots = list(filter(lambda x:x.id in list(set(request_data.bot_ids)), all_df_bots))
                    
                    for bot in bots:
                        team.bots.append(bot)
                    try:
                        SessionLocal.add(team)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add the team object to session while removing team-mate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error adding bots"})
                await SessionLocal.commit() 
                log_message(20,f"Bots added to team successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Bots added!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while adding bots to team! USER:{current_user_email} INPUT: {request_data}")
            return JSONResponse(content={"Error":"Error adding bots"})
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while adding bots to team! INPUT: {request_data}")
        return JSONResponse(content={"Error": "Invalid token"})






async def removeBot(request_data: RemoveBotSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to remove bot from team! USER:{current_user_email} INPUT: {request_data}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while removing bot from team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error removing bot"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.default_team).options(joinedload(DefaultTeam.teams))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while removing bot from team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error removing bot"})
                    
                    all_teams = super_admin.default_team.teams #all teams under default team
                    
                    # check whether this team id is present under the superadmin teams
                    if request_data.team_id not in [team.id for team in all_teams]:
                        log_message(20,f"Team id not present under default team of this account while removing the bot from team! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error removing bot"}) #There is no team for this team_id under superadmin
                    try:
                        team_obj_query=select(Team).options(selectinload(Team.bots)).filter(Team.id == request_data.team_id) #requested team
                        team = await SessionLocal.execute(team_obj_query)
                        team = team.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch team_obj_query while removing bot from team! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error removing bot"})
                    
                    team_bot_ids = [bot.id for bot in team.bots]
                    
                    if request_data.bot_id not in team_bot_ids:
                        log_message(20,f"Requested bot id not present in team while removing the bot from team! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error removing bot"}) #bot not present in the team
                    
                    bot_obj = list(filter(lambda x:x.id == request_data.bot_id,team.bots))[0]
                    try:
                        team.bots.remove(bot_obj)
                        SessionLocal.add(team)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add the team object to session while removing team-mate! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error removing bot"})
                await SessionLocal.commit() 
                log_message(20,f"Bot removed successfully from the team! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Bot removed!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while removing bots from team! USER:{current_user_email} INPUT: {request_data}")
            return JSONResponse(content={"Error":"Error removing bot"})
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while removing bots from team! INPUT: {request_data}")
        return JSONResponse(content={"Error": "Invalid token"})
            
            


async def showCsatRatings(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view CSAT ratings! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing CSAT Ratings! USER:{current_user_email}")
                        return JSONResponse(content={"Error": "Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing CSAT Ratings! USER:{current_user_email}")
                        return JSONResponse(content={"Error": "Couldn't fetch requested resource"})
                    
                    csat_ratings_enabled = super_admin.account_option.csat_ratings_enabled
            log_message(20,f"CAST Ratings viewed successfully! USER:{current_user_email}")
            return JSONResponse(content={"csat_rating_enabled":csat_ratings_enabled })
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing CAST Ratings! USER:{current_user_email}")
            return JSONResponse(content={"Error": "Couldn't fetch requested resource"})
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while viewing CSAT Ratings!")
        return JSONResponse(content={"Error": "Invalid token"})
            




async def csatRatingsUpdation(request_data:CsatRatingsSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update CSAT Ratings! USER:{current_user_email} INPUT: {request_data}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing CSAT Ratings! USER:{current_user_email}")
                        return JSONResponse(content={"Error": "Error updating csat ratings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing CSAT Ratings! USER:{current_user_email}")
                        return JSONResponse(content={"Error": "Error updating csat ratings"})
                    try:
                        super_admin.account_option.csat_ratings_enabled=request_data.turn_on_csat
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add the super_admin object to session while updating CSAT Ratings! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error": "Error updating csat ratings"})
                    
                    result_dict={}
                    if request_data.turn_on_csat == True:
                        result_dict["message"]="CSAT Ratings Enabled!"
                    else:
                        result_dict["message"]="CSAT Ratings Disabled!"    
                await SessionLocal.commit()
                log_message(20,f"CAST Ratings updated successfully! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating CAST Ratings! USER:{current_user_email}")
            return JSONResponse(content={"Error": "Error updating csat ratings"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating CAST Ratings!")
        return JSONResponse(content={"Error": "Invalid token"})
            


async def showFallbackEmails(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view Falback emails setting! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing Falback emails setting! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing Falback emails setting! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                    send_fallback_emails = super_admin.account_option.send_fall_back_emails
                log_message(20,f"Fallback emails viewed successfully! USER:{current_user_email}")
                return JSONResponse(content={"fallback_emails_enabled":send_fallback_emails })
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing Falback emails setting! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while viewing Falback emails setting!")
        return JSONResponse(content={"Error": "Invalid token"})





async def fallbackEmailsUpdation(request_data:FallbackEmailSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update Fallback email setting! USER:{current_user_email} INPUT: {request_data}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating Falback emails setting! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Error updating fallback emails"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating falback emails setting! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Error updating fallback emails"})
                        
                    try:
                        super_admin.account_option.send_fall_back_emails=request_data.turn_on_fallback_email
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add the super_admin object to session while updating fallback emails setting! USER:{current_user_email} INPUT: {request_data}")
                        return JSONResponse(content={"Error":"Error updating fallback emails"})
                    
                    result_dict={}
                    if request_data.turn_on_fallback_email == True:
                        result_dict["message"]="Fallback Emails Enabled!"
                    else:
                        result_dict["message"]="Fallback Emails Disabled!"    
                await SessionLocal.commit()
                log_message(20,f"Fallback emails updated successfully! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating Falback emails setting! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Error updating fallback emails"})
    except Exception as e:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating Falback emails setting!")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    
    
async def conversationRules(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view conversation rules! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing conversation rules! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.account_option),
                            selectinload(User.default_team).options(
                                selectinload(DefaultTeam.teams).options(
                                    selectinload(Team.bots),
                                    selectinload(Team.conv_rules)),
                                selectinload(DefaultTeam.bots))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing conversation rules! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    result_dict = {}
                    result_dict["team_conversation_assignment"]={}
                    result_dict["team_conversation_assignment"]["options"] = [{"id":super_admin.default_team.id, "name": "Default Team"}]
                    
                    all_teams = super_admin.default_team.teams
                    for team in all_teams:
                        team_dict = {}
                        team_dict["id"]=team.id
                        team_dict["name"] = team.team_name
                        result_dict["team_conversation_assignment"]["options"].append(team_dict)
                        
                    if super_admin.account_option.first_conversation_assignment_option == 'DefaultTeam':
                        result_dict["team_conversation_assignment"]["selected"] = {"id":super_admin.default_team.id,"name":"DefaultTeam"}
                    else : #Team
                        team = list(filter(lambda x:x.id == super_admin.account_option.first_conversation_assignment_id,super_admin.default_team.teams))[0]
                        result_dict["team_conversation_assignment"]["selected"] = {"id":team.id, "name":team.team_name}
                        
                    result_dict["conversation_assignment_rules"]=[]

                    #This is only for default Team
                    default_team_conv_ass_rules = {}
                    default_team_conv_ass_rules["id"]=1
                    default_team_conv_ass_rules["name"]="Default Team"
                    default_team_conv_ass_rules["assign_new_conv_to_bot"] = super_admin.default_team.assign_new_conv_to_bot
                    default_team_conv_ass_rules["select_bot"] = []
                    
                    bots_in_default_team = super_admin.default_team.bots
                    for bot in bots_in_default_team:
                        bot_dict={}
                        bot_dict["id"]=bot.id
                        bot_dict["bot_name"] = bot.bot_name
                        default_team_conv_ass_rules["select_bot"].append(bot_dict)
                        
                        
                    selected_bot = list(filter(lambda x:x.id ==super_admin.default_team.bot_selected_id ,super_admin.default_team.bots))

                    if selected_bot == []: #if no bot is selected by default
                        default_team_conv_ass_rules["selected_bot"] = {}
                    else:
                        default_team_conv_ass_rules["selected_bot"] = {"id":selected_bot[0].id, "bot_name":selected_bot[0].bot_name}
                    
                        
                    default_team_conv_ass_rules["human_routing_rules"] = {"option1":{},"option2":{}}
                    option1 = default_team_conv_ass_rules["human_routing_rules"]["option1"]
                    option2 = default_team_conv_ass_rules["human_routing_rules"]["option2"]
                    
                    if super_admin.default_team.notify_everybody == True:
                        default_team_conv_ass_rules["human_routing_rules"]["selected_option"] = "option1"
                    else:
                        default_team_conv_ass_rules["human_routing_rules"]["selected_option"] = "option2"

                    option1["option_name"] = "Notify Everybody"
                    option1["assign_conversation_to"]=[{"id":super_admin.id,"first_name":super_admin.first_name ,"last_name": super_admin.last_name}]

                    option2["option_name"]= "Automatic Assignment"
                    option2["assign_conversation_to"]=[{"id":super_admin.id,"first_name":super_admin.first_name , "last_name" : super_admin.last_name}]
                    
                    try:
                        default_team_members_query = select(User).filter(and_(User.super_admin_id==super_admin.id, User.email_invitation_status==2))
                        default_team_members=await SessionLocal.execute(default_team_members_query)
                        default_team_members = default_team_members.scalars().all()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch default_team_members_query while viewing conversation rules! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                    
                    for team_member in default_team_members:
                        team_member_dict = {}
                        team_member_dict["id"]=team_member.id
                        team_member_dict["first_name"]= team_member.first_name 
                        team_member_dict["last_name"]= team_member.last_name
                        option1["assign_conversation_to"].append(team_member_dict)
                        option2["assign_conversation_to"].append(team_member_dict)
                        
                    #adding super admin to default team members
                    default_team_members.append(super_admin)
                    all_df_team_members = default_team_members


                    selected_user_for_option1 = list(filter(lambda x:x.id ==super_admin.default_team.initial_assignment_id ,all_df_team_members))


                    if selected_user_for_option1 == []:
                        option1["selected_user"]={}
                    else:
                        option1["selected_user"] = {"id":selected_user_for_option1[0].id, "name":selected_user_for_option1[0].first_name + " " +selected_user_for_option1[0].last_name}

                    selected_user_for_option2 = list(filter(lambda x:x.id ==super_admin.default_team.user_assigned_when_noone_is_online_id ,all_df_team_members))


                    if selected_user_for_option2 == []:
                        option2["selected_user"]={}
                    else:
                        option2["selected_user"] = {"id":selected_user_for_option2[0].id, "name":selected_user_for_option2[0].first_name + " " +selected_user_for_option2[0].last_name}

                    result_dict["conversation_assignment_rules"].append(default_team_conv_ass_rules)
                    
                    #Now for all other teams
                    for team in all_teams:
                        team_conv_ass_rules = {}
                        team_conv_ass_rules["id"]=team.id
                        team_conv_ass_rules["name"]=team.team_name
                        team_conv_ass_rules["assign_new_conv_to_bot"] = team.conv_rules[0].assign_new_conv_to_bot
                        team_conv_ass_rules["select_bot"] = []

                        for team_bot in team.bots:
                            team_bot_dict = {}
                            team_bot_dict["id"] = team_bot.id
                            team_bot_dict["bot_name"] = team_bot.bot_name
                            team_conv_ass_rules["select_bot"].append(team_bot_dict)


                        team_conv_ass_rules["selected_bot"] = {}

                        selected_bot = list(filter(lambda x:x.id== team.conv_rules[0].bot_selected_id ,team.bots))

                        if selected_bot == []: #if no bot is selected by default
                            team_conv_ass_rules["selected_bot"] = {}
                        else:
                            team_conv_ass_rules["selected_bot"] = {"id":selected_bot[0].id, "bot_name":selected_bot[0].bot_name}

                        team_conv_ass_rules["human_routing_rules"] = {"option1":{},"option2":{}}
                        option1 = team_conv_ass_rules["human_routing_rules"]["option1"]
                        option2 = team_conv_ass_rules["human_routing_rules"]["option2"]
                        
                        if team.conv_rules[0].notify_everybody == True:
                            team_conv_ass_rules["human_routing_rules"]["selected_option"] = "option1"
                        else:
                            team_conv_ass_rules["human_routing_rules"]["selected_option"] = "option2"

                        option1["option_name"] = "Notify Everybody"
                        option2["option_name"]= "Automatic Assignment"
                        
                        try:
                            team_query = select(Team).options(selectinload(Team.team_members),
                                                            selectinload(Team.team_lead)).filter(Team.id==team.id)
                            team = await SessionLocal.execute(team_query)
                            team = team.scalars().first()
                        except:
                            log_message(40,str(sys.exc_info())+f"Couldn't fetch team_query while viewing conversation rules! USER:{current_user_email}")
                            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                        if team.team_lead in team.team_members:
                            all_team_members = team.team_members
                        else:
                            team.team_members.append(team.team_lead)
                            all_team_members = team.team_members

                        option1["assign_conversation_to"]=[]
                        option2["assign_conversation_to"]=[]

                        for team_member in all_team_members:
                            team_member_dict = {}
                            team_member_dict["id"]=team_member.id
                            team_member_dict["name"]= team_member.first_name + " " + team_member.last_name
                            option1["assign_conversation_to"].append(team_member_dict)
                            option2["assign_conversation_to"].append(team_member_dict)


                        option1["selected_user"] = {}
                        option2["selected_user"] = {}

                        selected_user_for_option1 = list(filter(lambda x:x.id ==team.conv_rules[0].initial_assignment_id ,all_team_members))


                        if selected_user_for_option1 == []:
                            option1["selected_user"]={}
                        else:
                            option1["selected_user"] = {"id":selected_user_for_option1[0].id, "first_name":selected_user_for_option1[0].first_name , "last_name" :selected_user_for_option1[0].last_name}

                        selected_user_for_option2 = list(filter(lambda x:x.id ==team.conv_rules[0].user_assigned_when_noone_is_online_id ,all_team_members))

                        if selected_user_for_option2 == []:
                            option2["selected_user"]={}
                        else:
                            option2["selected_user"] = {"id":selected_user_for_option2[0].id,
                                                        "first_name":selected_user_for_option2[0].first_name ,
                                                        "last_name" :selected_user_for_option2[0].last_name}
                        result_dict["conversation_assignment_rules"].append(team_conv_ass_rules)
                        
                    result_dict["conversation_reassignment"]={}
                    result_dict["conversation_reassignment"]["allow"]=super_admin.account_option.allow_conversation_reassignment
                    result_dict["conversation_reassignment"]["reassign_time"] =  {
                        "interval":super_admin.account_option.reassignment_duration,
                        "duration_type":super_admin.account_option.reassignment_interval_type
                    }
                    result_dict["allow_unassigned_bots_to_reply"] = super_admin.account_option.unassigned_bot_can_reply 
                log_message(20,f"User successfully viewed conversation rules! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing conversation rules! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})    
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing conversation rules!")
        return JSONResponse(content={"Error": "Invalid token"})
        

async def assignConversation(request_data:AssignConversationSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update assign all conversations to a team setting in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating assign all conversations to a team setting in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating conversation assignment"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option),
                                                                selectinload(User.default_team).options(
                                                                    joinedload(DefaultTeam.teams)
                                                                    )
                                                                ).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating assign all conversations to a team setting in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating conversation assignment"})

                    if request_data.is_default_team == True:
                        first_conversation_assignment_option = "DefaultTeam"
                        if request_data.team_id != super_admin.default_team.id: #check whether default team id present under super admin
                            log_message(20,f"Default team id not present under superadmin account while updating assign all conversations to a team setting in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating conversation assignment"}) #team id invalid
                        else:
                            first_conversation_assignment_id=request_data.team_id
                    else:
                        first_conversation_assignment_option = "Team"
                        team = list(filter(lambda x:x.id == request_data.team_id,super_admin.default_team.teams))

                        if team == []: #check whether team id present under super admin
                            log_message(20,f"Team id not present under superadmin account while updating assign all conversations to a team setting in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating conversation assignment"}) #team id invalid
                        else:
                            first_conversation_assignment_id=request_data.team_id
                    try:  
                        super_admin.account_option.first_conversation_assignment_option = first_conversation_assignment_option
                        super_admin.account_option.first_conversation_assignment_id = first_conversation_assignment_id
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating assign all conversations to a team setting in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating conversation assignment"})
                await SessionLocal.commit()
                log_message(20,f"Assigning all incoming conversations to team updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Conversation Assignment Updated!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating assign all conversations to a team setting in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error updating conversation assignment"})    
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating assign all conversations to a team setting in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    






async def botRoutingRules(request_data:BotRoutingRulesSerializer, Authorize : AuthJWT=Depends()):
    try:
        print(f"BOTROUTING REQUEST {e} \n {request_data}")
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update routing rules for bot in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating routing rules for bot in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating bot routing rules"}) #database fetching error

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.account_option),
                            selectinload(User.default_team).options(
                                selectinload(DefaultTeam.bots),
                                selectinload(DefaultTeam.teams).options(
                                    selectinload(Team.bots),
                                    selectinload(Team.conv_rules)))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating routing rules for bot in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating bot routing rules"}) #database fetch error
                    
                    is_default_team = request_data.set_rules_for["is_default_team"]
                    team_id = request_data.set_rules_for["team_id"]
                    
                    if request_data.bot_selected == None:
                        log_message(20,f"Bot selected id cannot be None while updating routing rules for bot in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Please select a bot to update Bot routing rules"})
                        
                    
                    if is_default_team == True:
                        if super_admin.default_team.id == team_id:
                            super_admin.default_team.assign_new_conv_to_bot =request_data.assign_conversation_to_bot
                            
                            bots_in_default_team = super_admin.default_team.bots
                            bot_selected = list(filter(lambda x:x.id == request_data.bot_selected, bots_in_default_team))

                            if bot_selected == []:
                                log_message(20,f"Bot selected id not present under super_admin while updating routing rules for bot in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                                return JSONResponse(content={"Error":"Error updating bot routing rules"}) #bot id not present under default team
                            else:
                                try:
                                    super_admin.default_team.bot_selected_id = bot_selected[0].id
                                    SessionLocal.add(super_admin)
                                except:
                                    log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating routing rules for bot in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                                    return JSONResponse(content={"Error":"Error updating bot routing rules"}) #database insertion error
                        else:
                            log_message(20,f"DefaultTeam not present with this id under super_admin while updating routing rules for bot in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating bot routing rules"}) #team id not present
                    else:
                        #check for teams
                        team =  list(filter(lambda x:x.id == team_id, super_admin.default_team.teams))
                        if team == []:
                            log_message(20,f"Team not present with this id under super_admin while updating routing rules for bot in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"message":"There is no team with this id"})
                        
                        bots_in_team = team[0].bots
                        bot_selected = list(filter(lambda x:x.id == request_data.bot_selected, bots_in_team))
                        if bot_selected == []:
                            log_message(20,f"Bot id not present under the selected team while updating routing rules for bot in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating bot routing rules"}) #bot id not present under team
                        else:
                            try:
                                team[0].conv_rules[0].bot_selected_id = bot_selected[0].id
                                team[0].conv_rules[0].assign_new_conv_to_bot = request_data.assign_conversation_to_bot
                                SessionLocal.add(team[0])
                            except:
                                log_message(40,str(sys.exc_info())+f"Cannot add team object to session while updating routing rules for bot in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                                return JSONResponse(content={"Error":"Error updating bot routing rules"}) #database insertion error
                await SessionLocal.commit()
                log_message(20,f"Routing rules for bot in conversation rules updated! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Bot Routing Rules Updated"})    
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating routing rules for bot in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error updating bot routing rules"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error updating routing rules for bot in conversation rules! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    


async def humanRoutingRules(request_data:HumanRoutingRulesSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating human routing rules"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option),
                                                                selectinload(User.default_team).options(
                                                                    joinedload(DefaultTeam.bots),
                                                                    joinedload(DefaultTeam.teams))
                                                                ).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating human routing rules"})
                    
                    
                    is_default_team = request_data.set_rules_for["is_default_team"]
                    team_id = request_data.set_rules_for["team_id"]
                    
                    
                    if request_data.selected_user == None:
                        log_message(20,f"Selected user id cannot be None while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Please select a User to update Human routing rules"})
                        
                    if is_default_team == True: #Updation for default team table
                        if super_admin.default_team.id != team_id:
                            log_message(20,f"Default team id requested is not present under super_admin while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating human routing rules"}) #Default team not present with this id
                        try:
                            all_df_users_query = select(User).filter(and_(User.super_admin_id==super_admin.id,User.email_invitation_status==2))
                            all_users = await SessionLocal.execute(all_df_users_query)
                            all_users = all_users.scalars().all()
                        except:
                            log_message(40,str(sys.exc_info())+f"Couldn't fetch all_df_users_query while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating human routing rules"})
                        
                        all_users.append(super_admin) #because superadmin will not be present in invited users
                        selected_user = list(filter(lambda x:x.id == request_data.selected_user,all_users))

                        if selected_user == []:
                            log_message(20,f"Selected user not present in the dedault team while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating human routing rules"})
                            #user not present in default team

                        if request_data.notify_everybody==True: #initial assignment for selected user
                            try:
                                super_admin.default_team.notify_everybody = request_data.notify_everybody
                                super_admin.default_team.initial_assignment_id = selected_user[0].id
                                super_admin.account_option.waiting_queue_status_on = False
                                SessionLocal.add(super_admin)
                            except:
                                log_message(40,str(sys.exc_info())+f"Cannot add superadmin obj to session while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                                return JSONResponse(content={"Error":"Error updating human routing rules"})#data insertion error
                            
                        else: #notify everybody == false  : user assigned when no one is online
                            try:
                                super_admin.default_team.notify_everybody = request_data.notify_everybody
                                super_admin.default_team.user_assigned_when_noone_is_online_id = selected_user[0].id
                                SessionLocal.add(super_admin)
                            except:
                                log_message(40,str(sys.exc_info())+f"Cannot add superadmin obj to session while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                                return JSONResponse(content={"Error":"Error updating human routing rules"})#data insertion error
                            
                    else:#Updation for Team conversation rules table
                        try:
                            all_teams_query = select(Team).options(selectinload(Team.team_lead),
                                                                selectinload(Team.team_members),
                                                                selectinload(Team.conv_rules)).filter(Team.default_team_id==super_admin.default_team.id)
                            all_teams = await SessionLocal.execute(all_teams_query)
                            all_teams = all_teams.scalars().all()
                        except:
                            log_message(40,str(sys.exc_info())+f"Couldn't fetch all_teams_query while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating human routing rules"})
                                        
                        team = list(filter(lambda x:x.id == team_id, all_teams))
                        
                        if team ==[]:
                            log_message(20,f"There is no team present with this id under super_admin while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating human routing rules"}) #There is no team present with this id
                            
                        
                        if team[0].team_lead in team[0].team_members:
                            all_team_members=team[0].team_members
                        else:
                            team[0].team_members.append(team[0].team_lead)
                            all_team_members=  team[0].team_members
                            
                        selected_user = list(filter(lambda x:x.id == request_data.selected_user,all_team_members))

                        if selected_user == []:
                            log_message(20,f"There is no user present with this id while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating human routing rules"}) #User not present in team

                        if request_data.notify_everybody == True: #initial assignment for selected user
                            try:
                                team[0].conv_rules[0].notify_everybody = request_data.notify_everybody
                                team[0].conv_rules[0].initial_assignment_id = selected_user[0].id
                                SessionLocal.add(team[0])
                            except:
                                log_message(40,str(sys.exc_info())+f"Cannot add team obj to session while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                                return JSONResponse(content={"Error":"Error updating human routing rules"}) #database insertion error
                            
                        else: #notify everybody == false  : user assigned when no one is online
                            try:
                                team[0].conv_rules[0].notify_everybody = request_data.notify_everybody
                                team[0].conv_rules[0].user_assigned_when_noone_is_online_id = selected_user[0].id
                                SessionLocal.add(team[0])
                            except:
                                log_message(40,str(sys.exc_info())+f"Cannot add team obj to session while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                                return JSONResponse(content={"Error":"Error updating human routing rules"})
                            
                await SessionLocal.commit()
                if request_data.notify_everybody == True:
                    log_message(20,f"Notify everybody updated while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Notify everybody updated"})
                else:    # False
                    log_message(20,f"Automatic assignment updated while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Automatic assignment updated"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating routing rules for human in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error updating human routing rules"})            
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating routing rules for human in conversation rules! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    

async def allowConvReassignment(request_data: ConvReassignmentSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update allow conversation re-assignment settings in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating allow conversation re-assignment setting in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"message":"Error updating Reassignment Option"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating allow conversation re-assignment setting in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"message":"Error updating Reassignment Option"})
                    
                    try:
                        super_admin.account_option.reassignment_duration = request_data.time_interval
                        super_admin.account_option.reassignment_interval_type = request_data.duration_type
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating allow conversation re-assignment setting in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating Reassignment Option"})
                await SessionLocal.commit()
                log_message(20,f"Allow conversation re-assignment setting in conversation rules updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Reassignment option updated!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating allow conversation re-assignment setting in conversation rules! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating Reassignment Option"})  #Unknown error         
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating allow conversation re-assignment setting in conversation rules! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    
  

    
async def waitingQueueStatus(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view waiting queue status! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing waiting queue status! USER:{current_user_email}")
                        JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing waiting queue status! USER:{current_user_email}")
                        JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                        
                    result_dict  =  {}
                    result_dict["waiting_queue_status"]=super_admin.account_option.waiting_queue_status_on
                    result_dict["max_concurrent_chats"] = super_admin.account_option.maximum_concurrent_chats
                    
                log_message(20,f"User viewed waiting queue status successfully! USER:{current_user_email}")  
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing waiting queue status! USER:{current_user_email}")
            JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while viewing waiting queue status!")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    
async def enableWaitingQueue(request_data:WaitingQueueSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update waiting queue status! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating waiting queue status! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating waiting queue"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option),
                                                                 selectinload(User.default_team)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating waiting queue status! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating waiting queue"})
                    
                    
                    if super_admin.default_team.notify_everybody==True:
                        log_message(20,f"Automatic assignment should be set in conversation rules inorder to turn on waiting queue error while updating waiting queue status! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Automatic assignment should be set in conversation rules inorder to turn on waiting queue"})
                    
                    try:
                        super_admin.account_option.waiting_queue_status_on = request_data.enable_waiting_queue
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object while updating waiting queue status! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating waiting queue"})
                await SessionLocal.commit()
                log_message(20,f"Waiting queue status updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                if request_data.enable_waiting_queue == True:
                    return JSONResponse(content={"message":"Waiting queue enabled!"})
                else:
                    return JSONResponse(content={"message":"Waiting queue disabled!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating waiting queue status! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating waiting queue"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating waiting queue status! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    
async def maxConcurrentChatsUpdation(request_data:MaxConcurrentChatsSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update max concurrent chats a user can handle setting! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating max concurrent chats a user can handle setting! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating waiting queue"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating max concurrent chats a user can handle setting! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating waiting queue"})
                    
                    if request_data.max_concurrent_users>100:
                        log_message(20,f"Maximum concurrent chats cannot exceed 100 while updating max concurrent chats a user can handle setting! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Maximumm concurrent chats should not be more than 100"})
                    
                    try:
                        super_admin.account_option.maximum_concurrent_chats = request_data.max_concurrent_users
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add superadmin to session while updating max concurrent chats a user can handle setting! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating waiting queue"})
                await SessionLocal.commit()
                log_message(20,f"Maximum concurrent chats a user can handle setting has been updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Max concurrent chats set to {}".format(request_data.max_concurrent_users)})
                
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while updating max concurrent chats a user can handle setting! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating waiting queue"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating max concurrent chats a user can handle setting! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    
    
    
async  def autoResolve(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view auto-resolve setting! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing auto-resolve setting! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing auto-resolve setting! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                        
                    result_dict = {}
                    result_dict["auto_resolve_conversations"] = super_admin.account_option.auto_resolve_conversations
                    result_dict["auto_resolve_message"] = super_admin.account_option.auto_resolve_message 
                log_message(20,f"Auto-resolve setting viewed successfully! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing auto-resolve setting! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing auto-resolve setting! USER:{current_user_email}")
        return JSONResponse(content={"Error": "Invalid token"})
    
      
      
      
      
      
async def autoResolveUpdation(request_data:AutoResolveSerilaizer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update auto-resolve setting! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating auto-resolve setting! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating auto-resolve settings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating auto-resolve setting! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating auto-resolve settings"})
                    
                    try:
                        super_admin.account_option.auto_resolve_conversations = request_data.auto_resolve_conversation
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating auto-resolve setting! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating auto-resolve settings"})
                await SessionLocal.commit()
                log_message(20,f"Conversation auto-resolve settings updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Conversation auto-resolve settings updated!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating auto-resolve setting! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating auto-resolve settings"}) 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating auto-resolve setting! USER:{current_user_email} INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})

    
async def autoResolveMessageUpdation(request_data:AutoResolveMessageSerilaizer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update auto-resolve message! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating auto-resolve message! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating auto-resolve message"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating auto-resolve message! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating auto-resolve message"})
                    
                    try:
                        super_admin.account_option.auto_resolve_message = request_data.auto_resolve_message
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating auto-resolve message! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating auto-resolve message"})
                await SessionLocal.commit()
                log_message(20,f"Conversation auto-resolve message updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Conversation auto-resolve message updated!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating auto-resolve message! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating auto-resolve message"}) 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating auto-resolve message! USER:{current_user_email} INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



async def convTranscript(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view conversation-transcript setting! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing conversation-transcript setting! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing conversation-transcript setting! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                        
                    result_dict  =  {}
                    result_dict["company_email_for_conv_transcript"] = super_admin.account_option.company_email_for_conv_transcript
                    result_dict["send_transcripts_to_user"] = super_admin.account_option.send_transcripts_to_user
                log_message(20,f"Conversation-transcript setting viewed successfully! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing conversation-transcript setting! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while viewing conversation-transcript setting! USER:{current_user_email}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    






async def convTranscriptCompany(request_data:ConvTranscriptCompanySerilaizer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update company email for conversation-transcript! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating company email for conversation-transcript! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating company email"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating company email for conversation-transcript! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating company email"})
                    
                    try:
                        super_admin.account_option.company_email_for_conv_transcript = request_data.company_email
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating company email for conversation-transcript! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating company email"})
                await SessionLocal.commit()
                log_message(20,f"Company email for conversation-transcript updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Company email for chat transcript updated!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating company email for conversation-transcript! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating company email"})  #Unknown error 
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while updating company email for conversation-transcript!  INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})






async def convTranscriptUser(request_data :ConvTranscriptUserSerilaizer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update send transcript to customers email option! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating send transcript to customers emaail settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating user transcript settings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating send transcript to customers emaail settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating user transcript settings"})
                    
                    try:
                        super_admin.account_option.send_transcripts_to_user = request_data.send_transcripts_to_user
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating send transcript to customers email settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating user transcript settings"})
                await SessionLocal.commit()
                log_message(20,f"Send transcript to customers email settings updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                if request_data.send_transcripts_to_user == True:
                    return JSONResponse(content={"message":"Send chat transcript to user enabled!"})
                else:
                    return JSONResponse(content={"message":"Send chat transcript to user disabled!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating send transcript to customers email settings! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating user transcript settings"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating send transcript to customers email settings! USER:{current_user_email} INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    
    
    
async def quickReplies(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view quick-replies! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing quick replies! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.quick_replies)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing quick replies! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                        
                    result_dict  =  {}
                    result_dict["quick_replies"] = [{"id":quick_reply.id, "shortcut_message":quick_reply.shortcut_message, "full_message":quick_reply.full_message} for quick_reply in super_admin.quick_replies]
                    
                log_message(20,f"Quick-replies viewed successfully! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing quick replies! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing quick replies! USER:{current_user_email}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    

    
    
    
    
    
async def addQuickReply(request_data: AddQuickReplySerilaizer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to add quick reply! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while adding quick replies! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error creating quick reply"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.quick_replies)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while adding quick replies! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error creating quick reply"})
                    
                    try:
                        quick_reply_obj = QuickReply(super_admin_id=super_admin.id, shortcut_message = request_data.shortcut_message, full_message = request_data.full_message)
                        SessionLocal.add(quick_reply_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add quick_reply_obj to session while adding quick replies! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error creating quick reply"})
                await SessionLocal.commit()
                log_message(20,f"Quick reply created successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Quick reply created!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while adding quick replies! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error creating quick reply"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while adding quick replies! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    
    
async def editQuickReply(request_data:EditQuickReplySerilaizer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to edit quick reply! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while editing quick reply! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing quick reply"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.quick_replies)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while editing quick reply! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing quick reply"})
                    
                    quick_reply_obj = list(filter(lambda x:x.id == request_data.qr_id, super_admin.quick_replies))

                    if quick_reply_obj == []:
                        log_message(20,f"There is no quick reply object present with this id while editing quick reply! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return {"message":"Error editing quick reply"} #There is no quick reply object present with id.
                    
                    try:
                        quick_reply_obj[0].shortcut_message = request_data.shortcut_message
                        quick_reply_obj[0].full_message = request_data.full_message
                        SessionLocal.add(quick_reply_obj[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add quick_reply_obj to session while editing quick reply! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing quick reply"})
                await SessionLocal.commit()
                log_message(20,f"Quick reply edited successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Quick reply edited!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while editing quick reply! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error editing quick reply"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while editing quick reply! USER:{current_user_email} INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    
    
    
    
async def deleteQuickReply(request_data:DeleteQuickReplySerilaizer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to delete quick reply! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while deleting quick reply! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting quick reply"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.quick_replies)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while deleting quick reply! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting quick reply"})
                    
                    quick_reply_obj = list(filter(lambda x:x.id == request_data.qr_id, super_admin.quick_replies))

                    if quick_reply_obj == []:
                        log_message(20,f"There is no quick reply object present with this id while deleting quick reply! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return {"message":"Error deleting quick reply"} #There is no quick reply object present with id.
                    
                    try:
                        await SessionLocal.delete(quick_reply_obj[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot delete quick_reply_obj in session while deleting quick reply! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting quick reply"})
                await SessionLocal.commit()
                return JSONResponse(content={"message":"Quick reply deleted!"})
                
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while deleting quick reply! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error deleting quick reply"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while deleting quick reply! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    



  
async def pseudonym(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view pseudonym, setting! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing pseudonym setting ! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing pseudonym setting ! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                    
                    result_dict  =  {}
                    result_dict["show_pseudonyms"] = super_admin.account_option.show_pseudonyms
                log_message(20,f"Pseudonym setting viewed successfully! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing pseudonym setting ! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while viewing pseudonym setting!")
        return JSONResponse(content={"Error": "Invalid token"})
    

    
    
    
    
async def pseudonymUpdation(request_data: PseudonymSerilaizer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update pseudonym, setting! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating pseudonym setting ! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating pseudonym settings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.account_option)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating pseudonym setting ! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating pseudonym settings"})
                    
                    try:
                        super_admin.account_option.show_pseudonyms = request_data.show_pseudonyms
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating pseudonym setting ! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating pseudonym settings"})
                await SessionLocal.commit()
                log_message(20,f"Pseudonym setting updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Pseudonym settings updated!"})
                
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating pseudonym setting ! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating pseudonym settings"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating pseudonym setting! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    


async def chatWidgetCustomization(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view chat-widget-customization settings! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing chat-widget-customization settings! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                    
                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        chat_wdgt_cust_query = select(ChatWidgetCustomization).filter(ChatWidgetCustomization.super_admin_id==super_admin_id)
                        customization_obj = await SessionLocal.execute(chat_wdgt_cust_query)
                        customization_obj = customization_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch chat_wdgt_cust_query while viewing chat-widget-customization settings! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                        
                    result_dict  =  {}
                    result_dict["chat_widget_styling"] = {}
                    result_dict["chat_widget_styling"]["color"] = customization_obj.color
                    result_dict["chat_widget_styling"]["launcher_option"]=customization_obj.launcher_option
                    
                    if customization_obj.launcher_option == 'Upload':
                        result_dict["chat_widget_styling"]["icon_image"] = customization_obj.icon_image.decode('utf-8')
                    else:
                        result_dict["chat_widget_styling"]["icon_image"] = customization_obj.default_icon_option
                        
                    result_dict["chat_widget_styling"]["widget_position"] = customization_obj.widget_position
                    result_dict["chat_widget_styling"]["show_branding"] = customization_obj.show_branding
                    result_dict["notification_sound"] = customization_obj.chat_notification_sound
                    
                log_message(20,f"User viewed chat-widget-customization settings successfully! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing chat-widget-customization settings! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing chat-widget-customization settings!")
        return JSONResponse(content={"Error": "Invalid token"})





async def chatWidgetStyling(request_data:WidgetStyleSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update chat-widget-style settings! USER:{current_user_email} INPUT:{request_data.dict()}")
        
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating chat-widget-style settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating chat widget style"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.chat_widget_customization)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating chat-widget-style settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating chat widget style"})
                    
                    try:
                        super_admin.chat_widget_customization.color = request_data.color
                        super_admin.chat_widget_customization.launcher_option = request_data.launcher_icon
                        if request_data.launcher_icon == 'Default':
                            super_admin.chat_widget_customization.default_icon_option = request_data.icon_image
                        else:
                            if checkImageSize(request_data.icon_image,20) == True:
                                super_admin.chat_widget_customization.icon_image = request_data.icon_image.encode('utf-8')
                            else:
                                log_message(30,str(sys.exc_info())+f"Image size cannot be more than 20KB while updating chat-widget-style settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                                return JSONResponse(content={"Error":"Image size cannot be more than 20KB"})
                            
                        super_admin.chat_widget_customization.widget_position = request_data.widget_position
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating chat-widget-style settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating chat widget style"})
                await SessionLocal.commit()
                log_message(20,f"Chat-widget-style settings updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Chat widget style updated!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating chat-widget-style settings! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating chat widget style"})  #Unknown error 
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while updating chat-widget-style settings! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    




async def chatWidgetBranding(request_data:WidgetBrandingSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update chat-widget show branding settings! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating chat-widget show branding settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating show branding option"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.chat_widget_customization)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating chat-widget show branding settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating show branding option"})
                    
                    try:
                        super_admin.chat_widget_customization.show_branding = request_data.show_branding
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating chat-widget show branding settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating show branding option2"})
                await SessionLocal.commit()
                
                if request_data.show_branding == True:
                    log_message(20,f"Chat-widget show branding settings enabled successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Show branding enabled"})
                else:
                    log_message(20,f"Chat-widget show branding settings disabled successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Show branding disabled"})
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while updating chat-widget show branding settings! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating show branding option1"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating chat-widget show branding settings! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    






async def chatNotificationSound(request_data:NotificationSoundSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update chat-widget notification sound! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating chat-widget notification sound! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating notification sound"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.chat_widget_customization)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating chat-widget notification sound! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating notification sound"})
                    
                    try:
                        super_admin.chat_widget_customization.chat_notification_sound = request_data.notification_sound
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating chat-widget notification sound! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating notification sound"})
                await SessionLocal.commit()
                log_message(20,f"Chat-widget notification sound updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Notification sound updated!"})
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while updating chat-widget notification sound! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating notification sound"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating chat-widget notification sound! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    



async def chatWidgetConfig(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view chat-widget configuration! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing chat-widget configuration! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id 
                    try:
                        cht_wdgt_config_query = select(ChatWidgetConfiguration).filter(ChatWidgetConfiguration.super_admin_id==super_admin_id)
                        widget_config_obj = await SessionLocal.execute(cht_wdgt_config_query)
                        widget_config_obj = widget_config_obj.scalars().first() 
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch cht_wdgt_config_query while viewing chat-widget configuration! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                    
                    result_dict  =  {}
                    result_dict["secure_chat_widget"]={}
                    result_dict["secure_chat_widget"]["remove_chat_history_on_page_refresh"]=widget_config_obj.remove_chat_history_on_page_refresh
                    result_dict["secure_chat_widget"]["history_removal_days"]=widget_config_obj.history_removal_days
                    result_dict["secure_chat_widget"]["history_removal_hours"]=widget_config_obj.history_removal_hours
                    result_dict["secure_chat_widget"]["history_removal_minutes"]=widget_config_obj.history_removal_minutes
                    result_dict["time_delay_setting"]=widget_config_obj.bot_reply_delay
                    result_dict["allow_single_thread_conversation"]=widget_config_obj.allow_single_thread_conversation
                    result_dict["disable_chat_widget"]=widget_config_obj.disable_chat_widget
                    result_dict["domain_restriction_list"]=widget_config_obj.domain_restriction_list
                    result_dict["add_text_to_speech"]=widget_config_obj.add_text_to_speech
                    result_dict["add_speech_to_text"]=widget_config_obj.add_speech_to_text
                    result_dict["hide_attachment"]=widget_config_obj.hide_attachment
                log_message(20,f"Chat-widget configuration viewed successfully! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f" Unknown error while viewing chat-widget configuration! USER:{current_user_email}")  
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing chat-widget configuration!")
        return JSONResponse(content={"Error": "Invalid token"})




async def secureChatwidget(request_data:SecureChatWidgetSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update secure chat widget option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating secure chat widget option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating chat widget settings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.chat_widget_configuration)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating secure chat widget option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating chat widget settings"})
                    
                    try:
                        super_admin.chat_widget_configuration.remove_chat_history_on_page_refresh = request_data.remove_chat_history_on_page_refresh
                        super_admin.chat_widget_configuration.history_removal_days = request_data.history_removal_days
                        super_admin.chat_widget_configuration.history_removal_hours = request_data.history_removal_hours
                        super_admin.chat_widget_configuration.history_removal_minutes = request_data.history_removal_minutes
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object while updating secure chat widget option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating chat widget settings"})
                await SessionLocal.commit()
                log_message(20,f"Secure chat widget option in chat widget configuration updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Chat widget settings updated!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating secure chat widget option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating chat widget settings"})  #Unknown error 
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while updating secure chat widget option in chat widget configuration! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



async def botReplyDelay(request_data:BotReplyDelaySerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update time delay setting for bot replies option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating time delay setting for bot replies option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating bot reply delay settings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.chat_widget_configuration)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating time delay setting for bot replies option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating bot reply delay settings"})
                    
                    try:
                        super_admin.chat_widget_configuration.bot_reply_delay = request_data.delay_interval
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating time delay setting for bot replies option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating bot reply delay settings"})
                await SessionLocal.commit()
                log_message(20,f"Time delay setting for bot replies option in chat widget configuration update successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Bot reply delay settings updated!"})
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while updating time delay setting for bot replies option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating bot reply delay settings"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating time delay setting for bot replies option in chat widget configuration! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



async def singleThreadConv(request_data:SingleThreadConvSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update allow single-thread conversation only option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating allow single-thread conversation only option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating single thread conversation settings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.chat_widget_configuration)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating allow single-thread conversation only option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating single thread conversation settings"})
                    
                    try:
                        super_admin.chat_widget_configuration.allow_single_thread_conversation = request_data.is_enabled
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating allow single-thread conversation only option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating single thread conversation settings"})
                await SessionLocal.commit()
                log_message(20,f"Allow single-thread conversation only option in chat widget configuration updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Single thread conversation settings updated!"})
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while updating allow single-thread conversation only option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating single thread conversation settings"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating allow single-thread conversation only option in chat widget configuration! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})




async def disableChatWidget(request_data:DisableChatWidgetSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update disable chat widget option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating disable chat widget option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating disable chat widget settings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.chat_widget_configuration)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating disable chat widget option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating disable chat widget settings"})
                    
                    try:
                        super_admin.chat_widget_configuration.disable_chat_widget = request_data.disable_widget
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating disable chat widget option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating disable chat widget settings"})
                await SessionLocal.commit()
                log_message(20,f"Disable chat widget option in chat widget configuration updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Disable chat widget settings updated!"})
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while updating disable chat widget option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating disable chat widget settings"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating disable chat widget option in chat widget configuration! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})





async def domainRestriction(request_data:DomainRestrictionSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update domain restriction list in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating domain restriction list option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating domain-restriction settings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.chat_widget_configuration)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating domain restriction list option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating domain-restriction settings"})
                    
                    try:
                        super_admin.chat_widget_configuration.domain_restriction_list = request_data.domain_list
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating domain restriction list option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating domain-restriction settings"})
                await SessionLocal.commit()
                log_message(20,f"Domain restriction list option in chat widget configuration updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Domain-restriction settings updated!"})
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while updating domain restriction list option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating domain-restriction settings"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating domain restriction list option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}") 
        return JSONResponse(content={"Error": "Invalid token"})




async def textToSpeech(request_data:TextToSpeechSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update text to speech option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
        
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating text to speech option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating text to speech settings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.chat_widget_configuration)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating text to speech option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating text to speech settings"})
                    
                    try:
                        super_admin.chat_widget_configuration.add_text_to_speech = request_data.is_enabled
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating text to speech option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating text to speech settings"})
                await SessionLocal.commit()
                log_message(20,f"Text to speech option in chat widget configuration updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Text to Speech settings updated!"})
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while updating text to speech option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating text to speech settings"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating text to speech option in chat widget configuration! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})




async def speechToText(request_data:SpeechToTextSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update speech to text option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating speech to text option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating speech to text settings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.chat_widget_configuration)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating speech to text option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating speech to text settings"})
                    
                    try:
                        super_admin.chat_widget_configuration.add_speech_to_text = request_data.is_enabled
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating speech to text option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating speech to text settings"})
                await SessionLocal.commit()
                log_message(20,f"Speech to text option in chat widget configuration updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Speech to text settings updated!"})
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while updating speech to text option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating speech to text settings"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating speech to text option in chat widget configuration! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



async def hideAttachment(request_data:HideAttachmentSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update hide attachment option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating hide attachment option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating attachment settings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.chat_widget_configuration)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating hide attachment option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating attachment settings"})
                    
                    try:
                        super_admin.chat_widget_configuration.hide_attachment = request_data.is_enabled
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating hide attachment option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating attachment settings"})
                await SessionLocal.commit()
                log_message(20,f"Hide attachment option in chat widget configuration updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Attachment settings updated!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating hide attachment option in chat widget configuration! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating attachment settings"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating hide attachment option in chat widget configuration! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})






async def greetingMessage(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view greeting message setting! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing greeting message settings! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(joinedload(User.greeting_message)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing greeting message settings! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                        
                    result_dict  =  {}
                    result_dict["greeting_message_enabled"]= super_admin.greeting_message.greeting_message_enabled
                    result_dict["message_option"]= super_admin.greeting_message.msg_option_selected
                    result_dict["options"]= {}
                    result_dict["options"]["message_option1"]= super_admin.greeting_message.msg_option_1
                    result_dict["options"]["message_option2"]= super_admin.greeting_message.msg_option_2
                    result_dict["greeting_trigger_time"]= super_admin.greeting_message.greeting_trigger_time
                    result_dict["play_notification_sound"]= super_admin.greeting_message.play_notification_sound
                    result_dict["show_greeting_on_mobile"]= super_admin.greeting_message.show_greeting_on_mobile
                    
                log_message(20,f"Greeting message settings viewed successfully! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing greeting message settings! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing greeting message settings!")
        return JSONResponse(content={"Error": "Invalid token"})




async def enableGreetingMessage(request_data:GreetingMessageSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to enable/disable greeting message setting! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while enable/disabling greeting message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating greeting message settings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.greeting_message)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while  enable/disabling greeting message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating greeting message settings"})
                    
                    try:
                        super_admin.greeting_message.greeting_message_enabled = request_data.enable_greeting_message
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object tp session while  enable/disabling greeting message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating greeting message settings"})
                await SessionLocal.commit()
                
                if request_data.enable_greeting_message == True:
                    log_message(20,f"Greeting message enabled successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Greeting message enabled!"})
                else:
                    log_message(20,f"Greeting message disabled successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Greeting message disabled!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while  enable/disabling greeting message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating greeting message settings"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while  enable/disabling greeting message settings! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})





async def editGreetingMessage(request_data:EditGreetingMessageSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to edit greeting message setting! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while  editing greeting message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating greeting message settings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.greeting_message)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while  editing greeting message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating greeting message settings"})
                    
                    try:
                        super_admin.greeting_message.msg_option_selected = request_data.message_option
                        super_admin.greeting_message.msg_option_1 = request_data.options["msg_option1"]
                        super_admin.greeting_message.msg_option_2 = request_data.options["msg_option2"]
                        super_admin.greeting_message.greeting_trigger_time = request_data.greeting_trigger_time
                        super_admin.greeting_message.play_notification_sound = request_data.play_notification_sound
                        super_admin.greeting_message.show_greeting_on_mobile = request_data.show_greeting_on_mobile
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while editing greeting message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating greeting message settings"})
                await SessionLocal.commit()
                log_message(20,f"Greeting message settings edited successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Greeting message settings updated!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while  editing greeting message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating greeting message settings"})  #Unknown error 
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while  editing greeting message settings! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})





async def preChatLeadCollection(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view pre-chat-lead collection setting! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing pre-chat-lead collection settings! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.pre_chat_lead_collection).options(
                                selectinload(PreChatLeadCollection.pre_chat_lead_collection_fields)
                            )
                            ).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing pre-chat-lead collection settings! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                        
                    result_dict  =  {}
                    result_dict["enable_pre_chat_lead_collection"] = super_admin.pre_chat_lead_collection.enable_prechat_lead
                    result_dict["pre_chat_heading"] = super_admin.pre_chat_lead_collection.prechat_lead_collection_heading
                    result_dict["pre_chat_lead_collections"] = []
                    for custom_field in super_admin.pre_chat_lead_collection.pre_chat_lead_collection_fields:
                        custom_field_dict = {}
                        custom_field_dict["id"] =  custom_field.id
                        custom_field_dict["is_mandatory"] =  custom_field.is_mandatory
                        custom_field_dict["field_type"] =  custom_field.field_type
                        custom_field_dict["field_name"] =  custom_field.field_name
                        custom_field_dict["placeholder"] =  custom_field.place_holder
                        result_dict["pre_chat_lead_collections"].append(custom_field_dict)
                        
                log_message(20,f"Pre-chat-lead collection settings viewed succcessfully! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while viewing pre-chat-lead collection settings! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing pre-chat-lead collection settings!")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    

async def enablePreChatLeadCollection(request_data:EnablePreChatLeadCollectionSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to enable/disable pre-chat-lead collection setting! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while enabling/disbling pre-chat-lead collection settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating pre-chat-lead settings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.pre_chat_lead_collection)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while enabling/disbling pre-chat-lead collection settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating pre-chat-lead settings"})
                    
                    try:
                        super_admin.pre_chat_lead_collection.enable_prechat_lead = request_data.enable_pre_chat_lead_collection
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin to session while enabling/disbling pre-chat-lead collection settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating pre-chat-lead settings"})
                    
                await SessionLocal.commit()
                if request_data.enable_pre_chat_lead_collection==True:
                    log_message(20,f"Pre-chat-lead collection settings enabled successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Pre-chat-lead settings enabled!"})
                else:
                    log_message(20,f"Pre-chat-lead collection settings disabled successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Pre-chat-lead settings disabled!"})
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while enabling/disbling pre-chat-lead collection settings! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating pre-chat-lead settings"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while enabling/disbling pre-chat-lead collection settings! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})


async def preChatHeading(request_data:PreChatHeadingSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update pre-chat-lead collection heading setting! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating pre-chat-lead collection heading setting! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating pre-chat-lead settings"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.pre_chat_lead_collection)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating pre-chat-lead collection heading setting! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating pre-chat-lead settings"})
                    
                    try:
                        super_admin.pre_chat_lead_collection.prechat_lead_collection_heading = request_data.pre_chat_heading
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating pre-chat-lead collection heading setting! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating pre-chat-lead settings"})
                await SessionLocal.commit()
                log_message(20,f"Pre-chat-lead collection heading updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Pre-chat-lead settings updated!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating pre-chat-lead collection heading setting! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating pre-chat-lead settings"}) 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating pre-chat-lead collection heading setting! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})


async def addPreChatCustomField(request_data:AddPreChatFieldSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to add pre-chat-lead custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while adding pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding pre-chat-lead custom filed"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.pre_chat_lead_collection).options(
                                selectinload(PreChatLeadCollection.pre_chat_lead_collection_fields)
                            )
                        ).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while adding pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding pre-chat-lead custom filed"})
                    
                    try:
                        pre_chat_lead_obj =  super_admin.pre_chat_lead_collection
                        
                        
                        all_prechat_objects = super_admin.pre_chat_lead_collection.pre_chat_lead_collection_fields
                        
                        check_lis = list(filter(lambda x:x.field_name==request_data.field_name,all_prechat_objects))
                        if check_lis !=[]:
                            log_message(30,str(sys.exc_info())+f"Pre-chat-lead custom filed already present while adding pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Pre-chat-lead custom filed already present"})
                            
                        
                        pre_chat_lead_field = PreChatLeadCollectionFields(
                                                    prechatlead_parent =  pre_chat_lead_obj,
                                                    is_mandatory= request_data.is_mandatory, 
                                                    field_type = request_data.field_type,
                                                    field_name = request_data.field_name,
                                                    place_holder = request_data.place_holder)
                        
                        SessionLocal.add(pre_chat_lead_field)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while adding pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding pre-chat-lead custom filed"})
                await SessionLocal.commit()
                log_message(20,f"Pre-chat-lead collection custom field added successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Pre-chat-lead custom field added successfully!"})
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while adding pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error adding pre-chat-lead custom filed"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while adding pre-chat-lead collection custom field! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})





async def editPreChatCustomField(request_data:EditPreChatFieldSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to edit pre-chat-lead custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while editing pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating pre-chat-lead custom field"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.pre_chat_lead_collection)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while editing pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating pre-chat-lead custom field"})
                    
                    try:
                    
                        all_prechat_objects = super_admin.pre_chat_lead_collection
                        
                        check_lis = list(filter(lambda x:x.id==request_data.id,all_prechat_objects))
                        
                        if check_lis ==[]:
                            log_message(30,f"There is no custom field with the requested id while editing pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating pre-chat-lead custom field"})
                        
                        prechat_obj = check_lis[0]
                        prechat_obj.is_mandatory = request_data.is_mandatory
                        prechat_obj.field_type = request_data.field_type
                        prechat_obj.field_name = request_data.field_name
                        prechat_obj.place_holder = request_data.place_holder
                        
                        check_field_name = list(filter(lambda x:x.field_name==request_data.field_name and x.id!=request_data.id,all_prechat_objects))
                        
                        if check_field_name !=[]:
                            log_message(30,f"The field name already present and cannot be duplicated while editing pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating pre-chat-lead custom field"})
                        
                        SessionLocal.add(prechat_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add prchat_obj to session while editing pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding pre-chat-lead custom field"})
                await SessionLocal.commit()
                log_message(20,f"Pre-chat-lead collection custom field edited successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Pre-chat-lead custom field updated successfully!"})
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while editing pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating pre-chat-lead custom field"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while editing pre-chat-lead collection custom field! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})




async def deletePreChatCustomField(request_data:DeletePreChatFieldSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to delete pre-chat-lead custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while deleting pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating pre-chat-lead custom field"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.pre_chat_lead_collection)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while deleting pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting pre-chat-lead custom field"})
                    
                    try:
                    
                        all_prechat_objects = super_admin.pre_chat_lead_collection
                        
                        check_lis = list(filter(lambda x:x.id==request_data.id,all_prechat_objects))
                        
                        if check_lis ==[]:
                            log_message(30,f"There is no pre-chat custom filed present to delete with this id while deleting pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error deleting pre-chat-lead custom field"}) #not present
                        
                        prechat_obj = check_lis[0]
                        await SessionLocal.delete(prechat_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add prechat_obj to session while deleting pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting pre-chat-lead custom field"})
                await SessionLocal.commit()
                log_message(20,f"Pre-chat-lead collection custom field deleted successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Pre-chat-lead custom field deleted successfully!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while deleting pre-chat-lead collection custom field! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error deleting pre-chat-lead custom field"})  #Unknown error 
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while deleting pre-chat-lead collection custom field! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})




async def awayMessage(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view away-message settings! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing away-message settings! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.away_message)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing away-message settings! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                        
                    result_dict  =  {}
                    result_dict["id"] = super_admin.away_message.id
                    result_dict["away_message_status"] = super_admin.away_message.show_away_message
                    result_dict["away_messages"] = {}
                    result_dict["away_messages"]["anonymous_users_away_message"] = {}
                    result_dict["away_messages"]["anonymous_users_away_message"]["collect_email_id"] = super_admin.away_message.collect_email_id
                    result_dict["away_messages"]["anonymous_users_away_message"]["away_message"] = super_admin.away_message.away_message_for_unknown
                    result_dict["away_messages"]["known_users_away_message"] = {}
                    result_dict["away_messages"]["known_users_away_message"]["away_message"] = super_admin.away_message.away_message_for_known
                    
                log_message(20,f"Away-message settings viewed successfully! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while viewing away-message settings! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing away-message settings!")
        return JSONResponse(content={"Error": "Invalid token"})
    




async def showAwayMessage(request_data:AwayMessageSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to enable/disable away-message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while enabling/disabling away-message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating away message settings!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.away_message)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while enabling/disabling away-message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating away message settings!"})
                    try:
                        super_admin.away_message.show_away_message = request_data.away_message_status        
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while enabling/disabling away-message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating away message settings!"})
                await SessionLocal.commit()
                if request_data.away_message_status == True:
                    log_message(20,f"Away-message enabled successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Away message enabled!"})
                else:
                    log_message(20,f"Away-message disabled successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Away message disabled!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while enabling/disabling away-message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating away message settings!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while enabling/disabling away-message settings! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    




async def collectEmailFromAnonymous(request_data:CollectEmailSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update collect-email-id from anonymous user option in away message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating collect-email-id from anonymous user option in away message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating away message settings!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.away_message)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating collect-email-id from anonymous user option in away message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating away message settings!"})
                    try:
                        super_admin.away_message.collect_email_id = request_data.collect_email_from_anonymous_users        
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating collect-email-id from anonymous user option in away message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating away message settings!"})
                await SessionLocal.commit()
                if request_data.collect_email_from_anonymous_users == True:
                    log_message(20,f"Collect-email-id from anonymous user option in away message settings enabled! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Collect email id from anonymous users enabled!"})
                else:
                    log_message(20,f"Collect-email-id from anonymous user option in away message settings enabled! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Collect email id from anonymous users disabled!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating collect-email-id from anonymous user option in away message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating away message settings!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating collect-email-id from anonymous user option in away message settings! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    




async def awayMessageForKnown(request_data:KnownUsersAwayMessageSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update away message for known users! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating away message for known users! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating away message settings!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.away_message)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating away message for known users! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating away message settings!"})
                    try:
                        super_admin.away_message.away_message_for_known = request_data.message        
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add supper_admin object to session while updating away message for known users! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating away message settings!"})
                await SessionLocal.commit()
                log_message(20,f"Away message settings for known users updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Away message for known users set successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating away message for known users! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating away message settings!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating away message for known users! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    





async def awayMessageForUnknown(request_data:UnknownUsersAwayMessageSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update away message settings for unknown users! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating away message for unknown users! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating away message settings!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.away_message)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating away message for unknown users! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating away message settings!"})
                    try:
                        super_admin.away_message.away_message_for_unknown = request_data.message        
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while updating away message for unknown users! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating away message settings!"})
                await SessionLocal.commit()
                log_message(20,f"Away message for unknown users updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Away message for anonymous users set successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating away message for unknown users! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating away message settings!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating away message for unknown users! USER:{current_user_email} INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    




async def welcomeMessage(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view welcome message settings! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing welcome message settings! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.welcome_msg_configuration)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing welcome message settings! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                        
                    result_dict  =  {}
                    result_dict["show_welcome_message"] = super_admin.welcome_msg_configuration.show_welcome_message
                    result_dict["collect_email_from_anonymous_users"] = super_admin.welcome_msg_configuration.collect_email_id
                    
                    try:
                        all_welcome_messages_query = select(WelcomeMessages).filter(WelcomeMessages.welcome_msg_config == super_admin.welcome_msg_configuration)
                        all_welcome_messages = await SessionLocal.execute(all_welcome_messages_query)
                        all_welcome_messages = all_welcome_messages.scalars().all()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch all_welcome_messages_query while viewing welcome message settings! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                        
                    result_dict["welcome_messages"] = []
                    all_categories = super_admin.welcome_msg_configuration.message_categories
                    
                    for category in all_categories:
                        category_dict = {}
                        category_dict["message_category"]= category
                        category_dict["messages"]=[]
                        category_messages = list(filter(lambda x: x.message_category==category,all_welcome_messages))
                        for message in category_messages:
                            message_dict = {}
                            message_dict["id"]=message.id
                            message_dict["message"]= message.welcome_message
                            category_dict["messages"].append(message_dict)
                        result_dict["welcome_messages"].append(category_dict)
                
                log_message(20,f"Welcome message settings viewed successfully! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing welcome message settings! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing welcome message settings! USER:{current_user_email}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
async def showWelcomeMessage(request_data:WelcomeMessageSerializer, Authorize : AuthJWT=Depends()): 
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to enable/disable welcome message to users setting! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while enabling/disabling welcome message to users setting! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating welcome message settings!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.welcome_msg_configuration)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while enabling/disabling welcome message to users setting! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating welcome message settings!"})
                    try:
                        super_admin.welcome_msg_configuration.show_welcome_message = request_data.welcome_message_status        
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while enabling/disabling welcome message to users setting! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating welcome message settings!"})
                await SessionLocal.commit()
                
                if request_data.welcome_message_status == True:
                    log_message(20,f"Welcome message to users setting enabled successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Show welcome message enabled!"})
                else:
                    log_message(20,f"Welcome message to users setting disabled successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Show welcome message disabled!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while enabling/disabling welcome message to users setting! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating welcome message settings!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while enabling/disabling welcome message to users setting! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    

async def collectEmailForWelcomeMsg(request_data:CollectEmailSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to enable/disable collect email id for anonymous users in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while enabling/disabling collect email id for anonymous users in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating welcome message settings!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.welcome_msg_configuration)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while enabling/disabling collect email id for anonymous users in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating welcome message settings!"})
                    try:
                        super_admin.welcome_msg_configuration.collect_email_id = request_data.collect_email_from_anonymous_users        
                        SessionLocal.add(super_admin)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add super_admin object to session while enabling/disabling collect email id for anonymous users in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating welcome message settings!"})
                await SessionLocal.commit()
                if request_data.collect_email_from_anonymous_users == True:
                    log_message(20,f"Collect email id for anonymous users in welcome message settings enabled successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Collect email id from anonymous users enabled!"})
                else:
                    log_message(20,f"Collect email id for anonymous users in welcome message settings disabled successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Collect email id from anonymous users disabled!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while enabling/disabling collect email id for anonymous users in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating welcome message settings!"})  
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while enabling/disabling collect email id for anonymous users in welcome message settings! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
   

async def addWelcomeMsgCategory(request_data:AddWcMsgCategorySerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to add welcome-message-category in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while adding welcome-message-category in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding welcome message language category!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.welcome_msg_configuration)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while adding welcome-message-category in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding welcome message language category!"})
                    
                    language_category = request_data.language_category
                    
                    welcome_msg_config_obj = super_admin.welcome_msg_configuration
            
                    categories=[category for category in welcome_msg_config_obj.message_categories]
                    choices=['Default', 'English', 'German', 'French','Portuguese','Spanish']
                    
                    if language_category in categories or language_category not in choices:
                        log_message(30,+f"Language category already present or wroong choice error while adding welcome-message-category in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding welcome message language category! "})
                    
                    categories.append(language_category)
                    try:
                        welcome_msg_config_obj.message_categories=categories
                        SessionLocal.add(welcome_msg_config_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add welcome_msg_config_obj to session while adding welcome-message-category in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding welcome message language category!"})
                await SessionLocal.commit()
                
                log_message(20,f"Cannot add welcome_msg_config_obj to session while adding welcome-message-category in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Welcome message language category added successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while adding welcome-message-category in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error adding welcome message language category!"}) 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while adding welcome-message-category in welcome message settings! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    

async def deleteWelcomeMsgCategory(request_data:DeleteWcMsgCategorySerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to delete welcome-message-category in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while deleting welcome-message-category in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting welcome message category!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.welcome_msg_configuration)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while deleting welcome-message-category in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting welcome message category!"})
                    
                    language_category = request_data.language_category
                    
                    welcome_msg_config_obj = super_admin.welcome_msg_configuration
            
                    categories=[category for category in welcome_msg_config_obj.message_categories]
                    choices=['Default', 'English', 'German', 'French','Portuguese','Spanish']
                    
                    if language_category not in categories or language_category not in choices:
                        log_message(30,+f"Language category not present or wroong choice error while deleting welcome-message-category in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting welcome message category! "})
                    
                    categories.remove(language_category)
                    try:
                        welcome_msg_config_obj.message_categories=categories
                        SessionLocal.add(welcome_msg_config_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add welcome_msg_config_obj to session while deleting welcome-message-category in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting welcome message category!"})
                await SessionLocal.commit()
                log_message(40,str(sys.exc_info())+f"Welcome-message-category in welcome message settings deleted successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Welcome message category deleted successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while deleting welcome-message-category in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error deleting welcome message category!"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while deleting welcome-message-category in welcome message settings! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



async def addWelcomeMessage(request_data:AddWcMsgSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to add welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while adding welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding welcome message!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.welcome_msg_configuration).options(selectinload(WelcomeMessageConfiguration.welcome_messages))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while adding welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding welcome message!"})
                    
                    language_category = request_data.language_category
                    messages = request_data.message
                    
                    welcome_msg_config_obj = super_admin.welcome_msg_configuration
                    
                    if language_category not in welcome_msg_config_obj.message_categories:
                        log_message(30,f"Language category not present while adding welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding welcome message!"}) 
                    
                    
                    try:
                        welcome_msg_objs = [WelcomeMessages(welcome_msg_config=welcome_msg_config_obj,welcome_message=wc_msg,message_category=language_category) for wc_msg in messages] 
                        SessionLocal.add_all(welcome_msg_objs)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add message_obj to session while adding welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding welcome message!"})
                await SessionLocal.commit()
                
            log_message(20,f"Welcome-message in welcome message settings added successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Welcome message added successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while adding welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error adding welcome message!"})  
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while adding welcome-message in welcome message settings!  INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})


async def editWelcomeMessage(request_data:EditWcMsgSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to edit welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while editing welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing welcome message!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.welcome_msg_configuration).options(selectinload(WelcomeMessageConfiguration.welcome_messages))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while editing welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing welcome message!"})
                    
                    
                    messages = request_data.messages
                    msg_ids = [wc_msg["id"] for wc_msg in messages]
                    
                    all_welcome_messages = super_admin.welcome_msg_configuration.welcome_messages
                    
                    welcome_message_objs = list(filter(lambda x:x.id in msg_ids,all_welcome_messages))
                    
                    if welcome_message_objs == []:
                        log_message(30,f"There is no welcome message object with requested id while editing welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing welcome message!"})
                    
                    try:
                        new_welcome_message_obj_lis = []
                        for welcome_message_obj in welcome_message_objs:
                            welcome_message_obj.welcome_message = next(wc_msg["message"] for wc_msg in messages if wc_msg["id"] == welcome_message_obj.id)
                            new_welcome_message_obj_lis.append(welcome_message_obj)
                            
                        SessionLocal.add_all(new_welcome_message_obj_lis)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add welcome_message_obj to session while editing welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing welcome message!"})
                await SessionLocal.commit()
                
                log_message(20,f"Welcome-message in welcome message settings edited successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Welcome message edited successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while editing welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error editing welcome message!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while editing welcome-message in welcome message settings!  INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})


async def deleteWelcomeMessage(request_data:DeleteWcMsgSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to delete welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while deleting welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting welcome message!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.welcome_msg_configuration).options(selectinload(WelcomeMessageConfiguration.welcome_messages))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while deleting welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting welcome message!"})
                    
                    msg_id = request_data.id
                    
                    all_welcome_messages = super_admin.welcome_msg_configuration.welcome_messages
                    
                    welcome_message_obj = list(filter(lambda x:x.id == msg_id,all_welcome_messages))
                    
                    if welcome_message_obj == []:
                        log_message(30,f"There is no welcome messge object with the requested id while deleting welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting welcome message!"})
                
                    try:
                        await SessionLocal.delete(welcome_message_obj[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot delete welcome_message_obj in session while deleting welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting welcome message!"})
                    
                await SessionLocal.commit()
                log_message(20,f"Welcome-message in welcome message settings deleted successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Welcome message deleted successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while deleting welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error deleting welcome message!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while deleting welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



async def WelcomeMessageCRud(request_data:WcMsgCrudSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to crud welcome-messages in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating welcome-message crud in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding welcome message!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.welcome_msg_configuration).options(selectinload(WelcomeMessageConfiguration.welcome_messages))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating welcome-message crud in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating welcome message!"})
                    
                    addable_message_dict = request_data.addable_messages
                    editable_message_dict = request_data.editable_messages
                    
                    welcome_msg_config_obj = super_admin.welcome_msg_configuration
                
                    #ADD WELCOME MESSAGE
                    if addable_message_dict["messages"] != []:
                        language_category = addable_message_dict["language_category"]
                        messages = addable_message_dict["messages"]
                        
                        if language_category not in welcome_msg_config_obj.message_categories:
                            log_message(30,f"Language category not present while adding welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating welcome message!"}) 
                        
                        try:
                            addable_welcome_msg_objs = [WelcomeMessages(welcome_msg_config=welcome_msg_config_obj,welcome_message=wc_msg,message_category=language_category) for wc_msg in messages] 
                            SessionLocal.add_all(addable_welcome_msg_objs)
                        except:
                            log_message(40,str(sys.exc_info())+f"Cannot add message_obj to session while adding welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error adding welcome message!"})
                    
                    #EDITING WELCOME MESSAGE
                    if editable_message_dict !=[]:
                        editable_msg_ids = [wc_msg["id"] for wc_msg in editable_message_dict]
                        
                        all_welcome_messages = welcome_msg_config_obj.welcome_messages
                        
                        welcome_message_objs = list(filter(lambda x:x.id in editable_msg_ids,all_welcome_messages))
                        
                        if welcome_message_objs == []:
                            log_message(30,f"There is no welcome message object with requested id while editing welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating welcome message!"})
                        
                        try:
                            editable_welcome_message_obj_lis = []
                            for welcome_message_obj in welcome_message_objs:
                                welcome_message_obj.welcome_message = next(wc_msg["message"] for wc_msg in editable_message_dict if wc_msg["id"] == welcome_message_obj.id)
                                editable_welcome_message_obj_lis.append(welcome_message_obj)
                            SessionLocal.add_all(editable_welcome_message_obj_lis)
                        except:
                            log_message(40,str(sys.exc_info())+f"Cannot add welcome_message_obj to session while editing welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating welcome message!"})
                    
                await SessionLocal.commit()
                
            log_message(20,f"Welcome-message in welcome message crud settings updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
            if addable_message_dict["messages"] != [] and editable_message_dict !=[]:
                response_message = "Welcome message updated successfully!"
            elif addable_message_dict["messages"] == [] and editable_message_dict !=[]:
                response_message = "Welcome message edited successfully!"
            else:
                response_message = "Welcome message created successfully!"
                
            return JSONResponse(content={"message":response_message})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while adding welcome-message in welcome message settings! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating welcome message!"})  
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating welcome-message crud in welcome message settings!  INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    


async def awayMode(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view away mode! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing away mode! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                            
                    result_dict  =  {}
                    result_dict["away_mode_status"]= current_user.is_online
                    
                log_message(20,f"Away mode viewed successfully! USER:{current_user_email}")    
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing away mode! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing away mode! USER:{current_user_email}")
        return JSONResponse(content={"Error": "Invalid token"})




async def awayModeUpdation(request_data:AwayModeSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"Changing users away mode! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating away mode! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating away mode status!"})

                    try:
                        current_user.is_online = request_data.away_mode_status
                        SessionLocal.add(current_user)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add surrent user object to session while updating away mode! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating away mode status!"})
                await SessionLocal.commit()
                
            if request_data.away_mode_status == True:
                log_message(20,f"Away mode turned on successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Away mode turned on!"}) 
            else:    
                log_message(20,f"Away mode turned off successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Away mode turned off!"})     
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while updating away mode! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error updating away mode status!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating away mode! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    
async def showHelpCenterCategories(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view Help-center-categories! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing Help-center-categories! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.help_center_category).options(selectinload(HelpCenterCategory.articles))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing Help-center-categories! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                        
                    result_dict  =  {}
                    result_dict["categories"] = []
                    for category in super_admin.help_center_category:
                        category_dict = {}
                        category_dict["category_id"]=category.id
                        category_dict["category_title"]=category.category_title
                        category_dict["category_description"]=category.category_description
                        category_dict["number_of_articles"]=len(category.articles)
                        result_dict["categories"].append(category_dict)
                log_message(20,f"Help-center-categories viewed successfully! USER:{current_user_email}")       
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing Help-center-categories! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing Help-center-categories!")
        return JSONResponse(content={"Error": "Invalid token"})


async def addHelpCenterCategory(request_data:AddHelpCenterCategorySerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject() 
        log_message(10,f"User trying to add Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while adding Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding help center category!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.help_center_category)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while adding Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding help center category!"})
                    
                    all_categories = super_admin.help_center_category
                    
                    category_check = list(filter(lambda x:x.category_title==request_data.category_title,all_categories))
                    
                    if category_check !=[]:
                        log_message(30,f"Category title aalready present while adding Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Category with this title already present!"})
                    
                    try:
                        category_obj = HelpCenterCategory(category_title=request_data.category_title,
                                                            super_admin = super_admin,
                                                            category_description = request_data.category_description,
                                                            creator_id = current_user.id,
                                                            last_edited_by = current_user.id)
                        SessionLocal.add(category_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add category_obj to session while adding Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding help center category!"})
                await SessionLocal.commit()
                log_message(20,f"Help-center-category added successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Help center category added successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while adding Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error adding help center category!"}) 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while adding Help-center-category! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})


async def editHelpCenterCategory(request_data:EditHelpCenterCategorySerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to edit Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while editing Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing help center category!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.help_center_category)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while editing Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing help center category!"})
                    
                    all_categories = super_admin.help_center_category
                    
                    category_obj = list(filter(lambda x:x.id==request_data.category_id,all_categories))
                    
                    if category_obj ==[]:
                        log_message(30,f"Catgory object not present with the requested id while editing Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing help center category!"})
                    try:
                        category_obj[0].category_title = request_data.category_title
                        category_obj[0].category_description = request_data.category_description
                        category_obj[0].last_edited_by = current_user.id
                        
                        SessionLocal.add(category_obj[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add category object to session while editing Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing help center category!"})
                await SessionLocal.commit()
                log_message(20,f"Help-center-category edited successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Help center category edited successfully!"})     
        except:
            log_message(40,str(sys.exc_info())+f"Unknown error while editing Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error editing help center category!"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while editing Help-center-category! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



async def deleteHelpCenterCategory(request_data:DeleteHelpCenterCategorySerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to delete Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while deleting Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting help center category!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.help_center_category)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while deleting Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting help center category!"})
                    
                    all_categories = super_admin.help_center_category
                    
                    category_obj = list(filter(lambda x:x.id==request_data.category_id,all_categories))
                    
                    if category_obj ==[]:
                        log_message(30,f"Categoory object not present for the requested id while deleting Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting help center category!"})
                    
                    try:
                        await SessionLocal.delete(category_obj[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add category_obj to session while deleting Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting help center category!"})
                await SessionLocal.commit()
                log_message(20,f"Help-center-category deleted successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Help center category deleted successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while deleting Help-center-category! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error deleting help center category!"}) 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while deleting Help-center-category! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



async def singleHelpCenterCategory(category_id:int , Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view single Help-center-category! USER:{current_user_email} INPUT:{'category_id':{category_id}}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing single  Help-center-category! USER:{current_user_email} INPUT:{'category_id':{category_id}}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.help_center_category).options(selectinload(HelpCenterCategory.articles))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing single  Help-center-category! USER:{current_user_email} INPUT:{'category_id':{category_id}}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                        
                    
                    category_obj = list(filter(lambda x:x.id==category_id,super_admin.help_center_category))
                    
                    if category_obj ==[]:
                        log_message(30,f"There is no category object for the requested id while viewing single  Help-center-category! USER:{current_user_email} INPUT:{'category_id':{category_id}}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                        
                    result_dict  =  {}
                    result_dict["category_id"] = category_obj[0].id
                    result_dict["category_title"] = category_obj[0].category_title
                    result_dict["category_description"] = category_obj[0].category_description
                    result_dict["total_articles"] = len(category_obj[0].articles)
                    result_dict["articles"] = []
                    
                    for article_obj in category_obj[0].articles:
                        article_dict = {}
                        article_dict["article_id"] = article_obj.id
                        article_dict["article_title"] = article_obj.article_title
                        article_dict["article_description"] = article_obj.article_description
                        article_dict["article_status"] = article_obj.status_and_visiblity
                        result_dict["articles"].append(article_dict)    
                log_message(20,f"Single help-center-category viewed successfully! USER:{current_user_email} INPUT:{'category_id':{category_id}}")          
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing single  Help-center-category! USER:{current_user_email} INPUT:{'category_id':{category_id}}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while viewing single  Help-center-category! INPUT:{'category_id':{category_id}}")
        return JSONResponse(content={"Error": "Invalid token"})


async def emptyHelpCenterArticle(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view empty help-center-article! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing empty  help-center-article! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.help_center_category).options(selectinload(HelpCenterCategory.articles))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing empty help-center-article! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                      
                    result_dict  =  {}
                    result_dict["article_status"] = "Draft"
                    result_dict["author"] = {}
                    result_dict["author"]["author_id"] = current_user.id
                    result_dict["author"]["author_first_name"] = current_user.first_name
                    result_dict["author"]["author_last_name"] = current_user.last_name
                    result_dict["categories"] = []
                    for category in super_admin.help_center_category:
                        category_dict =  {}
                        category_dict["category_id"]=category.id
                        category_dict["category_name"]=category.category_title
                        result_dict["categories"].append(category_dict)
                        
                log_message(20,f"Empty help-center-article viewed successfully! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing empty help-center-article! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing empty help-center-article!")
        return JSONResponse(content={"Error": "Invalid token"})



async def showHelpCenterArticle(request_data : ShowHelpCenterArticleSerializer ,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing  help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.help_center_category).options(selectinload(HelpCenterCategory.articles))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing  help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                        
                    category_obj = list(filter(lambda x:x.id == request_data.category_id,super_admin.help_center_category))
                    
                    if category_obj == []:
                        log_message(30,f"Category object not present for the requested id while viewing  help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                    
                    all_articles = category_obj[0].articles
                    
                    article_obj = list(filter(lambda x:x.id == request_data.article_id,all_articles))
                    
                    if article_obj == []:
                        log_message(30,f"Article object not present for the requested id while viewing  help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                    
                    result_dict  =  {}
                    result_dict["article_id"] = article_obj[0].id
                    result_dict["article_title"] = article_obj[0].article_title
                    result_dict["article_description"] = article_obj[0].article_description
                    result_dict["article_status"] = article_obj[0].status_and_visiblity
                    result_dict["careated_by"] = {}
                    result_dict["careated_by"]["creator_id"] = article_obj[0].author.id
                    result_dict["careated_by"]["first_name"] = article_obj[0].author.first_name
                    result_dict["careated_by"]["last_name"] = article_obj[0].author.last_name
                    result_dict["categories"] = []
                    for category in super_admin.help_center_category:
                        category_dict = {}
                        category_dict["category_id"]=category.id
                        category_dict["category_name"]=category.category_title
                        result_dict["categories"].append(category_dict)
                        
                log_message(20,f"Help-center-article viewed successfully! USER:{current_user_email} INPUT:{request_data.dict()}")   
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing  help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing help-center-article! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})


    


async def addHelpCenterArticle(request_data:AddHelpCenterArticleSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to add help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while adding help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding help center article!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.help_center_category).options(selectinload(HelpCenterCategory.articles))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while adding help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding help center article!"})
                    
                    all_categories = super_admin.help_center_category
                    
                    category_obj = list(filter(lambda x:x.id==request_data.category_id,all_categories))
                    
                    if category_obj ==[]:
                        log_message(30,f"Category object not present for the requested id while adding help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding help center article!"}) #category not present
                    
                    check_article = list(filter(lambda x:x.article_title==request_data.article_title,category_obj[0].articles))
                    
                    
                    if check_article !=[]:
                        log_message(30,f"Article object already present for requested title while adding help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Help center article already present with title!"}) #article already present with this title
                
                    try:
                        article_obj = HelpCenterArticle(category= category_obj[0],
                                                        article_title=request_data.article_title,
                                                        article_description = request_data.article_description,
                                                        author = current_user,
                                                        last_editor = current_user,
                                                        status_and_visiblity = request_data.status_and_visiblity)
                        SessionLocal.add(article_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add article_obj to session while adding help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding help center article!"})
                await SessionLocal.commit()
                log_message(20,f"Help-center-article added succesfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Help center category added successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while adding help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error adding help center article!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while adding help-center-article! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})


async def editHelpCenterArticle(request_data:EditHelpCenterArticleSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing help center article!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.help_center_category).options(selectinload(HelpCenterCategory.articles))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing help center article!"})
                    
                    all_categories = super_admin.help_center_category
                    
                    current_category_obj = list(filter(lambda x:x.id==request_data.category_option["current_category_id"],all_categories))
                    
                    if current_category_obj ==[]:
                        log_message(30,f"Current category object not found for requested id while updating help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing help center article!"}) #category not present
                    
                    article_obj = list(filter(lambda x:x.id==request_data.article_id,current_category_obj[0].articles))
                    
                    if article_obj ==[]:
                        log_message(30,f"Article object not found for requested id while updating help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing help center article!"}) #article not present with this id
                    
                    
                    #now check whether updated category is present or not
                    updated_category_obj = list(filter(lambda x:x.id==request_data.category_option["updated_category_id"],all_categories))
                    
                    if updated_category_obj ==[]:
                        log_message(30,f"Updated category object not found for requested id while updating help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing help center article!  "}) #category not present
                 
                 
                    article_title_check= list(filter(lambda x:x.article_title==request_data.article_title and x.id !=article_obj[0].id,updated_category_obj[0].articles))
                    
                    
                    if article_title_check != []:
                        log_message(30,f"Article with this title already present while updating help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Article with this title already present"})   #Article with this title already present
                    
                
                    try:
                        article_obj = article_obj[0]
                        article_obj.article_title = request_data.article_title
                        article_obj.article_description = request_data.article_description
                        article_obj.category = updated_category_obj[0]
                        article_obj.status_and_visibility = request_data.status_and_visibility
                        article_obj.last_editor = current_user
                        SessionLocal.add(article_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add article_obj to session while updating help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing help center article!"})
                await SessionLocal.commit()
                log_message(20,f"Help-center-article updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Help center category edited successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error editing help center article!"})  
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating help-center-article! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})


async def deleteHelpCenterArticle(request_data:DeleteHelpCenterArticleSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to delete help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while deleting help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting help center article!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.help_center_category).options(selectinload(HelpCenterCategory.articles))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while deleting help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting help center article5!"})
                    
                    all_categories = super_admin.help_center_category
                    
                    category_obj = list(filter(lambda x:x.id==request_data.category_id,all_categories))
                    
                    if category_obj ==[]:
                        log_message(40,str(sys.exc_info())+f"Category object not present for the requested id while deleting help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting help center article4!"}) #category not present
                    
                    article_obj = list(filter(lambda x:x.id==request_data.article_id,category_obj[0].articles))
                    
                    if article_obj ==[]:
                        log_message(40,str(sys.exc_info())+f"Article object not present for the requested id while deleting help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting help center article3!"}) #article not present with this id
                
                    try:
                        await SessionLocal.delete(article_obj[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add article object to session while deleting help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting help center article2!"})
                await SessionLocal.commit()
                log_message(30,f"Help-center-article deleted successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Help center category deleted successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while deleting help-center-article! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error deleting help center article1!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while deleting help-center-article! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})




async def helpCenterCustomization(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view help-center-customization! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing help-center-customization! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.help_center_customization)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing help-center-customization! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                        
                    result_dict  =  {}
                    result_dict["appearance"]={}
                    result_dict["appearance"]["customization_id"]=super_admin.help_center_customization.id
                    result_dict["appearance"]["primary_color"]=super_admin.help_center_customization.primary_color
                    result_dict["appearance"]["headline_text"]=super_admin.help_center_customization.headline_text
                    result_dict["appearance"]["searchbar_text"]=super_admin.help_center_customization.searchbar_text
                    result_dict["appearance"]["logo_image"]=super_admin.help_center_customization.logo_image.decode('utf-8') if super_admin.help_center_customization.logo_image!=None else None
                    result_dict["appearance"]["fav_icon"]=super_admin.help_center_customization.fav_icon.decode('utf-8') if super_admin.help_center_customization.fav_icon!=None else None
                    result_dict["appearance"]["show_branding"]=super_admin.help_center_customization.show_branding
                    result_dict["appearance"]["show_live_chat_in_helpcenter"]=super_admin.help_center_customization.show_live_chat_in_helpcenter
                    result_dict["settings"]={}
                    result_dict["settings"]["home_page_title"]=super_admin.help_center_customization.homepage_title
                    result_dict["settings"]["google_tag_manager_id"]=super_admin.help_center_customization.google_tag_manager_id
                    result_dict["settings"]["custom_domain_url"]=super_admin.help_center_customization.custom_domain_url
                    
                log_message(20,f"Help-center-customization viewed successfully! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing help-center-customization! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing help-center-customization!")
        return JSONResponse(content={"Error": "Invalid token"})



async def helpCenterAppearanceUpdation(request_data:HelpCenterCustomizationSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        
        image_removed_dict = request_data.dict()
        image_removed_dict["appearance"].pop("logo_image")
        image_removed_dict["appearance"].pop("fav_icon")
        
        log_message(10,f"User trying to update help-center-appearance! USER:{current_user_email} INPUT:{image_removed_dict}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating help-center-appearance! USER:{current_user_email} INPUT:{image_removed_dict}")
                        return JSONResponse(content={"Error":"Error editing help center customization!"})
                    
                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.help_center_customization)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating help-center-appearance! USER:{current_user_email} INPUT:{image_removed_dict}")
                        return JSONResponse(content={"Error":"Error editing help center customization!"})
                    
                    try:
                        help_center_cust_obj = super_admin.help_center_customization
                        help_center_cust_obj.primary_color = request_data.appearance["primary_color"]
                        help_center_cust_obj.headline_text = request_data.appearance["headline_text"]
                        help_center_cust_obj.searchbar_text = request_data.appearance["searchbar_text"]
                        if checkImageSize(request_data.appearance["logo_image"],20) == True:
                            help_center_cust_obj.logo_image = request_data.appearance["logo_image"].encode('utf-8')
                        else:
                            log_message(30,str(sys.exc_info())+f"Image size cannot be more than 20KB while updating help center customization logo image icon! USER:{current_user_email} INPUT:{image_removed_dict}")
                            return JSONResponse(content={"Error":"Image size cannot be more than 20KB"})
                        
                        if checkImageSize(request_data.appearance["fav_icon"],20) == True:
                            help_center_cust_obj.fav_icon = request_data.appearance["fav_icon"].encode('utf-8')
                        else:
                            log_message(30,str(sys.exc_info())+f"Image size cannot be more than 20KB while updating help center customization fav icon! USER:{current_user_email} INPUT:{image_removed_dict}")
                            return JSONResponse(content={"Error":"Image size cannot be more than 20KB"})
                        
                        
                        
                        
                        help_center_cust_obj.show_branding = request_data.appearance["show_branding"]
                        help_center_cust_obj.show_live_chat_in_helpcenter = request_data.appearance["show_live_chat_in_helpcenter"]
                        
                        help_center_cust_obj.homepage_title = request_data.settings["homepage_title"]
                        help_center_cust_obj.google_tag_manager_id = request_data.settings["google_tag_manager_id"]

                        SessionLocal.add(help_center_cust_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add help_center_cust_obj object to session while updating help-center-appearance! USER:{current_user_email} INPUT:{image_removed_dict}")
                        return JSONResponse(content={"Error":"Error editing help center customization!"})
                await SessionLocal.commit()
                log_message(20,f"Help-center-appearance updated successfully! USER:{current_user_email} INPUT:{image_removed_dict}")
                return JSONResponse(content={"message":"Help center customization edited successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating help-center-appearance! USER:{current_user_email} INPUT:{image_removed_dict}")
            return JSONResponse(content={"message":"Error editing help center customization!"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating help-center-appearance! INPUT:{image_removed_dict}")
        return JSONResponse(content={"Error": "Invalid token"})



async def helpCenterCustomDomainUrl(request_data:HelpCenterDomainUrlSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update help-center custom domain url! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating help-center custom domain url! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing help center custom domain url!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.help_center_customization)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating help-center custom domain url! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing help center custom domain url!"})
                    
                    try:
                        help_center_cust_obj = super_admin.help_center_customization
                        help_center_cust_obj.custom_domain_url = request_data.custom_domain_url
                        SessionLocal.add(help_center_cust_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add help_center_cust_obj to session while updating help-center custom domain url! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing help center custom domain url!"})
                await SessionLocal.commit()
                log_message(20,f"Help-center custom domain url updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Help center custom domain url updated successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating help-center custom domain url! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Error editing help center custom domain uurl!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating help-center custom domain url! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



async def manageAllBots(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view manage all bots list! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing manage all bots list! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.default_team).options(selectinload(DefaultTeam.bots))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing manage all bots list! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                      
                    all_bots =list(filter(lambda x:x.is_active==True,super_admin.default_team.bots))
                    result_dict  =  {}
                    result_dict["all_bots"]=[]
                    for bot in all_bots:
                        bot_dict={}
                        bot_dict["bot_id"] = bot.id
                        bot_dict["bot_name"] = bot.bot_name
                        bot_dict["bot_platform"] = bot.integration_platform
                        bot_dict["bot_photo"]= str(bot.bot_photo.decode('utf-8')) if bot.bot_photo!=None else None
                        result_dict["all_bots"].append(bot_dict)
                        
                log_message(20,f"Manage all bots list viewed successfully! USER:{current_user_email}")
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing manage all bots list! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing manage all bots list!")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    
    



async def showSingleBot(bot_id : int , Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view single bot! USER:{current_user_email} INPUT:{'bot_id':{bot_id}}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing single bot! USER:{current_user_email} INPUT:{'bot_id':{bot_id}}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.default_team).options(selectinload(DefaultTeam.bots).options(
                            selectinload(Bot.dialogflow_es)
                            ))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing single bot! USER:{current_user_email} INPUT:{'bot_id':{bot_id}}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                      
                    selected_bot =list(filter(lambda x:x.id==bot_id and x.is_active==True,super_admin.default_team.bots))
                    
                    if selected_bot == []:
                        log_message(30,f"Bot not present with the requested id while viewing single bot! USER:{current_user_email} INPUT:{'bot_id':{bot_id}}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"}) #there is not bot with this id
                    
                    selected_bot = selected_bot[0]
                    
                    result_dict  =  {}
                    result_dict["bot_info"] = {}
                    result_dict["bot_info"]["bot_id"] = selected_bot.id
                    result_dict["bot_info"]["bot_name"] = selected_bot.bot_name
                    result_dict["bot_info"]["bot_photo"] = str(selected_bot.bot_photo.decode('utf-8')) if selected_bot.bot_photo!=None else None
                    result_dict["bot_info"]["allow_human_handoff"] = selected_bot.allow_human_handoff

                    result_dict["integration_info"] = {}
                    
                    if selected_bot.integration_platform == 'Dialogflow-ES':
                        result_dict["integration_info"]["bot_platform"] = selected_bot.integration_platform
                        result_dict["integration_info"]["integration_platform_id"] = selected_bot.dialogflow_es.id
                        result_dict["integration_info"]["private_key_file"] = "key_file_uploaded" if selected_bot.dialogflow_es.dialogflow_private_key!=None else "no_key_file"
                        result_dict["integration_info"]["default_language"] = selected_bot.dialogflow_es.default_language
                        result_dict["integration_info"]["default_region"] = selected_bot.dialogflow_es.default_region
                        result_dict["integration_info"]["default_knowledge_base_id"] = selected_bot.dialogflow_es.dialogflow_knowledge_base_id
                        
                log_message(20,f"Single bot details viewed succesfully! USER:{current_user_email} INPUT:{'bot_id':{bot_id}}")        
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing single bot! USER:{current_user_email} INPUT:{'bot_id':{bot_id}}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing single bot! INPUT:{'bot_id':{bot_id}}")
        return JSONResponse(content={"Error": "Invalid token"})
    


async def editBotProfile(request_data: EditBotProfileSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update bot profile! USER:{current_user_email} INPUT: bot_id:{request_data.bot_id}, bot_name:{request_data.bot_name}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating bot profile! USER:{current_user_email} INPUT:bot_id:{request_data.bot_id}, bot_name:{request_data.bot_name}")
                        return JSONResponse(content={"Error":"Error updating bot-profile!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.default_team).options(selectinload(DefaultTeam.bots).options(
                            selectinload(Bot.dialogflow_es)
                            ))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating bot profile! USER:{current_user_email} INPUT:bot_id:{request_data.bot_id}, bot_name:{request_data.bot_name}")
                        return JSONResponse(content={"Error":"Error updating bot-profile!"})
                      
                    selected_bot =list(filter(lambda x:x.id==request_data.bot_id,super_admin.default_team.bots))
                    
                    if selected_bot == []:
                        log_message(30,f"Bot not present for the requested id while updating bot profile! USER:{current_user_email} INPUT:bot_id:{request_data.bot_id}, bot_name:{request_data.bot_name}")
                        return JSONResponse(content={"Error":"Error updating bot-profile!"}) #there is not bot with this id
                    
                    try: 
                        selected_bot[0].bot_name = request_data.bot_name
                        selected_bot[0].bot_photo = request_data.bot_photo.encode('utf-8')  
                        SessionLocal.add(selected_bot[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add selected_bot object to session while updating bot profile! USER:{current_user_email} INPUT:bot_id:{request_data.bot_id}, bot_name:{request_data.bot_name}")
                        return JSONResponse(content={"Error":"Error updating bot-profile!"})
                    
                await SessionLocal.commit()     
                log_message(20,f"Bot-Profile updated successfully! USER:{current_user_email} INPUT:bot_id:{request_data.bot_id}, bot_name:{request_data.bot_name}")   
                return JSONResponse(content={"message":"Bot-Profile updated successfully!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating bot profile! USER:{current_user_email} INPUT:bot_id:{request_data.bot_id}, bot_name:{request_data.bot_name}")
            return JSONResponse(content={"Error":"Error updating bot-profile!"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating bot profile! INPUT:bot_id:{request_data.bot_id}, bot_name:{request_data.bot_name}")
        return JSONResponse(content={"Error": "Invalid token"})





async def editBotHumanHandoff(request_data: EditBotHumanHandoffSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update bot human-handoff option! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating bot human-handoff option! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating human handoff settings!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.default_team).options(selectinload(DefaultTeam.bots).options(
                            selectinload(Bot.dialogflow_es)
                            ))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating bot human-handoff option! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating human handoff settings!"})
                      
                    selected_bot =list(filter(lambda x:x.id==request_data.bot_id,super_admin.default_team.bots))
                    
                    if selected_bot == []:
                        log_message(30,f"Bot nott present for the requested id while updating bot human-handoff option! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating human handoff settings!"}) #there is not bot with this id
                    
                    try: 
                        selected_bot[0].allow_human_handoff = request_data.allow_human_handoff
                        
                        if selected_bot[0].is_active == False:
                            selected_bot[0].is_active = True
                            
                        SessionLocal.add(selected_bot[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add selected_bot to session while updating bot human-handoff option! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating human handoff settings!"})
                await SessionLocal.commit()     
            if request_data.allow_human_handoff == True:
                log_message(20,f"Bot human-handoff option enabled successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Allow human hand-off settings enabled!"})
            else:
                log_message(20,f"Bot human-handoff option disabled successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Allow human hand-off settings disabled!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating bot human-handoff option! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error updating human handoff settings!!"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating bot human-handoff option! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})




async def deleteBot(bot_id: int, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to delete the bot! USER:{current_user_email} INPUT:{'bot_id':{bot_id}}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while deleting the bot! USER:{current_user_email} INPUT:{'bot_id':{bot_id}}")
                        return JSONResponse(content={"Error":"Error deleting the bot"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.default_team).options(selectinload(DefaultTeam.bots).options(
                            selectinload(Bot.dialogflow_es)
                            ))).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while deleting the bot! USER:{current_user_email} INPUT:{'bot_id':{bot_id}}")
                        return JSONResponse(content={"Error":"Error deleting the bot"})
                      
                    selected_bot =list(filter(lambda x:x.id==bot_id,super_admin.default_team.bots))
                    
                    if selected_bot == []:
                        log_message(30,f"Bot not present for the requested id while deleting the bot! USER:{current_user_email} INPUT:{'bot_id':{bot_id}}")
                        return JSONResponse(content={"Error":"Error deleting the bot"}) #there is not bot with this id
                    
                    try:  
                        selected_bot[0].is_active=False
                        SessionLocal.add(selected_bot[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add selected_bot to session while deleting the bot! USER:{current_user_email} INPUT:{'bot_id':{bot_id}}")
                        return JSONResponse(content={"Error":"Error deleting the bot!"})
                await SessionLocal.commit()     
                log_message(20,f"Bot deleted successfully! USER:{current_user_email} INPUT:{'bot_id':{bot_id}}")        
                return JSONResponse(content={"message":"Bot Deleted Successfully!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while deleting the bot! USER:{current_user_email} INPUT:{'bot_id':{bot_id}}")
            return JSONResponse(content={"Error":"Error deleting the bot"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while deleting the bot! INPUT:{'bot_id':{bot_id}}")
        return JSONResponse(content={"Error": "Invalid token"})
    


async def dialogflowESBotIntegration(request_data:DialogFlowESSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to integrate Dialogflow ES bot! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while integrating Dialogflow ES bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error integrating the bot!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.default_team)
                            ).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while integrating Dialogflow ES bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error integrating the bot!"})
                    
                    try:
                        new_bot_obj = Bot(
                                        created_user = current_user,
                                        integration_platform = 'Dialogflow-ES',
                                        default_team = super_admin.default_team,
                                        dialogflow_es = DialogFlowES(dialogflow_private_key= request_data.private_key_file,
                                                                    default_language = request_data.default_bot_language,
                                                                    default_region = request_data.dialogflow_region,
                                                                    dialogflow_knowledge_base_id = request_data.dialogflow_knowledge_base_id)
                                        )
                        
                        SessionLocal.add(new_bot_obj)
                        await SessionLocal.flush()
                        bot_id = new_bot_obj.id
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add new_bot_obj to session while integrating Dialogflow ES bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error integrating the bot!"})
                await SessionLocal.commit()
                log_message(20,f"Dialogflow ES bot integrated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Bot integrated successfully!" , "bot_id":bot_id})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while integrating Dialogflow ES bot! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error integrating the bot!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while integrating Dialogflow ES bot! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    

async def dialogflowESSetupEdition(request_data: DialogFlowESUpdateSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update Dialogflow ES bot! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating Dialogflow ES bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the bot!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.default_team).options(selectinload(DefaultTeam.bots).selectinload(Bot.dialogflow_es))
                            ).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating Dialogflow ES bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the bot!"})
                    
                    bot_obj = list(filter(lambda x:x.id == request_data.bot_id,super_admin.default_team.bots))
                    
                    if  bot_obj == []:
                        log_message(30,f"Bot not present with the requested id while updating Dialogflow ES bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the bot!"}) #There is no bot
                    
                    if bot_obj[0].integration_platform != 'Dialogflow-ES':
                        log_message(30,f"Requested bots integration platform is not Dialogflow-ES while updating Dialogflow ES bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the bot!"}) #Other integration bots cannot be updated
                    try:
                        bot_obj[0].dialogflow_es.dialogflow_private_key = request_data.private_key_file
                        bot_obj[0].dialogflow_es.default_language = request_data.default_bot_language
                        bot_obj[0].dialogflow_es.default_region = request_data.dialogflow_region
                        bot_obj[0].dialogflow_es.dialogflow_knowledge_base_id = request_data.dialogflow_knowledge_base_id
                        SessionLocal.add(bot_obj[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add bot_obj to session while updating Dialogflow ES bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the bot!"})
                await SessionLocal.commit()
                log_message(20,f"Dialogflow ES bot updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Bot updated successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating Dialogflow ES bot! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error updating the bot!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating Dialogflow ES bot! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    




async def dialogflowCXBotIntegration(request_data : DialogFlowCXSerializer ,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to integrate Dialogflow CX bot! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while integrating Dialogflow CX bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error integrating the bot!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.default_team)
                            ).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while integrating Dialogflow CX bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error integrating the bot!"})
                    
                    try:
                        new_bot_obj = Bot(
                                        created_user = current_user,
                                        integration_platform = 'Dialogflow-CX',
                                        default_team = super_admin.default_team,
                                        dialogflow_cx = DialogFlowCX(
                                            dialogflow_private_key= request_data.private_key_file,
                                            default_region = request_data.dialogflow_region,
                                            agent_id = request_data.agent_id
                                            )
                                        )
                        
                        SessionLocal.add(new_bot_obj)
                        await SessionLocal.flush()
                        bot_id = new_bot_obj.id
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add new_bot_obj to session while integrating Dialogflow CX bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error integrating the bot!"})
                await SessionLocal.commit()
                log_message(20,f"Dialogflow CX bot integrated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Bot integrated successfully!" , "bot_id":bot_id})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while integrating Dialogflow CX bot! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error integrating the bot!"}) 
    except:
        log_message(50,str(sys.exc_info())+f"Invalid token error while integrating Dialogflow CX bot! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})




async def dialogflowCXSetupEdition(request_data:DialogFlowCXUpdateSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to update Dialogflow CX bot! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while updating Dialogflow CX bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the bot!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.default_team).options(selectinload(DefaultTeam.bots).selectinload(Bot.dialogflow_cx))
                            ).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating Dialogflow CX bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the bot!"})
                    
                    bot_obj = list(filter(lambda x:x.id == request_data.bot_id,super_admin.default_team.bots))
                    
                    if  bot_obj == []:
                        log_message(30,f"Bot object not present for the requested id while updating Dialogflow CX bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the bot!"}) #There is no bot

                    if bot_obj[0].integration_platform != 'Dialogflow-CX':
                        log_message(30,f"Requested bot's integration platfor is not Dialogflow CX while updating Dialogflow CX bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the bot!"}) #Other integration bots cannot be updated
                
                    try:
                        bot_obj[0].dialogflow_cx.dialogflow_private_key = request_data.private_key_file
                        bot_obj[0].dialogflow_cx.default_region = request_data.dialogflow_region
                        bot_obj[0].dialogflow_cx.agent_id = request_data.agent_id
                        SessionLocal.add(bot_obj[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add bot_obj to session while updating Dialogflow CX bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the bot!"})
                await SessionLocal.commit()
                log_message(30,f"Dialogflow CX bot updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Bot updated successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating Dialogflow CX bot! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error updating the bot!"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating Dialogflow CX bot! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})




async def customPlatformBotIntegration(request_data: CustomPlatformSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to integrate Custom bot platform! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while integrating Custom bot platform! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error integrating the bot!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.default_team)
                            ).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while integrating Custom bot platform! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error integrating the bot!"})
                    
                    try:
                        new_bot_obj = Bot(
                                        created_user = current_user,
                                        integration_platform = 'Custom-Platform',
                                        default_team = super_admin.default_team,
                                        custom_bot_platform = CustomBotPlatform(
                                            webhook_url= request_data.webhook_url,
                                            header_key = request_data.header_key,
                                            header_value = request_data.header_value,
                                            platform_name = request_data.platform_name
                                            )
                                        )
                        
                        SessionLocal.add(new_bot_obj)
                        await SessionLocal.flush()
                        bot_id = new_bot_obj.id
                    except: 
                        log_message(40,str(sys.exc_info())+f"Cannot add new_bot_obj to session while integrating Custom bot platform! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error integrating the bot!"})
                await SessionLocal.commit()
                log_message(20,f"Custom bot platform integrated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Bot integrated successfully!" , "bot_id":bot_id})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while integrating Custom bot platform! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error integrating the bot!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while integrating Custom bot platform! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



 

async def customPlatformSetupEdition(request_data: CustomPlatformUpdateSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to edit Custom bot platform! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while editing Custom bot platform! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the bot!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.default_team).options(selectinload(DefaultTeam.bots).selectinload(Bot.custom_bot_platform))
                            ).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while editing Custom bot platform! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the bot!"})
                    
                    bot_obj = list(filter(lambda x:x.id == request_data.bot_id,super_admin.default_team.bots))
                    
                    if  bot_obj == []:
                        log_message(30,f"Bot not present for requested id while editing Custom bot platform! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the bot!"}) #There is no bot

                    if bot_obj[0].integration_platform != 'Custom-Platform':
                        log_message(30,f"Requested bot's  integration platform is not Custom bot platform while editing Custom bot platform! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the bot!"}) #Other integration bots cannot be updated
                
                    try:
                        bot_obj[0].custom_bot_platform.webhook_url = request_data.webhook_url
                        bot_obj[0].custom_bot_platform.header_key = request_data.header_key
                        bot_obj[0].custom_bot_platform.header_value = request_data.header_value
                        SessionLocal.add(bot_obj[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add bot_obj to session while editing Custom bot platform! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the bot!"})
                await SessionLocal.commit()
                log_message(20,f"Custom platform Bot updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Bot updated successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while editing Custom bot platform! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error updating the bot!"})  
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while editing Custom bot platform! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})







    
    


async def allCustomers(number_of_users:int,page_number:int,sort_column:str,reverse:bool,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view all customers! USER:{current_user_email} INPUT:{number_of_users},{page_number},{sort_column},{reverse}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing all customers! USER:{current_user_email} INPUT:{number_of_users},{page_number},{sort_column},{reverse}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                        
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.all_customers).options(
                                selectinload(Customers.conversation).options(
                                    selectinload(Conversation.assigned_bot),
                                    selectinload(Conversation.assigned_agent)
                                    )
                                )).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing all customers! USER:{current_user_email} INPUT:{number_of_users},{page_number},{sort_column},{reverse}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                    
                                            
                    all_customers = list(filter(lambda x:x.is_deleted == False,super_admin.all_customers))
                    all_customers.sort(key=operator.attrgetter(sort_column), reverse=reverse)
                    
                    
                    
                    start_slice=(page_number - 1) * number_of_users 
                    end_slice=number_of_users*page_number
                    
                    all_customers = all_customers[start_slice:end_slice]
                    
                    
                    
                    result_dict = {}
                    result_dict["all_customers"]=[]
                    for customer in all_customers:
                        customer_dict={}
                        customer_dict["customer_id"] = customer.customer_generated_name
                        customer_dict["got_real_name"] = customer.got_real_name
                        customer_dict["customer_name"] = customer.customer_real_name
                        customer_dict["last_seen"] = "4 hrs ago (Redis server)"
                        customer_dict["created_time"] = str(customer.created_time)
                        customer_dict["is_blocked"] = customer.is_blocked
                        customer_dict["latest_conversation"] = {}
                        
                        sorted_conv_list = sorted(customer.conversation, key=lambda x: x.created_time, reverse=True)
                        
                        latest_conversation = sorted_conv_list[0]
                        customer_dict["latest_conversation"]["conversation_status"] = latest_conversation.end_user_conversation_status

                        if latest_conversation.conversation_handler == "BOT":
                            customer_dict["latest_conversation"]["conversation_handler"] = "BOT"
                            customer_dict["latest_conversation"]["conversation_agent"] = {}
                            customer_dict["latest_conversation"]["conversation_agent"]["assignee_id"] = latest_conversation.assigned_bot_id
                            customer_dict["latest_conversation"]["conversation_agent"]["assignee_name"] = latest_conversation.assigned_bot.bot_name
                        else:
                            customer_dict["latest_conversation"]["conversation_handler"] = "HUMAN"
                            customer_dict["latest_conversation"]["conversation_agent"] = {}
                            customer_dict["latest_conversation"]["conversation_agent"]["assignee_id"] =latest_conversation.assigned_agent_id
                            if latest_conversation.assigned_agent.last_name !=None:
                                customer_dict["latest_conversation"]["conversation_agent"]["assignee_name"] =latest_conversation.assigned_agent.first_name + latest_conversation.assigned_agent.last_name
                            else:
                                customer_dict["latest_conversation"]["conversation_agent"]["assignee_name"] =latest_conversation.assigned_agent.first_name 
                        
                        result_dict["all_customers"].append(customer_dict)
                        
                log_message(20,f"All customers viewed successfully! USER:{current_user_email} INPUT:{number_of_users},{page_number},{sort_column},{reverse}")
                return JSONResponse(content=result_dict) 
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing all customers! USER:{current_user_email} INPUT:{number_of_users},{page_number},{sort_column},{reverse}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing all customers! INPUT:{number_of_users},{page_number},{sort_column},{reverse}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    

async def customerConversations(customer_id:str):
    async with settings.SessionLocal as SessionLocal:
        async with SessionLocal.begin_nested():
            try:
                customer_query = select(Customers).options(selectinload(Customers.conversation)).filter(Customers.customer_generated_name==customer_id)
                customer = await SessionLocal.execute(customer_query)
                customer = customer.scalars().first()
            except:
                log_message(40,str(sys.exc_info())+f"Couldn't fetch customer_query while viewing customer conversations! CUSTOMER_ID:{customer_id}")
                return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

            conversations=[{"conv_id":conv.conversation_uuid,"status":conv.end_user_conversation_status} for conv in customer.conversation]
        log_message(20,f"Customer conversations viewed successfully! CUSTOMER_ID:{customer_id}")
        return {"customer_covs":conversations}



async def getCurrentCustomer(customer_info: Optional[str] = Cookie(None)):
    customer_info = json.loads(customer_info)
    log_message(20,f"Got current customer successfully! CUSTOMER_ID:{customer_info['id']}")
    return JSONResponse(content=customer_info)


async def deleteCustomer(request_data: DeleteCustomerSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to delete customer! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while deleting a customer! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting the customer!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.all_customers)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while deleting a customer! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting the customer!"})
                    
                    try:
                        customer_obj = list(filter(lambda x:x.customer_generated_name==request_data.customer_id,super_admin.all_customers))
                        
                        if customer_obj == []:
                            log_message(30,f"Customer object for the requested id not present while deleting a customer! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error deleting the customer!"})    
                        
                        if customer_obj[0].is_deleted == True: 
                            log_message(30,f"Customer object for the requested id is already deleted while deleting a customer! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error deleting the customer!"}) 
                        else:      
                            customer_obj[0].is_deleted = True           
                            SessionLocal.add(customer_obj[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add customer_obj to session while deleting a customer! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error deleting the customer!"})
                await SessionLocal.commit()
                log_message(20,f"Customer deleted successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Customer deleted successfully!"})     
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while deleting a customer! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error deleting the customer!"})   
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while deleting a customer! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})

    
async def blockCustomer(request_data: BlockCustomerSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to block customer! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while blocking a customer! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating block status of the customer!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.all_customers)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while blocking a customer! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating block status of the customer!"})
                    
                    try:
                        customer_obj = list(filter(lambda x:x.customer_generated_name==request_data.customer_id and x.is_deleted==False,super_admin.all_customers))
                        
                        if customer_obj == []:
                            return JSONResponse(content={"Error":"Error updating block status of the customer!"})    
                        
                        
                        customer_obj[0].is_blocked = request_data.block           
                        SessionLocal.add(customer_obj[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add customer_obj to session while blocking a customer! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating block status of the customer!"})
                await SessionLocal.commit()
                if request_data.block == True:
                    log_message(20,f"Customer blocked successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Customer blocked successfully!"})     
                else:
                    log_message(20,f"Customer unblocked successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                    return JSONResponse(content={"message":"Customer unblocked successfully!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while blocking a customer! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error updating block status of the customer!"})  
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while blocking a customer! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
                   


async def addCustomerEmail(request_data: AddCustomerEmailSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to add customer email! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while adding customer email! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating customer email!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.all_customers)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while adding customer email! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating customer email!"})
                    
                    try:
                        customer_obj = list(filter(lambda x:x.customer_generated_name==request_data.customer_id and x.is_deleted==False,super_admin.all_customers))
                        
                        if customer_obj == []:
                            log_message(30,f"Customer objevt not found for requested id while adding customer email! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating customer email!"})    
                        
                        
                        customer_obj[0].customer_email = request_data.email           
                        SessionLocal.add(customer_obj[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add customer_obj to session while adding customer email! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating customer email!"})
                await SessionLocal.commit()
                log_message(20,f"Customer email updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Customer email updated successfully!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while adding customer email! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error updating customer email!"}) 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while adding customer email! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})


async def addCustomerRealname(request_data: AddCustomerRealnameSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to add customer real name! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while adding customer real name! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating customer name!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.all_customers)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while adding customer real name! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating customer name!"})
                    
                    try:
                        customer_obj = list(filter(lambda x:x.customer_generated_name==request_data.customer_id and x.is_deleted==False,super_admin.all_customers))
                        
                        if customer_obj == []:
                            log_message(30,f"Customer object not present for the requested id while adding customer real name! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating customer name!"})    
                        
                        customer_obj[0].customer_real_name = request_data.name           
                        SessionLocal.add(customer_obj[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add  customer_obj to session while adding customer real name! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating customer name!"})
                    
                await SessionLocal.commit()
                log_message(20,f"Customer real name updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Customer name updated successfully!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while adding customer real name! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error updating customer name!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while adding customer real name! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})




async def addCustomerPhoneNumber(request_data: AddCustomerPhoneSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to add customer phone number! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while adding customer phone number! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating customer phone number!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        super_admin_query = select(User).options(selectinload(User.all_customers)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while adding customer phone number! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating customer phone number!"})
                    
                    try:
                        customer_obj = list(filter(lambda x:x.customer_generated_name==request_data.customer_id and x.is_deleted==False,super_admin.all_customers))
                        
                        if customer_obj == []:
                            log_message(30,f"Customer object not found for the requested id while adding customer phone number! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error updating customer phone number!"})    
                        
                        customer_obj[0].customer_phone_number = request_data.phone           
                        SessionLocal.add(customer_obj[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add customer_obj to session while adding customer phone number! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating customer phone number!"})
                await SessionLocal.commit()
                log_message(20,f"Customer phone number updated successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Customer phone number updated successfully!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while adding customer phone number! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error updating customer phone number!"})  
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while adding customer phone number! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})


    


async def allConversations(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view all conversations list! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing all conversations list! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else: 
                        super_admin_id = current_user.super_admin_id
                    try:
                        # here we fetch the conversations of last 30 days
                        all_account_conversations_query= select(Conversation).options(
                            selectinload(Conversation.conversation_tags).options(selectinload(ConversationTags.tag)),
                            selectinload(Conversation.customer),
                            selectinload(Conversation.all_chats)).filter(
                                Conversation.super_admin_id==super_admin_id,
                                Conversation.conversation_deleted==False,
                                Conversation.created_time>=settings.conversation_time                        
                            )
                        all_account_conversations = await SessionLocal.execute(all_account_conversations_query)
                        all_account_conversations = all_account_conversations.scalars().all()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch all_account_conversations_query while viewing all conversations list! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource!"})
                    
                    
                    
                    # ---------------------- ASSIGNED CONVERSATIONS -------------------------
                    assigned_conversations = list(filter(
                        lambda x:x.conversation_handler=='HUMAN' 
                        and x.assigned_agent==current_user 
                        and x.end_user_conversation_status in ['Open'],
                        all_account_conversations))
                    
                                            
                        
                    #----------------------------   ALL CONVERSATIONS ------------------------
                    all_conversations = list(filter(
                        lambda x:x.end_user_conversation_status in ['Open','First-response-pending'],
                        all_account_conversations))
                    
                    
                    
                    #RESOLVED CONVERSATIONS
                    resolved_conversations = list(filter(
                        lambda x:x.end_user_conversation_status in ['Resolved','Spam'],
                        all_account_conversations))
                    
                    

                    conversations = [assigned_conversations,all_conversations,resolved_conversations]
                    result_dict = {}
                    
                    for i in range(len(conversations)):
                        if i == 0:
                            result_dict["assigned_conversations"]=[]
                            conv_part = "assigned_conversations"
                            conversation_part =conversations[i]
                        
                        if i == 1:
                            result_dict["all_conversations"]=[]
                            conv_part = "all_conversations"
                            conversation_part = conversations[i]
                        
                        if i == 2:
                            result_dict["resolved_conversations"]=[]
                            conv_part = "resolved_conversations"
                            conversation_part = conversations[i]
                        
                        
                        for conversation in conversation_part:
                            conversation_dict = {}
                            conversation_dict["conversation_id"] = conversation.conversation_uuid
                            conversation_dict["conversation_handler"] = conversation.conversation_handler
                            conversation_dict["customer"] = {}
                            conversation_dict["customer"]["customer_id"] = conversation.customer.id
                            if conversation.customer.got_real_name==True:
                                customer_name = conversation.customer.customer_real_name
                            else:
                                customer_name=conversation.customer.customer_generated_name
                            conversation_dict["customer"]["customer_name"] = customer_name
                            conversation_dict["conversation_status"] = conversation.end_user_conversation_status
                            conversation_dict["manually_assigned"] = conversation.conversation_manually_assigned
                            conversation_dict["tags"] = []
                            for conv_tag_obj in conversation.conversation_tags:
                                tag_obj_dict = {}
                                tag_obj_dict["tag_id"]=conv_tag_obj.tag.id
                                tag_obj_dict["tag_name"]=conv_tag_obj.tag.tag_name
                                conversation_dict["tags"].append(tag_obj_dict)
                                
                            conversation_dict["messages"]=[]  
                            for chat_obj in conversation.all_chats:
                                chat_obj_dict = {}
                                chat_obj_dict["chat_id"]=chat_obj.id
                                chat_obj_dict["response"]=json.loads(chat_obj.response)
                                chat_obj_dict["created_time"]=str(chat_obj.created_time)
                                conversation_dict["messages"].append(chat_obj_dict) 
                                
                            conversation_dict["last_message_time"] = conversation_dict["messages"][-1]["created_time"]
                                
                            result_dict[conv_part].append(conversation_dict)
                            
                log_message(20,f"All conversations list viewed successfully! USER:{current_user_email}")                  
                return JSONResponse(content=result_dict) 
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing all conversations list! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource!"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing all conversations list!")
        return JSONResponse(content={"Error": "Invalid token"})
    
     
     
     
async def resolvedConversations(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view resolved conversations list! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing all conversations list! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else: 
                        super_admin_id = current_user.super_admin_id
                    try:
                        # here we fetch the conversations of last 30 days
                        all_account_conversations_query= select(Conversation).options(
                            selectinload(Conversation.conversation_tags).options(selectinload(ConversationTags.tag)),
                            selectinload(Conversation.customer)).filter(
                                Conversation.super_admin_id==super_admin_id,
                                Conversation.conversation_deleted==False,
                                Conversation.created_time>=settings.conversation_time                        
                            )
                        all_account_conversations = await SessionLocal.execute(all_account_conversations_query)
                        all_account_conversations = all_account_conversations.scalars().all()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch all_account_conversations_query while viewing all conversations list! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource!"})
                    
                    #RESOLVED CONVERSATIONS
                    resolved_conversations = list(filter(
                        lambda x:x.end_user_conversation_status in ['Resolved','Spam'],
                        all_account_conversations))
                    
                    

                    result_dict = {}
                    result_dict["resolved_conversations"]=[]
                    
                    for conversation in resolved_conversations:
                        conversation_dict = {}
                        conversation_dict["conversation_id"] = conversation.conversation_uuid
                        conversation_dict["conversation_handler"] = conversation.conversation_handler
                        conversation_dict["customer"] = {}
                        conversation_dict["customer"]["customer_id"] = conversation.customer.id
                        if conversation.customer.got_real_name==True:
                            customer_name = conversation.customer.customer_real_name
                        else:
                            customer_name=conversation.customer.customer_generated_name
                        conversation_dict["customer"]["customer_name"] = customer_name
                        conversation_dict["conversation_status"] = conversation.end_user_conversation_status
                        conversation_dict["manually_assigned"] = conversation.conversation_manually_assigned
                        conversation_dict["last_message_time"] = "12:50 PM"
                        conversation_dict["tags"] = []
                        for conv_tag_obj in conversation.conversation_tags:
                            tag_obj_dict = {}
                            tag_obj_dict["tag_id"]=conv_tag_obj.tag.id
                            tag_obj_dict["tag_name"]=conv_tag_obj.tag.tag_name
                            conversation_dict["tags"].append(tag_obj_dict)
                        result_dict["resolved_conversations"].append(conversation_dict)
                            
                log_message(20,f"All conversations list viewed successfully! USER:{current_user_email}")                  
                return JSONResponse(content=result_dict) 
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing all conversations list! USER:{current_user_email}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource!"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing all conversations list!")
        return JSONResponse(content={"Error": "Invalid token"})
    

async def singleConversation(conversation_id: str, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view single conversation! USER:{current_user_email} INPUT:{{'conversation_id':{conversation_id}}}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing single conversation! USER:{current_user_email} INPUT:{{'conversation_id':{conversation_id}}}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else: 
                        super_admin_id = current_user.super_admin_id
                        
                    try:
                        conversation_query= select(Conversation).options(
                            selectinload(Conversation.conversation_tags).options(selectinload(ConversationTags.tag)),
                            selectinload(Conversation.customer).options(
                                selectinload(Customers.conversation)
                                ),
                            selectinload(Conversation.assigned_bot),
                            selectinload(Conversation.assigned_agent)).filter(
                                Conversation.super_admin_id==super_admin_id,
                                Conversation.conversation_deleted==False,
                                Conversation.conversation_uuid==conversation_id                      
                            )
                        conversation = await SessionLocal.execute(conversation_query)
                        conversation_obj = conversation.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch conversation_query while viewing single conversation! USER:{current_user_email} INPUT:{{'conversation_id':{conversation_id}}}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                
                    result_dict = {}
                    result_dict["conversation_id"] = conversation_obj.conversation_uuid
                    result_dict["conversation_handler"] = conversation_obj.conversation_handler
                    result_dict["customer"] = {}
                    result_dict["customer"]["customer_id"] = conversation_obj.customer.id
                    if conversation_obj.customer.got_real_name==True:
                        customer_name = conversation_obj.customer.customer_real_name
                    else:
                        customer_name=conversation_obj.customer.customer_generated_name
                    result_dict["customer"]["customer_name"] = customer_name
                    result_dict["customer"]["customer_email"] = conversation_obj.customer.customer_email
                    result_dict["customer"]["customer_phone"] = conversation_obj.customer.customer_phone_number
                    result_dict["conversation_status"] = conversation_obj.end_user_conversation_status
                    result_dict["manually_assigned"] = conversation_obj.conversation_manually_assigned
                    result_dict["last_message_time"] = "12:50 PM"
                    result_dict["tags"] = []
                    for conv_tag_obj in conversation_obj.conversation_tags:
                        tag_obj_dict = {}
                        tag_obj_dict["tag_id"]=conv_tag_obj.tag.id
                        tag_obj_dict["tag_name"]=conv_tag_obj.tag.tag_name
                        result_dict["tags"].append(tag_obj_dict)

                    result_dict["conversation_assigned_to"]={}  
                    result_dict["conversation_assigned_to"]["selected"]={}  
                    if conversation_obj.conversation_handler == 'HUMAN':     
                        result_dict["conversation_assigned_to"]["selected"]["agent_id"]=conversation_obj.assigned_agent.id           
                        result_dict["conversation_assigned_to"]["selected"]["first_name"]=conversation_obj.assigned_agent.first_name 
                        result_dict["conversation_assigned_to"]["selected"]["last_name"]=conversation_obj.assigned_agent.last_name
                        
                    if conversation_obj.conversation_handler == 'BOT':            
                        result_dict["conversation_assigned_to"]["selected"]["bot_id"]=conversation_obj.assigned_bot.id            
                        result_dict["conversation_assigned_to"]["selected"]["bot_name"]=conversation_obj.assigned_bot.bot_name  
                        
                log_message(20,f"Single conversation viewed successfully! USER:{current_user_email} INPUT:{{'conversation_id':{conversation_id}}}")          
                return JSONResponse(content=result_dict) 
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing single conversation! USER:{current_user_email} INPUT:{{'conversation_id':{conversation_id}}}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing single conversation! INPUT:{{'conversation_id':{conversation_id}}}")
        return JSONResponse(content={"Error": "Invalid token"})

  

async def addConversationTag(request_data: AddConversationTagSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to add conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while adding conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding conversation tag!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        conversation_query = select(Conversation).options(selectinload(Conversation.conversation_tags).options(selectinload(ConversationTags.tag))).filter(and_(Conversation.super_admin_id==super_admin_id,Conversation.conversation_uuid==request_data.conversation_id))
                        conversation_obj = await SessionLocal.execute(conversation_query)
                        conversation_obj = conversation_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch conversation_query while adding conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding conversation tag!"})
                    
                    if conversation_obj == None:
                        log_message(30,f"Conversation object cannot be None while adding conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding conversation tag!"}) #No conversation obj
                        
                    conversation_obj_tags = [conv_tag_obj.tag.tag_name for conv_tag_obj in conversation_obj.conversation_tags]
                    
                    if request_data.tag_name in conversation_obj_tags:
                        log_message(40,f"Cannot add already added tag while adding conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding conversation tag!"}) #Tag already added
                    
                    try:
                        tag_objects_query=select(Tags).filter(Tags.super_admin_id==super_admin_id)
                        tag_objects = await SessionLocal.execute(tag_objects_query)
                        tag_objects = tag_objects.scalars().all()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch tag_objects_query while adding conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding conversation tag!"})
                    
                    all_tag_names = [tag_obj.tag_name for tag_obj in tag_objects]
                    
                    if request_data.tag_name in all_tag_names:
                        tag=list(filter(lambda x:x.tag_name == request_data.tag_name,tag_objects))
                        tag=tag[0]
                    else:
                        tag = Tags(tag_name=request_data.tag_name,super_admin_id =super_admin_id)
                    
                    
                    try:
                        conversation_tag=ConversationTags(tag=tag, conversation=conversation_obj)
                        SessionLocal.add(conversation_tag)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add conversation_tag to session while adding conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding conversation tag!"})
                await SessionLocal.commit()
                log_message(20,f"Conversation tag added successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Conversation tag added successfully!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while adding conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error adding conversation tag!"}) 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while adding conversation tag! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



async def removeConversationTag(request_data: RemoveConversationTagSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to remove conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while removing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error removing conversation tag!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        conversation_query = select(Conversation).options(selectinload(Conversation.conversation_tags).options(selectinload(ConversationTags.tag))).filter(and_(Conversation.super_admin_id==super_admin_id,Conversation.conversation_uuid==request_data.conversation_id))
                        conversation_obj = await SessionLocal.execute(conversation_query)
                        conversation_obj = conversation_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch conversation_query while removing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error removing conversation tag!"})
                    
                    if conversation_obj == None:
                        log_message(30,f"Conversation object not found for the requested id while removing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error removing conversation tag!"}) #No conversation obj
                        
                    conv_tag = list(filter(lambda x:x.tag.tag_name==request_data.tag_name,conversation_obj.conversation_tags))
                    
                    if conv_tag==[]:
                        log_message(30,f"Conversation tag not found for the requested tag name while removing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error removing conversation tag!"}) 
                    
                    try:
                        await SessionLocal.delete(conv_tag[0])
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot delete conv_tag in session while removing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error removing conversation tag!"})
                await SessionLocal.commit()
                log_message(20,f"Conversation tag removed successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Conversation tag removed successfully!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while removing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error removing conversation tag!"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while removing conversation tag! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



async def conversationStatus(request_data: ConversationStatusSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to change conversation status! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while changing conversation status! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error changing conversation status!"})
                    
                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                                         
                    try:
                        conversation_query = select(Conversation).filter(
                            Conversation.super_admin_id==super_admin_id,
                            Conversation.conversation_uuid==request_data.conversation_id
                            )
                        conversation_obj = await SessionLocal.execute(conversation_query)
                        conversation_obj = conversation_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch conversation_query while changing conversation status! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error changing conversation status!"})
                    
                    
                    if conversation_obj == None:
                        log_message(30,f"Conversation object cannot be None while changing conversation status! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error changing conversation status!"}) #No conversation obj
                    
                    try:
                        conversation_obj.end_user_conversation_status = request_data.conversation_status
                        SessionLocal.add(conversation_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add conversation_obj to session while changing conversation status! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error changing conversation status!"})
                    
                await SessionLocal.commit()
                log_message(20,f"Conversation status changed successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Conversation status changed to {}!".format(request_data.conversation_status)})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while changing conversation status! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error changing conversation status!"})  
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while changing conversation status! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    


async def allTags(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view all conversation tags! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing all conversation tags! USER:{current_user_email}")
                        JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(selectinload(User.all_tags)).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing all conversation tags! USER:{current_user_email}")
                        JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                    
                    all_tags = super_admin.all_tags
                    result_dict={}
                    result_dict["all_tags"]=[]
                    for tag_obj in all_tags:
                        tag_dict={}
                        tag_dict["tag_id"]=tag_obj.id
                        tag_dict["tag_name"]=tag_obj.tag_name
                        result_dict["all_tags"].append(tag_dict)  
                        
                log_message(20,f"All conversation tags viewed successfully! USER:{current_user_email}")                        
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing all conversation tags! USER:{current_user_email}")
            JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing all conversation tags!")
        return JSONResponse(content={"Error": "Invalid token"})



async def addTag(request_data: AddTagSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to add new tag! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while adding new tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding new tag!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                
                    try:
                        tag_objects_query=select(Tags).filter(Tags.super_admin_id==super_admin_id)
                        tag_objects = await SessionLocal.execute(tag_objects_query)
                        tag_objects = tag_objects.scalars().all()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch tag_objects_query while adding new tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error adding new tag!"})
                    
                    all_tag_names = [tag_obj.tag_name for tag_obj in tag_objects]
                    
                    if request_data.tag_name in all_tag_names:
                        log_message(40,str(sys.exc_info())+f"Tag name already present while adding new tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Tag name already present!"})
                    else:
                        tag = Tags(tag_name=request_data.tag_name,super_admin_id =super_admin_id)
                        try:
                            SessionLocal.add(tag)
                        except:
                            log_message(40,str(sys.exc_info())+f"Cannot add tag_object to session while adding new tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                            return JSONResponse(content={"Error":"Error adding conversation tag!"})
                        
                await SessionLocal.commit()
                log_message(20,f"Tag created successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Tag created successfully!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while adding new tag! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error adding new tag!"}) 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while adding new tag! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})


async def editTag(request_data: EditTagSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to edit conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try: 
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while editing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing tag!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        tag_query = select(Tags).filter(and_(Tags.super_admin_id==super_admin_id,Tags.id==request_data.tag_id))
                        tag_obj = await SessionLocal.execute(tag_query)
                        tag_obj = tag_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch tag_query while editing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing tag!"})
                    
                    if tag_obj in (None,''):
                        log_message(30,f"Tag object cannot be None while editing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing tag!"}) 
                     
                    try:
                        tag_obj.tag_name = request_data.tag_name
                        SessionLocal.add(tag_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add tag_obj to session while editing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error editing tag!"})
                await SessionLocal.commit()
                
                log_message(20,f"Conversation tag edited successully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Tag edited successfully!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while editing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error editing tag!"})  
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while editing conversation tag! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})  
     
     
     
     
     
     
     
     
     
async def removeTags(request_data: TagSerializer, Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to remove conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try: 
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while removing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error removing tag!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        tag_query = select(Tags).filter(and_(Tags.super_admin_id==super_admin_id,Tags.id==request_data.tag_id))
                        tag_obj = await SessionLocal.execute(tag_query)
                        tag_obj = tag_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch tag_query while removing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error removing tag!"})
                    
                    if tag_obj == None:
                        log_message(30,f"Tag object cannot be None while removing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error removing tag!"}) 
                     
                    try:
                        await SessionLocal.delete(tag_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add tag_obj to session while removing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error removing tag!"})
                await SessionLocal.commit()
                
                log_message(20,f"Conversation tag removed successully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Tag removed successfully!"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while removing conversation tag! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error removing tag!"})  
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while removing conversation tag! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    

  




async def takeOverConversation(request_data:TakeOverConversationSerilaizer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to take over conversation! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while taking over conversation! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error assigning the conversation!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        conversation_query = select(Conversation).options(selectinload(Conversation.assigned_agent)).filter(and_(
                            Conversation.super_admin_id==super_admin_id,
                            Conversation.conversation_uuid==request_data.conversation_id))
                        conversation_obj = await SessionLocal.execute(conversation_query)
                        conversation_obj = conversation_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch conversation_query while taking over conversation! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error assigning the conversation!"})
                    
                    try:
                        conversation_obj.assigned_agent =current_user                        
                        conversation_obj.conversation_handler = "HUMAN"
                        conversation_obj.conversation_manually_assigned = True
                        SessionLocal.add(conversation_obj)
                    except:
                        log_message(40,str(sys.exc_info())+f"Cannot add conversation_obj to session while taking over conversation! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"assigning the conversation!"})
                    
                    first_name = current_user.first_name
                    last_name = current_user.last_name
                await SessionLocal.commit()
                log_message(20,f"Conversation took over by a user successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Conversation assigned to {} {}!".format(first_name,last_name)})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while taking over conversation! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error assigning the conversation!"})  #Unknown error 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while taking over conversation! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    
    
async def sendTranscriptToCustomer(request_data:SendTranscriptSerilaizer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to send conversation transcript to customer! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while sending conversation transcript to customer! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error sending the conversation transcript!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    
                    try:
                        customer_query = select(Customers).filter(and_(
                            Customers.super_admin_id==super_admin_id,
                            Customers.customer_generated_name==request_data.customer_id))
                        customer_obj = await SessionLocal.execute(customer_query)
                        customer_obj = customer_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch customer_query while sending conversation transcript to customer! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error sending the conversation transcript!"})
                    
                    if customer_obj==None:
                        log_message(30,f"Customer object cannot be None while sending conversation transcript to customer! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error sending the conversation transcript!"})
                    
                    if customer_obj.customer_email==None:
                        log_message(30,f"Customer email object cannot be None while sending conversation transcript to customer! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Please add customer email!"})
                    
                    
                    conversation_id = request_data.conversation_id 
                    #using this id try to fetch the conversation and send in the mail
                    
                    
                    sender_email = current_user.email
                    sender_name = current_user.first_name
                    if current_user.last_name:
                        last_name= current_user.last_name
                        sender_name = sender_name + " " + last_name
                        
                    try:
                        email_query = select(EmailTemplates).filter(EmailTemplates.template_name=='customer_transcript_template')
                        mail_data_obj = await SessionLocal.execute(email_query)
                        mail_data_obj = mail_data_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Error fetching email_query while sending conversation transcript to customer! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error sending the conversation transcript!"})
                    
                    
                    try:
                        sendEmails.delay(mail_data_obj.message_subject,[customer_obj.customer_email],mail_data_obj.message_template.format(sender_name,sender_email))
                    except:
                        log_message(40,str(sys.exc_info())+f"Error in sending email while sending conversation transcript to customer! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error sending the conversation transcript!!"})
                await SessionLocal.commit()
                log_message(20,f"Conversation transcript sent to customer successfully! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Conversation transcript sent successfully"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while sending conversation transcript to customer! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Error sending the conversation transcript!!"}) 
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while sending conversation transcript to customer! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
async def convFilterOptions(Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to access conversation filter while viewing conversation page! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while accessing conversation filter while viewing conversation page! USER:{current_user_email}")
                        JSONResponse(content={"Error":"Couldn't fetch requested resource"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.all_tags),
                            selectinload(User.default_team).options(selectinload(DefaultTeam.bots))
                            ).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while accessing conversation filter while viewing conversation page! USER:{current_user_email}")
                        JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                    
                    all_tags = super_admin.all_tags
                    result_dict={}
                    result_dict["all_status"]=["Open","First-response-pending","Resolved","Spam","Queued"]
                    result_dict["all_tags"]=[tag_obj.tag_name for tag_obj in all_tags]
                    
                    result_dict["assignd_to"] = {}
                    result_dict["assignd_to"]["Humans"]=[{"id":super_admin.id,"first_name":super_admin.first_name,"last_name":super_admin.last_name}]
                    try:
                        all_users_query = select(User).filter(User.super_admin_id==super_admin_id)
                        all_users = await SessionLocal.execute(all_users_query)
                        all_users = all_users.scalars().all()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch all_users_query while accessing conversation filter while viewing conversation page! USER:{current_user_email}")
                        JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                    
                    for user in all_users:
                        user_dict={}
                        user_dict["id"]=user.id
                        user_dict["first_name"]=user.first_name
                        user_dict["last_name"]=user.last_name
                        result_dict["assignd_to"]["Humans"].append(user_dict)
                                        
                    result_dict["assignd_to"]["Bots"]=[]
                    all_bots=super_admin.default_team.bots
                    all_bots = list(filter(lambda x:x.is_active==True,all_bots))
                    for bot_obj in all_bots:
                        bot_dict={}
                        bot_dict["bot_id"]=bot_obj.id
                        bot_dict["bot_name"] = bot_obj.bot_name
                        result_dict["assignd_to"]["Bots"].append(bot_dict)
                        
                log_message(20,f"Conversation filter while viewing conversation page accessed successfully! USER:{current_user_email}")      
                return JSONResponse(content=result_dict)
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while accessing conversation filter while viewing conversation page! USER:{current_user_email}")
            JSONResponse(content={"Error":"Couldn't fetch requested resource"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while accessing conversation filter while viewing conversation page!")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
    
async def filtered_conversations(request_data:ConversationFilterSerializer,Authorize : AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view filtered conversations! USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        current_user_query = select(User).filter(User.email==current_user_email)
                        current_user = await SessionLocal.execute(current_user_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch current_user_query while viewing filtered conversations! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource!"})

                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else: 
                        super_admin_id = current_user.super_admin_id
                        
                    
                    # ------------------ DATE FILTERING IS DONE HERE ------------------------
                    if request_data.date_range!={}:
                        from_date = request_data.date_range["from_date"]
                        to_date = request_data.date_range["to_date"]
                        from_date = datetime(from_date[0],from_date[1],from_date[2]) 
                        to_date = datetime(to_date[0],to_date[1],to_date[2]+1)
                    else:
                        from_date = datetime.today() - timedelta(days=30) 
                        to_date = datetime.today()
                        
                
                    try:
                        all_account_conversations_query= select(Conversation).options(
                            selectinload(Conversation.conversation_tags).options(selectinload(ConversationTags.tag)),
                            selectinload(Conversation.customer)).filter(
                                Conversation.super_admin_id==super_admin_id,
                                Conversation.conversation_deleted==False,
                                Conversation.created_time>=from_date,
                                Conversation.created_time<=to_date
                                                        
                            ).order_by(Conversation.created_time)
                        all_account_conversations = await SessionLocal.execute(all_account_conversations_query)
                        all_account_conversations = all_account_conversations.scalars().all()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch all_account_conversations_query while viewing filtered conversations! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource!"})
                    
                    
                    
                    # ---------------------- CONVERSATION STATUS FILTERING -------------------------
                    
                    if request_data.status !=[]:
                        status_list = request_data.status
                    else:
                        status_list = ['First-response-pending' ,'Open' ,'Resolved' ,'Spam' ,'Queued']
                                    
                    filtered_conversations = list(filter(
                        lambda x:x.end_user_conversation_status in status_list,
                        all_account_conversations))
                    
                    #--------------------------- TAG FILTERING -----------------------------------------
                    try:
                        all_account_tags_query= select(Tags).filter(Tags.super_admin_id==super_admin_id)
                        all_account_tags = await SessionLocal.execute(all_account_tags_query)
                        all_account_tags = all_account_tags.scalars().all()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch all_account_tags_query while viewing filtered conversations! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource!"})
                    
                    if request_data.tags!=[]:
                        requested_tags = request_data.tags
                    else:
                        requested_tags = [tag.tag_name for tag in all_account_tags]
                        
                    def tag_filter(conv):
                        if conv.conversation_tags !=[]:
                            for conv_tag in conv.conversation_tags:
                                if conv_tag.tag.tag_name in requested_tags:
                                    return True
                                
                        if conv.conversation_tags ==[]:
                            return True
                    
                    filtered_conversations = list(filter(lambda x:tag_filter(x),
                        filtered_conversations))
                    
                    #---------------------------- ASSIGNEE TYPE FILTERING --------------------
                    
                    
                    def assignee_filter(conv):
                        if request_data.assigned_to=={}:
                            return True
                            
                        if request_data.assigned_to["assignee_type"] == "HUMAN" and conv.conversation_handler=="HUMAN":
                            if conv.assigned_agent_id==request_data.assigned_to["assignee_id"]:
                                return True
                            
                        if request_data.assigned_to["assignee_type"] == "BOT" and conv.conversation_handler=="BOT":
                            if conv.assigned_bot_id==request_data.assigned_to["assignee_id"]:
                                return True
                
            
                    
                    filtered_conversations = list(filter(lambda x:assignee_filter(x),
                        filtered_conversations))
                    
                    #-------------------------- FINAL DICTIONARY --------------------------
                    result_dict = {}
                    result_dict["filtered_conversations"]=[]
                    
                    for conversation in filtered_conversations:
                        conversation_dict = {}
                        conversation_dict["conversation_id"] = conversation.conversation_uuid
                        conversation_dict["conversation_handler"] = conversation.conversation_handler
                        conversation_dict["customer"] = {}
                        conversation_dict["customer"]["customer_id"] = conversation.customer.id
                        if conversation.customer.got_real_name==True:
                            customer_name = conversation.customer.customer_real_name
                        else:
                            customer_name=conversation.customer.customer_generated_name
                        conversation_dict["customer"]["customer_name"] = customer_name
                        conversation_dict["conversation_status"] = conversation.end_user_conversation_status
                        conversation_dict["manually_assigned"] = conversation.conversation_manually_assigned
                        conversation_dict["last_message_time"] = "12:50 PM"
                        conversation_dict["tags"] = []
                        for conv_tag_obj in conversation.conversation_tags:
                            tag_obj_dict = {}
                            tag_obj_dict["tag_id"]=conv_tag_obj.tag.id
                            tag_obj_dict["tag_name"]=conv_tag_obj.tag.tag_name
                            conversation_dict["tags"].append(tag_obj_dict)
                        result_dict["filtered_conversations"].append(conversation_dict)
                log_message(20,f"Filtered conversations viewed succesfully! USER:{current_user_email} INPUT:{request_data.dict()}")                    
                return JSONResponse(content=result_dict) 
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing filtered conversations! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={"Error":"Couldn't fetch requested resource!"})
    except:
        log_message(40,str(sys.exc_info())+f"Invalid token error while viewing filtered conversations! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})




async def addCsatRating(request_data:CsatRatingSerilaizer):
    log_message(10,f"Customer trying to rate the conversation! INPUT:{request_data.dict()}")
    try:
        async with settings.SessionLocal as SessionLocal:
            async with SessionLocal.begin_nested():
                try:
                    conversation_query = select(Conversation).filter(
                        Conversation.conversation_uuid==request_data.conversation_id)
                    conversation = await SessionLocal.execute(conversation_query)
                    conversation = conversation.scalars().first()
                except:
                    log_message(40,str(sys.exc_info())+f"Couldn't fetch conversation_query while rating conversation! INPUT:{request_data.dict()}")
                    return JSONResponse(content={"Error":"Error rating the conversation!"})
                
                try:
                    rating_object = CsatRatings(super_admin_id=conversation.super_admin_id,
                                                conversation = conversation,
                                                rating=request_data.rating_type,
                                                comment=request_data.comment)
                    SessionLocal.add(rating_object)
                except:
                    log_message(40,str(sys.exc_info())+f"Cannot add rating_object to session while rating conversation! INPUT:{request_data.dict()}")
                    return JSONResponse(content={"Error":"Error rating the conversation!"})
            await SessionLocal.commit()
            log_message(20,f"Conversation rated by a customer successfully! INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Conversation rated by a customer successfully!!"})
    except:
        log_message(50,str(sys.exc_info())+f"Unknown error while rating conversation! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error":"Error rating the conversation!"})  #Unknown error 
    
    
async def getAppId(Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to get the app id! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).options(
                            selectinload(User.account_option)
                            ).where(User.email==current_user_email,User.email_verified==True)
                        user_obj = await SessionLocal.execute(user_obj_query)
                        user_obj = user_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch user_obj_query while viewing app id! USER:{current_user_email}")
                        return JSONResponse(content={'Error':"Couldn't fetch requested resource!"})
                    
                    if user_obj==None:
                        log_message(40,str(sys.exc_info())+f"User object cannot be None while fetching app id! USER:{current_user_email}")
                        return JSONResponse(content={'Error':"Couldn't fetch requested resource"})
                    
                    if user_obj.role == "SuperAdmin":
                        app_id =  user_obj.account_option.app_id
                    else: 
                        super_admin_id = user_obj.super_admin_id
                        
                        try:
                            super_admin_query = select(User).options(
                                selectinload(User.account_option)
                                ).where(User.id==super_admin_id,User.email_verified==True)
                            super_admin_obj = await SessionLocal.execute(super_admin_query)
                            super_admin_obj = super_admin_obj.scalars().first()
                        except:
                            log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing app id! USER:{current_user_email}")
                            return JSONResponse(content={'Error':"Couldn't fetch requested resource!"})
                        
                        app_id =  super_admin_obj.account_option.app_id
                    
                    log_message(20,'User successfully viewed the fetched the app id!'+f" USER:{current_user_email}")
                    return JSONResponse(content={'app_id':app_id})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while fetching app id! USER:{current_user_email}")
            return JSONResponse(content={'Error':"Couldn't fetch requested resource"}) 
    except:
        log_message(40,str(sys.exc_info())+"Invalid token error while fetching app id!")
        return JSONResponse(content={"Error":"Invalid Token"})
    
    
    
async def chatWidgetPopupSettings(bot_id: int, app_id:str):
    log_message(10,f"A new chat widget opened for bot_id = {bot_id} and app_id = {app_id}")
    try:
        async with settings.SessionLocal as SessionLocal:
            async with SessionLocal.begin_nested():
                try:
                    account_option_query = select(AccountOptions).options(
                        selectinload(AccountOptions.super_admin).options(
                            selectinload(User.chat_widget_customization),
                            selectinload(User.chat_widget_configuration),
                            selectinload(User.default_team).options(
                                selectinload(DefaultTeam.bots)))
                        ).where(AccountOptions.app_id==app_id)
                    account_option_obj = await SessionLocal.execute(account_option_query)
                    account_option_obj = account_option_obj.scalars().first()
                except Exception as e:
                    log_message(40,str(sys.exc_info())+f"Couldn't fetch account_option_query while viewing chat widget popup setting! BOT_ID:{bot_id} and app_id = {app_id}")
                    print(e)
                    print(str(sys.exc_info()))
                    return JSONResponse(content={'Error':"Couldn't fetch requested resource! Here"})
                
                bot_list = account_option_obj.super_admin.default_team.bots
                
                selected_bot = list(filter(lambda x:x.id == bot_id, bot_list))
                
                if selected_bot == []:
                    log_message(40,'There is no bot for the requested id!'+f"BOT_ID:{bot_id} and app_id = {app_id}")
                    return JSONResponse(content={'Error':"Couldn't fetch requested resource"})
                
                else:
                    bot_obj = selected_bot[0]
                    widget_settings = {}
                    widget_settings["bot_id"]=bot_obj.id
                    widget_settings["bot_name"]=bot_obj.bot_name
                    widget_settings["bot_image"]=str(bot_obj.bot_photo.decode('utf-8')) if bot_obj.bot_photo!=None else None
                    
                    chat_widget_customization = account_option_obj.super_admin.chat_widget_customization
                    chat_widget_configuration = account_option_obj.super_admin.chat_widget_configuration
                    
                    widget_settings["chatWidget"]={}
                    widget_settings["chatWidget"]["popup"]=True
                    widget_settings["chatWidget"]["position"]=chat_widget_customization.widget_position
                    widget_settings["chatWidget"]["color"]=chat_widget_customization.color
                    widget_settings["chatWidget"]["launcher_icon_option"]=chat_widget_customization.launcher_option
                    if chat_widget_customization.launcher_option == 'Upload':
                        widget_settings["chatWidget"]["icon_image"] = chat_widget_customization.icon_image.decode('utf-8')
                    else:
                        widget_settings["chatWidget"]["icon_image"] = chat_widget_customization.default_icon_option
                        
                    widget_settings["chatWidget"]["notification_tone"]=chat_widget_customization.chat_notification_sound
                    widget_settings["chatWidget"]["chat_session_history"]={}
                    widget_settings["chatWidget"]["chat_session_history"]["remove_history_after_page_refresh"]= chat_widget_configuration.remove_chat_history_on_page_refresh
                    widget_settings["chatWidget"]["chat_session_history"]["history_removal_days"]= chat_widget_configuration.history_removal_days
                    widget_settings["chatWidget"]["chat_session_history"]["history_removal_hours"]= chat_widget_configuration.history_removal_hours
                    widget_settings["chatWidget"]["chat_session_history"]["history_removal_minutes"]= chat_widget_configuration.history_removal_minutes
                    widget_settings["chatWidget"]["bot_msg_delay_interval"]= chat_widget_configuration.bot_reply_delay
                    
                    widget_settings["chatWidget"]["allow_single_thread_conversation"]= chat_widget_configuration.allow_single_thread_conversation
                    widget_settings["chatWidget"]["disable_chat_widget"]= chat_widget_configuration.disable_chat_widget
                    widget_settings["chatWidget"]["hide_attachment"]= chat_widget_configuration.hide_attachment
                   
                    log_message(20,'Chat widget popped ip successfully!'+f"BOT_ID:{bot_id} and app_id = {app_id}")
                    return JSONResponse(content=widget_settings)
    except:
        log_message(50,str(sys.exc_info())+f"Unknown error while viewing chat widget popup setting! BOT_ID:{bot_id} and app_id = {app_id}")
        return JSONResponse(content={'Error':"Couldn't fetch requested resource"}) 

async def chatHistory(visitorId:str,number_of_chats:int,scroll_call:int):
    try:
        log_message(10,f"User trying to view all chats of a conversation!")
        async with settings.SessionLocal as SessionLocal:
            async with SessionLocal.begin_nested():
                try:
                    visitor_query = select(Customers).options(
                        selectinload(Customers.conversation).options(
                            selectinload(Conversation.all_chats),
                            selectinload(Conversation.assigned_bot),
                            selectinload(Conversation.assigned_agent)
                        )
                    ).filter(Customers.customer_generated_name==visitorId)
                    visitor = await SessionLocal.execute(visitor_query)
                    visitor = visitor.scalars().first()
                except:
                    log_message(40,str(sys.exc_info())+f"Couldn't fetch visitor_query while viewing conversationChats!")
                    return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                
                                        
                all_chats = visitor.conversation.all_chats
                all_chats.sort(key=operator.attrgetter('created_time'), reverse=True)
                
                start_slice=(scroll_call - 1) * number_of_chats 
                end_slice=number_of_chats*scroll_call
                
                all_chats = all_chats[start_slice:end_slice]
                result = []
                for chat in all_chats:
                    chat_dict = json.loads(chat.response)
                    result.append(chat_dict)
                
            log_message(20,f"All Chats viewed successfully!")
            return JSONResponse(content=result) 
    except:
        log_message(50,str(sys.exc_info())+f"Unknown error while viewing all chats!")
        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})


async def frontEndChatWidgetSettings(app_id:str):
    log_message(10,f"A chat widget opened for app_id = {app_id}")
    try:
        async with settings.SessionLocal as SessionLocal:
            async with SessionLocal.begin_nested():
                try:
                    account_option_query = select(AccountOptions).options(
                        selectinload(AccountOptions.super_admin).options(
                            selectinload(User.chat_widget_customization),
                            selectinload(User.chat_widget_configuration)
                        )
                        ).filter(AccountOptions.app_id==app_id)
                    account_option_obj = await SessionLocal.execute(account_option_query)
                    account_option_obj = account_option_obj.scalars().first()
                except:
                    log_message(40,str(sys.exc_info())+f"Couldn't fetch account_option_query while viewing frontend chat widget popup setting!  app_id = {app_id}")
                    return JSONResponse(content={'Error':"Couldn't fetch requested resource!"})
                
                
                widget_settings = {}
                
                chat_widget_customization = account_option_obj.super_admin.chat_widget_customization
                chat_widget_configuration = account_option_obj.super_admin.chat_widget_configuration
                
                widget_settings["chatWidget"]={}
                widget_settings["chatWidget"]["popup"]=True
                widget_settings["chatWidget"]["position"]=chat_widget_customization.widget_position
                widget_settings["chatWidget"]["color"]=chat_widget_customization.color
                widget_settings["chatWidget"]["launcher_icon_option"]=chat_widget_customization.launcher_option
                if chat_widget_customization.launcher_option == 'Upload':
                    widget_settings["chatWidget"]["icon_image"] = chat_widget_customization.icon_image.decode('utf-8')
                else:
                    widget_settings["chatWidget"]["icon_image"] = chat_widget_customization.default_icon_option
                        
                widget_settings["chatWidget"]["notification_tone"]=chat_widget_customization.chat_notification_sound
                widget_settings["chatWidget"]["bot_msg_delay_interval"]= chat_widget_configuration.bot_reply_delay
                    
                widget_settings["chatWidget"]["disable_chat_widget"]= chat_widget_configuration.disable_chat_widget
                widget_settings["chatWidget"]["hide_attachment"]= chat_widget_configuration.hide_attachment
                   
                log_message(20,'Chat widget front-end popped ip successfully!'+f"app_id = {app_id}")
                return JSONResponse(content=widget_settings)
    except:
        log_message(50,str(sys.exc_info())+f"Unknown error while viewing chat widget front-end popup setting! app_id = {app_id}")
        return JSONResponse(content={'Error':"Couldn't fetch requested resource"})


async def showOperatorPermissions(Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view the operator permissions! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).where(User.email==current_user_email,User.email_verified==True)
                        current_user = await SessionLocal.execute(user_obj_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch user_obj_query while viewing operaator permissions! USER:{current_user_email}")
                        return JSONResponse(content={'Error':"Couldn't fetch requested resource!"})
                    
                    
                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.account_option).options(
                                selectinload(AccountOptions.operator_permissions))
                            ).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while viewing Falback emails setting! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource"})
                    
                    operator_permissions = {}
                    operator_permissions["allow_assign_to_teammates"] = super_admin.account_option.operator_permissions.allow_assign_to_teammates
                    operator_permissions["allow_assign_back_to_bot"] = super_admin.account_option.operator_permissions.allow_assign_back_to_bot
                    operator_permissions["allow_reassign_to_team"] = super_admin.account_option.operator_permissions.allow_reassign_to_team
                    
                    log_message(20,'User successfully viewed the operator permissions!'+f" USER:{current_user_email}")
                    return JSONResponse(content={'operator_permissions':operator_permissions})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing operator permissions! USER:{current_user_email}")
            return JSONResponse(content={'Error':"Couldn't fetch requested resource"}) 
    except:
        log_message(40,str(sys.exc_info())+"Invalid token error while viewing operaator permissions!")
        return JSONResponse(content={"Error":"Invalid Token"})



async def allowConvAssignmentToTeammates(request_data : OpPermissionTeammateSerializer, Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,"User trying to update the allow operators to assign conversation to teammates"+f"USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).where(User.email==current_user_email,User.email_verified==True)
                        current_user = await SessionLocal.execute(user_obj_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch user_obj_query while updating the allow operators to assign conversation to teammates! USER:{current_user_email}")
                        return JSONResponse(content={'Error':"Error updating the allow operators to assign conversation to teammates option!"})
                    
                    
                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.account_option).options(
                                selectinload(AccountOptions.operator_permissions))
                            ).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating the allow operators to assign conversation to teammates! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Error updating the allow operators to assign conversation to teammates option!"})
                    
                    try:
                        super_admin.account_option.operator_permissions.allow_assign_to_teammates = request_data.allow
                        SessionLocal.add(super_admin)
                    except:
                        log_message(30,str(sys.exc_info())+f"Error adding user_obj to session while updating the allow operators to assign conversation to teammates! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the allow operators to assign conversation to teammates option!"})
                    
                await SessionLocal.commit()
                log_message(20,f"Allow operators to assign conversation to teammates updated! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Allow operators to assign conversation to teammates updated"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating the allow operators to assign conversation to teammates option! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={'Error':'Error updating the allow operators to assign conversation to teammates option!'}) 
    except Exception as e:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating the allow operators to assign conversation to teammates option! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})


async def allowConvAssignmentToBot(request_data : OpPermissionBotSerializer, Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,"User trying to update the allow operators to assign conversation to bot"+f"USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).where(User.email==current_user_email,User.email_verified==True)
                        current_user = await SessionLocal.execute(user_obj_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch user_obj_query while updating the allow operators to assign conversation to bot! USER:{current_user_email}")
                        return JSONResponse(content={'Error':"Error updating the allow operators to assign conversation to bot option!"})
                    
                    
                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.account_option).options(
                                selectinload(AccountOptions.operator_permissions))
                            ).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating the allow operators to assign conversation to bot! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Error updating the allow operators to assign conversation to bot option!"})
                    
                    try:
                        super_admin.account_option.operator_permissions.allow_assign_back_to_bot = request_data.allow
                        SessionLocal.add(super_admin)
                    except:
                        log_message(30,str(sys.exc_info())+f"Error adding user_obj to session while updating the allow operators to assign conversation to bot! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the allow operators to assign conversation to bot option!"})
                    
                await SessionLocal.commit()
                log_message(20,f"Allow operators to assign conversation to bot updated! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Allow operators to assign conversation to bot updated"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating the allow operators to assign conversation to bot option! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={'Error':'Error updating the allow operators to assign conversation to bot option!'}) 
    except Exception as e:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating the allow operators to assign conversation to bot option! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})



async def allowConvAssignmentToTeam(request_data:OpPermissionTeamSerializer, Authorize:AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,"User trying to update the allow operators to re-assign conversation to Team"+f"USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).where(User.email==current_user_email,User.email_verified==True)
                        current_user = await SessionLocal.execute(user_obj_query)
                        current_user = current_user.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch user_obj_query while updating the allow operators to re-assign conversation to Team! USER:{current_user_email}")
                        return JSONResponse(content={'Error':"Error updating the allow operators to re-assign conversation to Team option!"})
                    
                    
                    if current_user.role == "SuperAdmin":
                        super_admin_id =current_user.id
                    else:
                        super_admin_id = current_user.super_admin_id
                    try:
                        super_admin_query = select(User).options(
                            selectinload(User.account_option).options(
                                selectinload(AccountOptions.operator_permissions))
                            ).filter(User.id==super_admin_id)
                        super_admin = await SessionLocal.execute(super_admin_query)
                        super_admin = super_admin.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch super_admin_query while updating the allow operators to re-assign conversation to Team! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Error updating the allow operators to re-assign conversation to Team option!"})
                    
                    try:
                        super_admin.account_option.operator_permissions.allow_reassign_to_team = request_data.allow
                        SessionLocal.add(super_admin)
                    except:
                        log_message(30,str(sys.exc_info())+f"Error adding user_obj to session while updating the allow operators to re-assign conversation to Team! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error updating the allow operators to re-assign conversation to Team!"})
                    
                await SessionLocal.commit()
                log_message(20,f"Allow operators to re-assign conversation to team updated! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Allow operators to re-assign conversation to team updated"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while updating the allow operators to re-assign conversation to team option! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={'Error':'Error updating the allow operators to re-assign conversation to Team option!'}) 
    except Exception as e:
        log_message(40,str(sys.exc_info())+f"Invalid token error while updating the allow operators to re-assign conversation to team option! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
    
    
async def checkAvailablityStatus(Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view availability status! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).where(User.email==current_user_email,User.email_verified==True)
                        user_obj = await SessionLocal.execute(user_obj_query)
                        user_obj = user_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch user_obj_query while viewing availability status! USER:{current_user_email}")
                        return JSONResponse(content={'Error':"Couldn't fetch requested resource!"})
                    
                    availablity_status =  user_obj.is_available_status
                    
                    log_message(20,'User successfully viewed availability status!'+f" USER:{current_user_email}")
                    return JSONResponse(content={'availablity_status':availablity_status})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing availability status! USER:{current_user_email}")
            return JSONResponse(content={'Error':"Couldn't fetch requested resource"}) 
    except:
        log_message(40,str(sys.exc_info())+"Invalid token error while viewing availability status!")
        return JSONResponse(content={"Error":"Invalid Token"})
    


async def changeAvailablityStatus(request_data:ChangeAvailablitySerializer, Authorize: AuthJWT=Depends()): 
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,"User trying to update the availability status"+f"USER:{current_user_email} INPUT:{request_data.dict()}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).where(User.email==current_user_email,User.email_verified==True)
                        user_obj = await SessionLocal.execute(user_obj_query)
                        user_obj = user_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch user_obj_query while changing availability status! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error changing availability status"})
                    
                    if user_obj.is_available_status==request_data.is_available_status:
                        log_message(f"Cannot change the status to previous state again while changing availability status! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error changing availability status"})
                    
                    try:
                        user_obj.is_available_status=request_data.is_available_status
                        SessionLocal.add(user_obj)
                    except:
                        log_message(30,str(sys.exc_info())+f"Error adding user_obj to session while changing availability status! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error changing availability status"})
                     
                    try:
                        punch_record_obj = AgentPunchRecord(user_id = user_obj.id,is_available_status=request_data.is_available_status)
                        SessionLocal.add(punch_record_obj)
                    except:
                        log_message(30,str(sys.exc_info())+f"Error adding punch_record_obj to session while changing availability status! USER:{current_user_email} INPUT:{request_data.dict()}")
                        return JSONResponse(content={"Error":"Error changing availability status"})
                    
                    
                await SessionLocal.commit()
                log_message(20,f"Availability status updated! USER:{current_user_email} INPUT:{request_data.dict()}")
                return JSONResponse(content={"message":"Availability status updated"})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while changing availability status! USER:{current_user_email} INPUT:{request_data.dict()}")
            return JSONResponse(content={'Error':'Error changing availability status!'}) 
    except Exception as e:
        log_message(40,str(sys.exc_info())+f"Invalid token error while changing availability status! INPUT:{request_data.dict()}")
        return JSONResponse(content={"Error": "Invalid token"})
  
  
  
async def currently_available_agent_list(Authorize: AuthJWT=Depends()):
    try:
        Authorize.jwt_refresh_token_required()
        current_user_email = Authorize.get_jwt_subject()
        log_message(10,f"User trying to view currently_available_agent_list! USER:{current_user_email}")
        try:
            async with settings.SessionLocal as SessionLocal:
                async with SessionLocal.begin_nested():
                    try:
                        user_obj_query = select(User).where(User.email==current_user_email,User.email_verified==True)
                        user_obj = await SessionLocal.execute(user_obj_query)
                        user_obj = user_obj.scalars().first()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch user_obj_query while viewing currently_available_agent_list! USER:{current_user_email}")
                        return JSONResponse(content={'Error':"Couldn't fetch requested resource!"})
                    
                    super_admin_id =  user_obj.super_admin_id
                    
                    try:
                        available_agents_query = select(User).filter(User.super_admin_id==super_admin_id,User.email_verified==True,or_(User.email_invitation_status==2,User.email_invitation_status==0))
                        available_agents = await SessionLocal.execute(available_agents_query)
                        available_agents = available_agents.scalars().all()
                    except:
                        log_message(40,str(sys.exc_info())+f"Couldn't fetch available_agents_query while viewing currently_available_agent_list!! USER:{current_user_email}")
                        return JSONResponse(content={"Error":"Couldn't fetch requested resource!"})
                    
                    available_agents = [ {"id":agent.id,
                                          "first_name":agent.first_name,
                                          "last_name":agent.last_name,
                                          "availability_status":agent.is_available_status} for agent in available_agents]
                    
                    log_message(20,'User successfully viewed currently_available_agent_list!'+f" USER:{current_user_email}")
                    return JSONResponse(content={'agents_list':available_agents})
        except:
            log_message(50,str(sys.exc_info())+f"Unknown error while viewing currently_available_agent_list! USER:{current_user_email}")
            return JSONResponse(content={'Error':"Couldn't fetch requested resource"}) 
    except:
        log_message(40,str(sys.exc_info())+"Invalid token error while viewing currently_available_agent_list!")
        return JSONResponse(content={"Error":"Invalid Token"})
    
    
    
async def changeConvOpenedStatus(request_data:ChangeConvOpenedSerializer):
   
    log_message(10,"Trying to update the conversation opened status"+ f"INPUT:{request_data.dict()}")
    try:
        async with settings.SessionLocal as SessionLocal:
            async with SessionLocal.begin_nested():
                try:
                    conv_obj_query = select(Conversation).filter(Conversation.conversation_uuid==request_data.conversation_id)
                    conv_obj = await SessionLocal.execute(conv_obj_query)
                    conv_obj = conv_obj.scalars().first()
                except:
                    log_message(40,str(sys.exc_info())+f"Couldn't fetch conv_obj_query while changing changeConvOpenedStatus ! INPUT:{request_data.dict()}")
                    return JSONResponse(content={"Error":"Error changing conversation opened status"})
                
                
                try:
                    conv_obj.conversation_opened=request_data.status
                    SessionLocal.add(conv_obj)
                except:
                    log_message(30,str(sys.exc_info())+f"Error adding conv_obj to session while changing changeConvOpenedStatus! INPUT:{request_data.dict()}")
                    return JSONResponse(content={"Error":"Error changing conversation opened status"})
                
            await SessionLocal.commit()
            log_message(20,f"Conversation opened status updated! INPUT:{request_data.dict()}")
            return JSONResponse(content={"message":"Conversation opened status updated!"})
    except:
        log_message(50,str(sys.exc_info())+f"Unknown error while changing conversation opened status! INPUT:{request_data.dict()}")
        return JSONResponse(content={'Error':'Error changing conversation opened status!'}) 
    
    
    
async def logfiles():
    log_folder_path='D:\\OneDrive - modefin.com\\chatbot with web sockets\\app_log\\logs'
    # log_folder_path='/srcchtfa/app/app_log/logs'
    all_log_files = [f for f in listdir(log_folder_path) if isfile(join(log_folder_path, f))]
    result_list = [{"file_date":file.split('.')[0],"file_path":str(settings.domain_name) + f"v2/api/single-log-file/{file.split('.')[0]}?page_number=1"} for file in all_log_files]
    return JSONResponse(content={"Log Files": result_list})



async def singleLogfile(file_name:str,page_number:int):
    log_file = 'D:\\OneDrive - modefin.com\\chatbot with web sockets\\app_log\\logs\\{}'.format(file_name + '.log')
    # log_file = '/srcchtfa/app/app_log/logs/{}'.format(file_name + '.log')
    if isfile(log_file)==True:
        with open(log_file,"r") as log:
            all_logs_list = log.read().split("-->>>")
            result=[]
            log_id=1
            for single_log in all_logs_list:
                if not single_log.startswith('>>>>>>'):
                    single_log = single_log.split("**")
                    log_dict={"id":log_id,"datetime":strip(single_log[0]),"level":single_log[2],"message":single_log[3]}
                    result.append(log_dict)
                    log_id+=1
            start_slice=(page_number - 1) * 100 #number of logs per page 
            end_slice=100*page_number
            result = result[start_slice:end_slice]
    else:
        result = "There is no log file for the requested file name"
    return JSONResponse(content={"Logs": result})


async def dashboard_page(request: Request): 
    return templates.TemplateResponse("dashboard.html", {"request": request})


async def ws_test_page(request: Request):  # RemProd Remove in production
    return templates.TemplateResponse("cookieTest.html", {"request": request})
