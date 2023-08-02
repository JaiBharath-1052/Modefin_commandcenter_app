# SQL Alchemy
from enum import unique
from typing import List
from sqlalchemy import Column, DateTime, Boolean, LargeBinary, Integer, String, ForeignKey, Text, ARRAY,Table, BigInteger,LargeBinary, Float, null
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import INTEGER, CHAR, TIMESTAMP, BYTEA, VARCHAR, ENUM,TEXT
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Time

from settings import default_profile_pic
import sqlalchemy.types as types
from sqlalchemy.exc import SQLAlchemyError
import re 



# Password hashing
import bcrypt

# Date&Time
import datetime
#Regex
import re 


# Define as metadata only for tracking migrations
Base = declarative_base()


# Custom Datatypes

class ChoiceType(types.TypeDecorator):

    impl = types.String

    def __init__(self, choices, **kw):
        self.choices = dict(choices)
        super(ChoiceType, self).__init__(**kw)

    def process_bind_param(self, value, dialect):
        return [k for k, v in self.choices.items() if v == value][0]

    def process_result_value(self, value, dialect):
        return self.choices[value]
    

class IntegerChoiceType(types.TypeDecorator):
    
    impl = types.Integer

    def __init__(self, choices, **kw):
        self.choices = dict(choices)
        super(IntegerChoiceType, self).__init__(**kw)

    def process_bind_param(self, value, dialect):
        return [k for k, v in self.choices.items() if v == value][0]

    def process_result_value(self, value, dialect):
        return self.choices[value]
    

    

# Many to many for User and Team
user_team_association = Table('user_team_association', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete="CASCADE")),
    Column('team_id', Integer, ForeignKey('team.id', ondelete="CASCADE"))
)


# User table
class User(Base):
    
    ROLE_CHOICES = {
            'SuperAdmin': 'SuperAdmin',
            'Admin': 'Admin',
            'Agent': 'Agent',
            'Operator': 'Operator'
        }
        
    
    NOTIFICATION_CHOICES = {
            'Sound1': 'Sound1',
            'Sound2': 'Sound2',
            'Sound3': 'Sound3',
            'Sound4': 'Sound4',
            'Sound5': 'Sound5'
        } 
    
    
    EMAIL_NOTIFICATION_CHOICES = {
            'all_conversations': 'all_conversations',
            'only_conversation_assigned_to_me': 'only_conversation_assigned_to_me',
            'donot_email_me_any_message_notifications': 'donot_email_me_any_message_notifications',
        }
        
    
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True,autoincrement=True, index=True)  #default id
    unique_id = Column(String(100), unique=True,nullable=False)
    first_name = Column(String(100),default="")  # first name
    last_name = Column(String(100),default="")  # last name
    email = Column(String(100), unique=True,index=True, nullable=False)  # user email
    password = Column(LargeBinary)  # password
    role = Column(ChoiceType(ROLE_CHOICES),default='Operator')  # role name
    email_verified = Column(Boolean, default=False)  # email verified or not
    email_verification_code = Column(String(100), unique=True,index=True)  # verification code
    designation = Column(String(100)) #Designation in the company
    country_code = Column(Integer) #country code for the phone number
    contact_number = Column(BigInteger) #phone number
    profile_photo = Column(LargeBinary, default=default_profile_pic) #user pro file photio
    email_notification = Column(ChoiceType(EMAIL_NOTIFICATION_CHOICES),default='only_conversation_assigned_to_me')
    is_available_status = Column(Boolean,default=False) 
    browser_notification_volume = Column(Integer, default=100) #1 to 100 value
    browser_notification_sound = Column(ChoiceType(NOTIFICATION_CHOICES),default='Sound1') #Sound tune for notification
    is_online = Column(Boolean, default=False) #user online or away status
    last_seen = Column(DateTime(timezone=True)) #time of away status
    is_invited = Column(Boolean, default=False) #the user is invited or not
    super_admin_id = Column(Integer) #invitors super_admin_id
    last_login = Column(DateTime(timezone=True),default=datetime.datetime.now)  # last_login_time 
    # last_logout = Column(DateTime(timezone=True),default=datetime.datetime.now)  # last_login_time 
    email_invitor_id = Column(Integer) #email invitor id 
    email_invitation_status = Column(Integer)
    last_fallback_emailed_time = Column(DateTime(timezone=True))
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now)  # info updated time
    
    
    company_id = Column(Integer, ForeignKey('company.id', ondelete="CASCADE")) #company foreign key (Many to one)
    company = relationship("Company", back_populates="users") #company object - Company
    
    default_team = relationship("DefaultTeam", foreign_keys='DefaultTeam.super_admin_id', back_populates="super_admin",uselist=False) #defaultteam object -DafaultTeam
    bots = relationship("Bot", back_populates="created_user") #bot list - BOT
    
    df_team_initial_assigned_user = relationship("DefaultTeam", foreign_keys='DefaultTeam.initial_assignment_id', back_populates="initial_assignment",uselist=False)
    
    df_team_noone_is_online_assigned_user = relationship("DefaultTeam",foreign_keys='DefaultTeam.user_assigned_when_noone_is_online_id', back_populates="user_assigned_when_noone_is_online",uselist=False)
    
    conv_rules_initial_assigned_user = relationship("ConversationRules", foreign_keys='ConversationRules.initial_assignment_id', back_populates="initial_assignment")
    
    conv_rules_noone_is_online_assigned_user = relationship("ConversationRules", foreign_keys = 'ConversationRules.user_assigned_when_noone_is_online_id', back_populates = "user_assigned_when_noone_is_online")
    
    
    punch_records = relationship("AgentPunchRecord", back_populates="user") #all punch records of user
    
    teams = relationship("Team",secondary=user_team_association,back_populates="team_members") #teams of user
    teams_if_teamlead = relationship("Team",back_populates="team_lead") #gives teams for which the user is team lead
    account_option = relationship("AccountOptions", uselist=False, back_populates="super_admin") #Account setting- One to One
    quick_replies = relationship("QuickReply", back_populates="super_admin") 
    pre_chat_lead_collection = relationship("PreChatLeadCollection", back_populates="super_admin",uselist=False)  #one to many
    chat_widget_customization = relationship("ChatWidgetCustomization",uselist=False, back_populates="super_admin") #One to one with CW-Cust
    chat_widget_configuration = relationship("ChatWidgetConfiguration", uselist=False,back_populates="super_admin") #One to one with CW-Config
    welcome_msg_configuration = relationship("WelcomeMessageConfiguration", uselist=False,back_populates="super_admin") #One to one with CW-Config
    greeting_message = relationship("GreetingMessage", back_populates="super_admin",uselist=False) #One to one with greeting_message
    away_message = relationship("AwayMessage", back_populates="super_admin", uselist=False) #One to one with AwayMessage
    help_center_category = relationship("HelpCenterCategory", back_populates="super_admin") #One to many with help_center_category
    
    articles_created = relationship("HelpCenterArticle", foreign_keys='HelpCenterArticle.author_id',back_populates="author")
    
    articles_edited = relationship("HelpCenterArticle",foreign_keys='HelpCenterArticle.last_edited_by', back_populates="last_editor")
    
    help_center_customization = relationship("HelpCenterCustomization", back_populates="super_admin",uselist=False) #One to many with help_center_customization
    conversations = relationship("Conversation",foreign_keys='Conversation.assigned_agent_id', back_populates="assigned_agent") #One to many with conversation
    all_customers = relationship("Customers", back_populates="super_admin") #One to many 
    all_account_conversations = relationship("Conversation",foreign_keys='Conversation.super_admin_id', back_populates="super_admin") #One to many with users
    assigned_conversations = relationship("Conversation", foreign_keys='Conversation.conversation_assignee_id',back_populates="conversation_assignee")
    all_tags = relationship("Tags", back_populates="super_admin") #One to many with users
    
    all_ratings = relationship("CsatRatings",foreign_keys='CsatRatings.super_admin_id',back_populates="super_admin") #One to many with users
    

    def __repr__(self):
        return "<User(id='%s', email='%s')>" % (self.id, self.email)
    
    def pass_hasher(self, password):
        self.password = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt())
    
    def pass_validator(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password)
    
    def is_valid_email(self,email):    
        regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
        if(re.search(regex,email)):  
            return True           
        else:  
            return False
    
    def serialize(self):
        user_dict={}
        user_dict["id"]=self.id
        user_dict["first_name"] = self.first_name
        user_dict["last_name"] =self.last_name
        user_dict["email"]=self.email
        user_dict["designation"]=self.designation
        user_dict["country_code"]= self.country_code
        user_dict["contact_number"]= self.contact_number
        user_dict["profile_picture"] = self.profile_photo.decode("utf-8")
        return user_dict
    
    def notification_preferences(self):
        result_dict = {}
        result_dict["email_notification"]=self.email_notification
        result_dict["browser_notification"]={}
        result_dict["browser_notification"]["notification_volume"]=self.browser_notification_volume
        result_dict["browser_notification"]["notification_sound"]=self.browser_notification_sound
        return result_dict
        
    
class AgentPunchRecord(Base): 
    __tablename__ = 'agent_punch_record'
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True)  #default id
    
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE")) #User - one to many
    user = relationship("User", back_populates="punch_records")
    
    is_available_status = Column(Boolean,nullable=False) 
    date = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_date
    
    def __repr__(self):
        return "<User(id='%s', is_available_status='%s', date='%s')>" % (self.id, self.is_available_status,self.date)


# class AgentChatHistory(Base): 
#     __tablename__ = 'agent_chat_history'
    
#     id = Column(Integer, primary_key=True,autoincrement=True, index=True)  #default id
    
#     user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE")) #User - one to many
#     user = relationship("User", back_populates="punch_records")

#     visitorID = Column(String, nullable=False) 
#     firstreply = Column(Integer, nullable=True)
#     duration = Column(Integer, nullable=True)
#     transferto = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"))
#     allocation_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_date
    
#     def __repr__(self):
#         return "<User(id='%s', added='%s', date='%s')>" % (self.id, self.is_available_status,self.date)

#Company table.
class Company(Base):
    __tablename__ = 'company'

    id = Column(Integer, primary_key=True,autoincrement=True, index=True)  #default id
    company_name = Column(String(100), nullable=True)  # company name
    company_url = Column(String(100), nullable=True)  #company url
    custom_domain_url = Column(String(100), nullable=True) #custom domain url
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now)# info updated time
    
    users = relationship("User", back_populates="company")
    
    def __repr__(self):
        return "<Company(id='%s', name='%s')>" % (self.id, self.company_name)
    
    def serialize(self):
        result_dict = {}
        result_dict["company"]={}
        result_dict["company"]["company_name"]=self.company_name
        result_dict["company"]["company_url"]=self.company_url
        result_dict["custom_domain_url"]=self.custom_domain_url
        return result_dict





#Default Team Table
class DefaultTeam(Base):
    __tablename__ = 'default_team'
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    super_admin_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"),unique=True) #super admin id (One to one)
    super_admin = relationship("User", foreign_keys=[super_admin_id],back_populates="default_team",lazy="subquery",uselist=False) #default superadmin object
    
    

    assign_new_conv_to_bot = Column(Boolean, default= False)
    
    
    bot_selected_id = Column(Integer, ForeignKey('bot.id', ondelete="CASCADE"),unique=True, nullable=True) #bot id for default team
    # bot_selected = relationship("Bot", back_populates="default_team_selected",uselist=False)
    bot_selected = relationship("Bot", foreign_keys=[bot_selected_id], back_populates="default_team_selected",uselist=False)
    
    
    notify_everybody = Column(Boolean, default = True) #routing rules for human
    
    initial_assignment_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE"),unique=True) #User id (notify every body - on)
    initial_assignment = relationship("User", foreign_keys=[initial_assignment_id], back_populates="df_team_initial_assigned_user",uselist=False)
    
    
    user_assigned_when_noone_is_online_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE"),unique=True) #User id (notify every body - off)
    user_assigned_when_noone_is_online = relationship("User", foreign_keys=[user_assigned_when_noone_is_online_id], back_populates="df_team_noone_is_online_assigned_user",uselist=False)
    
    
    
    teams = relationship("Team", back_populates="default_team") #team list present in default team
    
    bots = relationship("Bot",foreign_keys='Bot.default_team_id', back_populates="default_team")
    # bots = relationship("Bot", back_populates="default_team")
    
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    def __repr__(self):
        return "<DefaultTeam(id='%s', super_admin_id='%s')>" % (self.id, self.super_admin_id)



#Many to many for User and Team
bot_team_association = Table('bot_team_association', Base.metadata,
    Column('team_id', Integer, ForeignKey('team.id', ondelete="CASCADE"),nullable=False),
    Column('bot_id', Integer, ForeignKey('bot.id', ondelete="CASCADE"),nullable=False)
)



#Team Table
class Team(Base):
    __tablename__ = 'team'
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    team_name = Column(String(30), nullable=False) #team name
    
    
    default_team_id = Column(Integer, ForeignKey('default_team.id', ondelete="CASCADE"), nullable=False) #DefaultTeam - one to many
    default_team = relationship("DefaultTeam", back_populates="teams")
    
    team_lead_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False) #User - one to many
    team_lead = relationship("User", back_populates="teams_if_teamlead") #team lead user object 
    
    team_members = relationship(User,secondary=user_team_association,back_populates="teams")
    
    bots = relationship("Bot",secondary=bot_team_association,back_populates="teams")
    
    conv_rules = relationship("ConversationRules", back_populates="team") #One to many with conversation rules

    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    

    def __repr__(self):
        return "<Team(id='%s', team_name='%s')>" % (self.id, self.team_name)





#Bot Table
class Bot(Base):
    __tablename__ = 'bot'
    
    INTEGRATION_CHOICES = {
        'Dialogflow-ES':'Dialogflow-ES',
        'Dialogflow-CX': 'Dialogflow-CX',
        'Custom-Platform': 'Custom-Platform'
    }
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    bot_name = Column(String(30)) #bot name
    bot_photo = Column(LargeBinary, nullable=True) #profile of bot
    
    
    created_user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE")) #User - one to many
    created_user = relationship("User", back_populates="bots")
    
    teams = relationship("Team",secondary=bot_team_association,back_populates="bots") #gives teams of bot
    
    # default_team_selected = relationship("DefaultTeam", back_populates="bot_selected",uselist=False)
    default_team_selected = relationship("DefaultTeam",foreign_keys="DefaultTeam.bot_selected_id", back_populates="bot_selected",uselist=False)
    
    integration_platform = Column(ChoiceType(INTEGRATION_CHOICES), default = 'Dialogflow-ES') #integration name
    
    default_team_id = Column(Integer, ForeignKey('default_team.id', ondelete="CASCADE")) #Integrations - one to many
    default_team = relationship("DefaultTeam",foreign_keys=[default_team_id], back_populates="bots")
    # default_team = relationship("DefaultTeam", back_populates="bots")
    
    allow_human_handoff =  Column(Boolean, default=True) #allow human handoff
    
    is_active = Column(Boolean, default=False) 
 

    dialogflow_es = relationship("DialogFlowES", back_populates="bot", uselist=False)
    dialogflow_cx = relationship("DialogFlowCX", back_populates="bot", uselist=False)
    custom_bot_platform = relationship("CustomBotPlatform", back_populates="bot", uselist=False)
    
    conversations = relationship("Conversation", back_populates="assigned_bot") #One to many 
    conv_rules = relationship("ConversationRules", back_populates="bot_selected") #One to many with Conversation rules
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    def __repr__(self):
        return "<Bot(id='%s', bot_name='%s')>" % (self.id, self.bot_name)

    
    
   
    
    
    
    
#--------------------------------   INTEGRATIONS TABLE LIST  -------------------------------------------

#DIALOGFLOW ES
class DialogFlowES(Base):
    __tablename__ = 'dialogflow_es'
    
    LANGUAGE_CHOICES = {
        'English':'English',
        'Spanish':'Spanish',
        'German':'German',
        'Portuguese':'Portuguese',
        'French':'French'
    }
    
    REGION_CHOICES = {
        'US':'US',
        'Europe(Belgium)':'Europe(Belgium)',
        'Asia Pacific(Tokyo)':'Asia Pacific(Tokyo)',
        'Europe(London)':'Europe(London)',
        'Asia Pacific(Sydney)':'Asia Pacific(Sydney)'
    }
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    bot_id = Column(Integer, ForeignKey('bot.id', ondelete="CASCADE")) #Bot - one to one
    bot = relationship("Bot", back_populates="dialogflow_es", uselist=False)
    
    dialogflow_private_key = Column(Text) #private key json
    default_language = Column(ChoiceType(LANGUAGE_CHOICES), default='English') #default language
    default_region = Column(ChoiceType(REGION_CHOICES), default='US') #default region
    dialogflow_knowledge_base_id = Column(ARRAY(String,dimensions=1,as_tuple=False,zero_indexes=False) ,default=[]) #knowlwedge base id
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    def __repr__(self):
        return "<DialogFlowES(id='%s')>" % (self.id)

    
    

#DIALOGFLOW CX
class DialogFlowCX(Base):
    __tablename__ = 'dialogflow_cx'
    
    REGION_CHOICES = {
        'US':'US',
        'Europe(Belgium)':'Europe(Belgium)',
        'Asia Pacific(Tokyo)':'Asia Pacific(Tokyo)',
        'Europe(London)':'Europe(London)',
        'Asia Pacific(Sydney)':'Asia Pacific(Sydney)'
    }
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    bot_id = Column(Integer, ForeignKey('bot.id', ondelete="CASCADE"))
    bot = relationship("Bot", back_populates="dialogflow_cx", uselist=False)
    
    
    dialogflow_private_key = Column(Text) #private key json
    default_region = Column(ChoiceType(REGION_CHOICES), default='US') #default region
    agent_id = Column(String(100))
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    
    def __repr__(self):
        return "<DialogFlowCX(id='%s')>" % (self.id)
    
    


#Other Bot Platform
class CustomBotPlatform(Base):
    __tablename__ = 'custom_bot_platform'
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    platform_name = Column(String(50),nullable=False) 
    bot_id = Column(Integer, ForeignKey('bot.id', ondelete="CASCADE"))
    bot = relationship("Bot", back_populates="custom_bot_platform", uselist=False)
    
    webhook_url = Column(String(300))
    header_key = Column(String(100))
    header_value = Column(String(100))
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    def __repr__(self):
        return "<CustomBotPlatform(id='%s')>" % (self.id)   
 
#-----------------------------------------------------------------------------------------------------






    
#Account Options
class AccountOptions(Base):
    __tablename__ = 'account_options'
    
    TEAM_CHOICES = {
            'DefaultTeam': 'DefaultTeam',
            'Team': 'Team'
        }
    
    INTERVAL_CHOICES = {
            'hours': 'hours',
            'minutes': 'minutes'
        }
    
    
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    super_admin_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE"),unique=True) #super admin id
    super_admin = relationship("User", back_populates="account_option",uselist=False) #One to one with user
    
    app_id = Column(String(200), unique=True) #This is the app id for knowing from where the chat is coming(from which website) #installation
    
    csat_ratings_enabled = Column(Boolean, default=True) #CSAT rating
    send_fall_back_emails = Column(Boolean, default=True) #fall back emails
    
    first_conversation_assignment_option = Column(ChoiceType(TEAM_CHOICES),default="DefaultTeam") #default team or Team
    first_conversation_assignment_id = Column(Integer) #team or default_team id
    
    allow_conversation_reassignment = Column(Boolean, default=True) 
    reassignment_duration = Column(Integer, default=2)
    reassignment_interval_type = Column(ChoiceType(INTERVAL_CHOICES), default='minutes') #hour or min
    unassigned_bot_can_reply = Column(Boolean, default = False) 
    waiting_queue_status_on = Column(Boolean, default = False) #queue status
    maximum_concurrent_chats = Column(Integer, default=5) 
    auto_resolve_conversations = Column(Boolean, default=False)
    auto_resolve_message = Column(String(200), default="Sorry, We haven't heard you for a while, So we are resolving conversation. Please reachout again if any querys")
    company_email_for_conv_transcript = Column(String(100))
    send_transcripts_to_user = Column(Boolean, default=False)
    show_pseudonyms = Column(Boolean, default=True)
    operator_permissions = relationship("OperatorPermissions", uselist=False, back_populates="account_option")
       
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    def __repr__(self):
        return "<AccountOption(id='%s', super_admin_id='%s' )>" % (self.id, self.super_admin_id)
    

class OperatorPermissions(Base):
    __tablename__ = 'operator_permissions'
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    account_options_id = Column(Integer,ForeignKey('account_options.id', ondelete="CASCADE"),unique=True)
    account_option = relationship("AccountOptions", back_populates="operator_permissions",uselist=False) 
    
    allow_assign_to_teammates = Column(Boolean, default=False)
    allow_assign_back_to_bot = Column(Boolean, default=False)
    allow_reassign_to_team = Column(Boolean, default=False)
    
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    def __repr__(self):
        return "<OperatorPermissions(id='%s', account_options_id='%s' )>" % (self.id, self.account_options_id)
    
    
    
#Conversation Rules
class ConversationRules(Base):
    __tablename__ = 'conversation_rules'
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    team_id = Column(Integer,ForeignKey('team.id', ondelete="CASCADE"),unique=True) #team id
    team = relationship("Team", back_populates="conv_rules",uselist=False) 

    # conversation_assigned = Column(Boolean)    
    assign_new_conv_to_bot = Column(Boolean, default=False)
    
    bot_selected_id =  Column(Integer,ForeignKey('bot.id', ondelete="CASCADE")) #bot id
    bot_selected = relationship("Bot", back_populates="conv_rules") #One to many with bot
    
    notify_everybody = Column(Boolean, default=False) 
    
    
    
    initial_assignment_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE")) #User id (notify every body - on)
    initial_assignment = relationship("User", foreign_keys=[initial_assignment_id], back_populates="conv_rules_initial_assigned_user")
    
    
    user_assigned_when_noone_is_online_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE")) #User id (notify every body - off)
    user_assigned_when_noone_is_online = relationship("User", foreign_keys=[user_assigned_when_noone_is_online_id], back_populates="conv_rules_noone_is_online_assigned_user")
    
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    def __repr__(self):
        return "<ConversationRules(id='%s', team_id='%s' )>" % (self.id, self.team_id)
    




#Quick replies
class QuickReply(Base):
    __tablename__ = 'quick_reply'
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    super_admin_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE")) #superadmin id
    super_admin = relationship("User", back_populates="quick_replies") #One to many with users
    
    shortcut_message = Column(String(50))
    full_message = Column(String(300))
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    
    def __repr__(self):
        return "<QuickReply(id='%s', shortcut_message='%s' )>" % (self.id, self.shortcut_message)
    




#CHAT WIDGET CUSTOMIZATION
class ChatWidgetCustomization(Base):
    __tablename__ = 'chat_widget_customization'
    
    LAUNCHER_ICON_CHOICES = {
            'Default': 'Default',
            'Upload': 'Upload'
        }
    
    WIDGET_POSITION_CHOICES = {
            'Left': 'Left',
            'Right': 'Right'
        }
    
    NOTIFICATION_SOUND_CHOICES = {
            'Sound1': 'Sound1',
            'Sound2': 'Sound2',
            'Sound3': 'Sound3',
            'Sound4': 'Sound4',
            'Sound5': 'Sound5'
        }
    
    ICON_CHOICES = {
        '1':'1',
        '2':'2',
        '3':'3',
        '4':'4'
    }
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    super_admin_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE"),unique=True) #superadmin id
    super_admin = relationship("User", back_populates="chat_widget_customization",uselist=False) #One to one with users
    
    color = Column(String(50),  default='#5553b7')
    launcher_option = Column(ChoiceType(LAUNCHER_ICON_CHOICES), default='Default')
    default_icon_option = Column(ChoiceType(ICON_CHOICES),default='1')
    icon_image = Column(LargeBinary, nullable=True) #image should be added by default
    widget_position = Column(ChoiceType(WIDGET_POSITION_CHOICES),default='Left')
    show_branding = Column(Boolean, default=True)
    chat_notification_sound = Column(ChoiceType(NOTIFICATION_SOUND_CHOICES),default='Sound1')
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    
    def __repr__(self):
        return "<ChatWidgetCustomization(id='%s', super_admin_id='%s' )>" % (self.id, self.super_admin_id)
    
    
        
       



#CHAT WIDGET CONFIGURATION
class ChatWidgetConfiguration(Base):
    __tablename__ = 'chat_widget_configuration'
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    super_admin_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE"),unique=True) #superadmin id
    super_admin = relationship("User", back_populates="chat_widget_configuration",uselist=False) #One to one with user
    
    remove_chat_history_on_page_refresh = Column(Boolean, default=True)
    history_removal_days = Column(Integer, default=30)
    history_removal_hours = Column(Integer, default=0)
    history_removal_minutes = Column(Integer, default=0)
    bot_reply_delay = Column(Integer, default=0)
    allow_single_thread_conversation = Column(Boolean, default=False)
    disable_chat_widget =  Column(Boolean, default=False)
    domain_restriction_list = Column(ARRAY(String,dimensions=1,as_tuple=False,zero_indexes=False) ,default=[])
    add_text_to_speech = Column(Boolean, default=False)
    add_speech_to_text = Column(Boolean, default=False)
    hide_attachment = Column(Boolean, default=False)
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    def __repr__(self):
        return "<ChatWidgetConfiguration(id='%s', super_admin_id='%s' )>" % (self.id, self.super_admin_id)
    
         

#GREETING MESSAGE
class GreetingMessage(Base):
    __tablename__ = 'greeting_message'
    
    MESSAGE_OPTION_CHOICES = {
            'Option1': 'Option1',
            'Option2': 'Option2'
        }
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    super_admin_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE"),unique=True) #superadmin id
    super_admin = relationship("User", back_populates="greeting_message",uselist=False) #One to one with users

    greeting_message_enabled = Column(Boolean, default=False)
    msg_option_1 = Column(String(35),nullable=True)
    msg_option_2 = Column(String(150),nullable=True)
    msg_option_selected = Column(ChoiceType(MESSAGE_OPTION_CHOICES),default='Option1')
    greeting_trigger_time = Column(Integer, default=5)
    play_notification_sound = Column(Boolean, default=True)
    show_greeting_on_mobile = Column(Boolean, default=True)
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    def __repr__(self):
        return "<GreetingMessage(id='%s', super_admin_id='%s' )>" % (self.id, self.super_admin_id)
    
         
class PreChatLeadCollection(Base):
    __tablename__ = 'pre_chat_lead_collection'

    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    super_admin_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE")) #superadmin id
    super_admin = relationship("User", back_populates="pre_chat_lead_collection",uselist=False) #One to many with users
    
    enable_prechat_lead = Column(Boolean, default=False)
    prechat_lead_collection_heading = Column(String(200),default='') 
    
    pre_chat_lead_collection_fields = relationship("PreChatLeadCollectionFields", back_populates ="prechatlead_parent") 

    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    def __repr__(self):
        return "<PreChatLeadCollection(id='%s', super_admin_id='%s' )>" % (self.id, self.super_admin_id)
    

    
#PRE CHAT LEAD COLLECTION
class PreChatLeadCollectionFields(Base):
    __tablename__ = 'pre_chat_lead_collection_fields'

    FIELD_TYPE_CHOICES = {
            'Name': 'Name',
            'Email': 'Email',
            'Phone': 'Phone',
            'Other': 'Other'
        }
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    prechatlead_parent_id = Column(Integer,ForeignKey('pre_chat_lead_collection.id', ondelete="CASCADE")) 
    prechatlead_parent = relationship("PreChatLeadCollection", back_populates="pre_chat_lead_collection_fields") 
    
    is_mandatory = Column(Boolean)
    field_type = Column(ChoiceType(FIELD_TYPE_CHOICES), default='Other')
    field_name = Column(String(150))
    place_holder = Column(String(150))
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    def __repr__(self):
        return "<PreChatLeadCollectionField(id='%s', field_name='%s' )>" % (self.id, self.field_name)
    


#WELCOME MESSAGE
class WelcomeMessageConfiguration(Base):
    __tablename__ = 'welcome_message_configuration'
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    super_admin_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE"), unique = True) #superadmin id
    super_admin = relationship("User", back_populates="welcome_msg_configuration", uselist=False) #One to one with users
    
    show_welcome_message = Column(Boolean, default=False)
    collect_email_id = Column(Boolean, default=True)
    message_categories = Column(ARRAY(String,dimensions=1,as_tuple=False,zero_indexes=False) ,default=[],nullable=False)
    
    welcome_messages = relationship("WelcomeMessages", back_populates="welcome_msg_config")
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    

    def __repr__(self):
        return "<WelcomeMessageConfig(id='%s')>" % (self.id)
    
     
                    
            
                 
    
    

#WELCOME MESSAGE
class WelcomeMessages(Base):
    __tablename__ = 'welcome_messages'
    
    MESSAGE_CHOICES = {
        'Default': 'Default',
        'English': 'English',
        'French': 'French',
        'German': 'German',
        'Portuguese': 'Portuguese',
        'Spanish': 'Spanish'
    }
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    welcome_msg_config_id = Column(Integer,ForeignKey('welcome_message_configuration.id', ondelete="CASCADE"))
    welcome_msg_config = relationship("WelcomeMessageConfiguration", back_populates="welcome_messages")
    
    welcome_message = Column(String(200))
    message_category = Column(ChoiceType(MESSAGE_CHOICES), default='Default')
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    

    def __repr__(self):
        return "<WelcomeMessage(id='%s' msg='%s')>" % (self.id, self.welcome_message[:10]+"...")
    
         

#AWAY MESSAGE
class AwayMessage(Base):
    __tablename__ = "away_message"
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    super_admin_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE"),unique=True) #superadmin id
    super_admin = relationship("User", back_populates="away_message", uselist=False) #One to one with users
    
    show_away_message = Column(Boolean, default=False)
    collect_email_id = Column(Boolean, default=True)
    away_message_for_known = Column(String(300))
    away_message_for_unknown = Column(String(300))
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    def __repr__(self):
        return "<AwayMessage(id='%s', super_admin_id='%s' )>" % (self.id, self.super_admin_id)





       

#HELP CENTER CATEGORY
class HelpCenterCategory(Base):
    __tablename__ = "help_center_category"
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    super_admin_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE")) #superadmin id
    super_admin = relationship("User", back_populates="help_center_category") #One to many with users
    
   
    category_title = Column(String(300))
    category_description = Column(String(500)) 
    
    creator_id = Column(Integer)
    
    last_edited_by = Column(Integer)
    
    articles = relationship("HelpCenterArticle", back_populates="category") #One to many with HelpCenterCategory
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    
    def __repr__(self):
        return "<HelpCenterCategory(id='%s', category_title='%s' )>" % (self.id, self.category_title)



#HELP CENTER CATEGORY
class HelpCenterArticle(Base):
    __tablename__ = "help_center_article"
    
    STATUS_CHOICES = {
        "Draft":"Draft",
        "Published":"Published"
    }
    
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    category_id = Column(Integer,ForeignKey('help_center_category.id', ondelete="CASCADE")) #category id
    category = relationship("HelpCenterCategory", back_populates="articles") #One to many with HelpCenterCategory
    
   
    article_title = Column(String(300))
    article_description = Column(String(500))
    
    author_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE")) #user id
    author = relationship("User", foreign_keys=[author_id], back_populates="articles_created")
    
    
    status_and_visiblity = Column(ChoiceType(STATUS_CHOICES), default="Draft")
    
    last_edited_by = Column(Integer,ForeignKey('users.id', ondelete="CASCADE"))
    last_editor = relationship("User",foreign_keys=[last_edited_by], back_populates="articles_edited")
    
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    
    def __repr__(self):
        return "<HelpCenterArticle(id='%s', article_title='%s' )>" % (self.id, self.article_title)

    def set_widget_position(self, choice):
        if choice in ['Draft','Published']:
            self.status_and_visiblity= choice
        else:
            raise ValueError("The option entered is not present")
    





#HELP CENTER CUSTOMIZATION
class HelpCenterCustomization(Base):
    __tablename__ = "help_center_customization"
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    super_admin_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE"), unique=True) #superadmin id
    super_admin = relationship("User", back_populates="help_center_customization", uselist=False) #One to one with users
    
    primary_color = Column(String(10),  default='#5553B7')
    headline_text = Column(String(100), default='Hey, How can we help you?')
    searchbar_text = Column(String(100), default = 'Search Helpcenter')
    logo_image = Column(LargeBinary)
    fav_icon = Column(LargeBinary)
    show_branding = Column(Boolean, default=True)
    show_live_chat_in_helpcenter = Column(Boolean, default=False)
    homepage_title = Column(String(100), default='Help Center')
    google_tag_manager_id = Column(String(100))
    custom_domain_url = Column(String(100))
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    def __repr__(self):
        return "<HelpCenterCustomization(id='%s', super_admin_id='%s' )>" % (self.id, self.super_admin_id)





#CONVERSATION 
class Conversation(Base):
    __tablename__ = "conversation"
    
    CONVERSATION_STATUS_CHOICES = {
        'First-response-pending' : 'First-response-pending',
        'Open' : 'Open',
        'Resolved' : 'Resolved',
        'Spam' : 'Spam',
        'Queued' : 'Queued'
    }
    
    HANDLER_CHOICES = {
        'BOT' : 'BOT',
        'HUMAN' : 'HUMAN'
    }
    
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    
    super_admin_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE")) #superadmin id
    super_admin = relationship("User", foreign_keys=[super_admin_id],back_populates="all_account_conversations") #One to many with users
    
    conversation_uuid = Column(String(100), unique=True)
    

    customer_id = Column(Integer,ForeignKey('customers.id', ondelete="CASCADE"),nullable=False, unique=True) #end_user id
    customer = relationship("Customers", uselist=False, back_populates="conversation") #One to many with end users
    
    conversation_handler = Column(ChoiceType(HANDLER_CHOICES),default="BOT") #bot or human
    
    assigned_bot_id = Column(Integer,ForeignKey('bot.id', ondelete="CASCADE")) #bot id
    assigned_bot = relationship("Bot", back_populates="conversations") #One to many 
    
    
    assigned_agent_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE")) #user id
    assigned_agent = relationship("User", foreign_keys=[assigned_agent_id],back_populates="conversations") #One to many with users
    
    conversation_manually_assigned = Column(Boolean, default = False)
    
    conversation_assignee_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE")) #user id
    conversation_assignee = relationship("User", foreign_keys=[conversation_assignee_id],back_populates="assigned_conversations")
    
     
    send_transcript_to_user = Column(Boolean, default=False)
    end_user_conversation_status = Column(ChoiceType(CONVERSATION_STATUS_CHOICES), default='First-response-pending')
    
    conversation_tags = relationship("ConversationTags", back_populates="conversation")
    
    is_spam = Column(Boolean,default=False)
    
    conversation_deleted = Column(Boolean, default = False) 
    conversation_started = Column(Boolean, default = False)   
    conversation_opened = Column(Boolean,default=True)
    first_message_time = Column(DateTime(timezone=True), nullable = True)
    first_response_time = Column(DateTime(timezone=True), nullable = True)
    conversation_resolved_time = Column(DateTime(timezone=True), nullable = True)
    conv_handed_to_agent = Column(Boolean, default=False)
    
    
    rating = relationship("CsatRatings",back_populates="conversation")
    all_chats = relationship("ChatStorage", back_populates="conversation")
    
    last_contacted = Column(DateTime(timezone=True),default=datetime.datetime.now) #thi is the last contacted
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    def __repr__(self):
        return "<Conversation(uuid='%s')>" % (self.conversation_uuid)
    
    def serialize(self):
        conversation_dict = {}
        conversation_dict["conversation_id"] = self.conversation_uuid
        conversation_dict["conversation_handler"] = self.conversation_handler
        conversation_dict["customer"] = {}
        conversation_dict["customer"]["customer_id"] = self.customer.id
        if self.customer.got_real_name==True:
            customer_name = self.customer.customer_real_name
        else:
            customer_name=self.customer.customer_generated_name
        conversation_dict["customer"]["customer_name"] = customer_name
        conversation_dict["conversation_status"] = self.end_user_conversation_status
        conversation_dict["manually_assigned"] = self.conversation_manually_assigned
        conversation_dict["last_message_time"] = "12:50 PM"
        conversation_dict["tags"] = []
        for conv_tag_obj in self.conversation_tags:
            tag_obj_dict = {}
            tag_obj_dict["tag_id"]=conv_tag_obj.tag.id
            tag_obj_dict["tag_name"]=conv_tag_obj.tag.tag_name
            conversation_dict["tags"].append(tag_obj_dict)
        return conversation_dict



    
#STORAGE SYSTEM FOR CHATS
class ChatStorage(Base):
    __tablename__ = "chat_storage"
    
    SENDER_CHOICES = {
        'HUMAN' : 'HUMAN',
        'BOT' : 'BOT',
        'CUSTOMER':'CUSTOMER',
        'SERVER':'SERVER'
    }
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    conversation_id = Column(Integer,ForeignKey('conversation.id', ondelete="CASCADE")) 
    conversation = relationship("Conversation", back_populates="all_chats") 
     
    response = Column(Text)
    confidence_level = Column(Float,nullable=True)
    intent_detected = Column(String(100),nullable=True)
    
    sender = Column(ChoiceType(SENDER_CHOICES),default="BOT")
    sender_id = Column(String(100),nullable=True)
    
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    
    def __repr__(self):
        return "<Chat(id='%s', message='%s' )>" % (self.id, self.response[0:15])
    
    




#RATINGS FOR CONVERSATION
class CsatRatings(Base):
    
    RATING_CHOICES = {
        1 : 1, #Poor
        5 : 5, #Average
        10 : 10 #Great
    }
    
    __tablename__ = 'csat_ratings'
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #id
    
    super_admin_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE")) #superadmin id
    super_admin = relationship("User",back_populates="all_ratings") #One to many with users
    
    conversation_id = Column(Integer,ForeignKey('conversation.id', ondelete="CASCADE")) 
    conversation = relationship("Conversation",back_populates="rating") 
     
    
    rating = Column(IntegerChoiceType(RATING_CHOICES),default=5)
    comment = Column(TEXT, nullable=True)
    
    def __repr__(self):
        return "<Ratings(id='%s', rating='%s' )>" % (self.id, self.rating)
   
    
class Tags(Base):
    __tablename__ = "tags"
    
    id=Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    tag_name = Column(String, nullable=False)
    
    super_admin_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE")) #superadmin id
    super_admin = relationship("User",back_populates="all_tags") #One to many with users
    
    conversation_tags = relationship("ConversationTags", back_populates="tag")
    
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    

    def __repr__(self):
        return "<Tag(id='%s', tagname='%s' )>" % (self.id, self.tag_name)


    
class ConversationTags(Base):
    __tablename__ = "conversation_tag"
    

    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    
    tag_id=Column(Integer,ForeignKey('tags.id', ondelete="CASCADE"))
    tag = relationship("Tags", back_populates="conversation_tags")
    
    conversation_id= Column(Integer,ForeignKey('conversation.id', ondelete="CASCADE")) 
    conversation = relationship("Conversation", back_populates="conversation_tags")
    
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    

    def __repr__(self):
        return "<ConversationTag(conv_id='%s', tag_id='%s' )>" % (self.conversation_id, self.tag.tag_name)




#END USER
class Customers(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) #default id
    
    
    super_admin_id = Column(Integer,ForeignKey('users.id', ondelete="CASCADE")) #superadmin id
    super_admin = relationship("User", back_populates="all_customers") #One to many with users
    
    
    customer_generated_name  = Column(String(100),unique=True)
    
    got_real_name = Column(Boolean, default=False)
    customer_real_name  = Column(String(100))
    customer_phone_number = Column(BigInteger)
    customer_email = Column(String(100))
    
    is_deleted = Column(Boolean, default = False)
    is_blocked = Column(Boolean, default = False)
    
    is_online = Column(Boolean, default=True) #user online or away status
    last_seen = Column(DateTime(timezone=True)) #time of away status
    
    
    # conversations = relationship("Conversation",back_populates="customer")
    conversation = relationship("Conversation",uselist=False,back_populates="customer")
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  # created_time
    last_fallback_emailed_time = Column(DateTime(timezone=True))
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now) #updated
    
    
    def __repr__(self):
        return "<Customer(id='%s', customer_name='%s' )>" % (self.id, self.customer_generated_name)



#END USER
class EmailTemplates(Base):
    __tablename__ = "email_templates"
    
    id = Column(Integer, primary_key=True,autoincrement=True, index=True) 
    template_name = Column(String(100),unique=True,index=True,nullable=False)
    message_subject = Column(Text)
    message_template = Column(Text)
    created_time = Column(DateTime(timezone=True),default=datetime.datetime.now)  
    updated_time = Column(DateTime(timezone=True),default=datetime.datetime.now,onupdate=datetime.datetime.now)
    
    
    def __repr__(self):
        return "<Template(id='%s', name='%s' )>" % (self.id, self.template_name)



if __name__ == '__main__':
    from sqlalchemy.ext.asyncio import create_async_engine
    import asyncio

    # from .. import settings 
    DEBUG = False
    DATABASE_URL = "postgresql+asyncpg://postgres:54321@mode@localhost:5432/chatapi2"
    engine = create_async_engine(DATABASE_URL, echo=DEBUG)
    
    
    async def chuche():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # await conn.run_sync(Base.metadata.drop_all)
            
    asyncio.run(chuche())
    
    
