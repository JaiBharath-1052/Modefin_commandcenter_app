from sqlalchemy.sql.elements import conv
from .dbconnection import fetchSingle,fetchMany,updateObject
# from .redis import addServerMessage
from models import *
from sqlalchemy import select
from typing import Dict, Optional
from datetime import datetime,timedelta,timezone
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, or_
import random
import time
import traceback
from .exceptions import *
import settings
from fastapi_mail import FastMail, MessageSchema
import asyncio
from fastapi import BackgroundTasks
import json
import uuid
from app_log.logModule import log_message
import sys
from datetime import timedelta,datetime
from email_template_filler import email_templates
from models import EmailTemplates
    


async def changeAwayMessage(sender, sender_id, status):   
    if sender == "customer":
        query= select(Customers).filter(Customers.customer_generated_name==sender_id)
        user_obj = await fetchSingle(query)
        user_obj.is_online = status
    
    if sender == "agent":
        query= select(User).filter(User.id==int(sender_id))
        user_obj = await fetchSingle(query)
        user_obj.is_online = status

    if status == False:
        user_obj.last_seen = datetime.now()
        
    await updateObject(user_obj)
    return {"success": True}



        
        
        
#Currently Loggedin, Available and Websocket Connected agents, inorder to assign them to conversation
async def get_free_agent(conv_conn_manager,super_admin_id,team_id: Optional[int] = None):
    log_message(10,f"User trying to access get_free_agent function with Inputs: super_admin_id = {super_admin_id}, team_id = {team_id}")
    # try:
    if team_id==None:
        
        agent_objs_query = select(User).options(selectinload(User.conversations)).filter(
            User.super_admin_id == super_admin_id, 
            User.is_online==True,
            User.is_available_status==True)
        all_agent_objs = await fetchMany(agent_objs_query)
        
        active_agent_connections = list(conv_conn_manager.active_agent_connections.keys())
        
        #Here we will get all the free agent ids who are currently availavle for chat and websocket connected
        free_agent_objs = list(filter(lambda x:x.unique_id in active_agent_connections,all_agent_objs))
        #agent_today_convs = {agent:4,agent:9}
        agent_today_conv_nos = {}
        
        for agent in free_agent_objs:
            
            conversation_count = len(list(filter(lambda x:x.created_time.date()==datetime.today().date(),agent.conversations)))
            agent_today_conv_nos[agent]=conversation_count
            
        sorted_agent_list=dict(sorted(agent_today_conv_nos.items(), key=lambda item: item[1]))
        free_agent_list = list(sorted_agent_list.keys())
        if free_agent_list!=[]:
            free_agent=free_agent_list[0]
            return free_agent
        else:
            return None
    else:
        team_query = select(Team).options(selectinload(Team.team_members)).filter(Team.id==team_id)
        team_obj = await fetchSingle(team_query)
        
        team_members = team_obj.team_members
        
        team_agent_objs = list(filter(
            lambda x:x.is_online == True 
            and x.super_admin_id==super_admin_id
            and x.is_available_status==True, team_members))
        
        active_agent_connections = list(conv_conn_manager.active_agent_connections.keys())
        
        #Here we will get all the free agent ids who are currently availavle for chat and websocket connected
        free_agent_objs = list(filter(lambda x:x.unique_id in active_agent_connections,team_agent_objs)) 

        #agent_today_convs = {agent:4,agent:9}
        agent_today_conv_nos = {}
        for agent in free_agent_objs:
            conversation_count = len(list(filter(lambda x:x.created_time==datetime.today().date(),agent.conversations)))
            agent_today_conv_nos[agent]=conversation_count
        
        sorted_agent_list=dict(sorted(agent_today_conv_nos.items(), key=lambda item: item[1]))
        free_agent_list = list(sorted_agent_list.keys())
        if free_agent_list!=[]:
            free_agent=free_agent_list[0]
            return free_agent
        else:
            return None
    # except:
    #     log_message(40,str(sys.exc_info())+f"Some unknown error while accessing get_free_agent function! INPUT: super_admin_id = {super_admin_id}, team_id = {team_id}")
        
    
#GIVES THE CONVERSATION HANDLER AND THE CONVERSATION TO BE ASSIGNED TO WHN A NEW CONVERSATION OBJECT IS CREATED
#This will give the next assignable user or bot based on the conversation rules.
async def conversationAssigner(conv_conn_manager,super_admin_id):
    try:
        log_message(10,f"User trying to execute ConvAssigner function super_admin_id={super_admin_id}")
        super_admin_query = select(User).options(
            selectinload(User.account_option),
            selectinload(User.default_team).options(
                selectinload(DefaultTeam.bot_selected),
                selectinload(DefaultTeam.initial_assignment),            
                selectinload(DefaultTeam.user_assigned_when_noone_is_online),            
                selectinload(DefaultTeam.teams).options(
                    selectinload(Team.conv_rules).options(
                        selectinload(ConversationRules.initial_assignment),
                        selectinload(ConversationRules.bot_selected),
                        selectinload(ConversationRules.user_assigned_when_noone_is_online)
                    ))
                )
            ).filter(User.id==super_admin_id)
        
        super_admin = await fetchSingle(super_admin_query)
        conv_assignment_option = super_admin.account_option.first_conversation_assignment_option
        
        
        if conv_assignment_option == "DefaultTeam":
            default_team=super_admin.default_team
            
            if default_team.assign_new_conv_to_bot == True:
            #Assign the conv to selected bot
                bot_selected = default_team.bot_selected
                return ("BOT",bot_selected )
                        
            else: #False
            #Assign the conv to human based on routing rules
            
                if default_team.notify_everybody == True:
                    #Here we will get the user id who should be assigned initially
                    initial_assignment_user = default_team.initial_assignment
                    #Now return the id to be assigned in conv object
                    return ("HUMAN",initial_assignment_user)
                
                else: #False
                #Automatic assignment to users who are online on round robin basis
                    free_agent = await get_free_agent(conv_conn_manager,super_admin_id)
                    #If there are online agents
                    if free_agent !=None:
                        #(conversation_handler, handler_id)
                        return ("HUMAN",free_agent)
                    
                    else: #There are no users online
                        #This will be the user whom the conversation will be assigned if no one is online
                        assignable_user = default_team.user_assigned_when_noone_is_online
                        return ("HUMAN",assignable_user)
                    
                    
                    
                
        else: #Team
            team_id=super_admin.account_option.first_conversation_assignment_id
            all_teams = super_admin.default_team.teams
            team_obj = list(filter(lambda x:x.id == team_id, all_teams))
            
            if team_obj == []:
                raise ValueError
            
            team_obj = team_obj[0]
            
            if team_obj.conv_rules.assign_new_conv_to_bot == True:
                #Assign the conv to selected bot
                bot_selected = team_obj.conv_rules.bot_selected
                return ("BOT",bot_selected )
            
            else:#False
            #Assign the conv to human based on routing rules
            
                if team_obj.conv_rules.notify_everybody == True:
                    #Here we will get the user id who should be assigned initially
                    initial_assignment_user = team_obj.conv_rules.initial_assignment
                    #Now return the id to be assigned in conv object
                    #(conversation_handler, handler_id)
                    return ("HUMAN",initial_assignment_user)
                
                else: #False
                #Automatic assignment to users who are online on round robin basis
                    free_agent = await get_free_agent(conv_conn_manager, super_admin_id,team_obj.id)
                    #If there are online agents
                    if free_agent !=None:
                        #Now return the id to be assigned in conv object
                        #(conversation_handler, handler_id)
                        return ("HUMAN",free_agent)
                    
                    else: #There are no users online
                        #This will be the user whom the conversation will be assigned if no one is online
                        assignable_user = team_obj.conv_rules.user_assigned_when_noone_is_online
                        return ("HUMAN",assignable_user)
    except:
        log_message(40,str(sys.exc_info())+f"Some unknown error while executing CoonvAssigner function super_admin_id={super_admin_id}")       
        



    
#This function should give the chats of the particular conversation based on the given time so that we can send those chats to the emails.
async def getTimeBasisChats(conversation_id, start_time):
    conversation_query = select(Conversation).filter(Conversation.conversation_uuid == conversation_id)
    conv_obj = await fetchSingle(conversation_query)
    chats_list_query = select(ChatStorage).filter(ChatStorage.conversation_id ==  conv_obj.id, ChatStorage.created_time>=start_time)
    chats_list = await fetchMany(chats_list_query)
    chats_list = list(filter(lambda x:x.sender != 'SERVER',chats_list))
    
    chat_str = ''
    for chat_element in chats_list:
        val=json.loads(chat_element.response)["message"]["content"]["text"]
        chat_str = chat_str + f"<p>{val}</p>"
    return chat_str



#This function will send the email notification to te people based on notification preferences setting if the conversation is not replied for certain time.
#This function sends email only when the new conversation enters
async def sendEmailNotification(conv_id:str):
    current_time = datetime.now(timezone.utc)
    
    # Wait for 5 minutes and then send the email if the message is not responded
    await asyncio.sleep(5*60)
    
    conversation_query = select(Conversation).options(
        selectinload(Conversation.assigned_agent),
        selectinload(Conversation.customer)
        ).filter(Conversation.conversation_uuid==conv_id)
    conv_obj = await fetchSingle(conversation_query)
     
    if conv_obj.end_user_conversation_status == "First-response-pending":
        if conv_obj.conversation_handler == "HUMAN":
            #Check whether the agent is currently offline or not.
            assigned_agent = conv_obj.assigned_agent
            
            if assigned_agent.is_available_status == False:
                #Now send the email notification of the new conversation to the agents based on their notification preferences.
                if assigned_agent.email_notification in ['all_conversations','only_conversation_assigned_to_me']:
                    mail = FastMail(settings.conf)
                    
                    email_query = select(EmailTemplates).filter(EmailTemplates.template_name=='send_email_notification_template')
                    mail_data_obj = await fetchSingle(email_query)
                    
                    chats = await getTimeBasisChats(conv_id,current_time)
                    
                    message = MessageSchema(
                    subject=mail_data_obj.message_subject,
                    recipients=[assigned_agent.email],  # List of recipients, as many as you can pass 
                    body=mail_data_obj.message_template.formt(chats),
                    subtype="html"
                    )
                    await mail.send_message(message)
                    
                    users_query = select(User).filter(User.super_admin_id == conv_obj.customer.super_admin_id, User.id != assigned_agent.id)
                    users =  await fetchMany(users_query)
                    
                    users = list(filter(lambda x:x.email_notification =="all_conversations",users))
                    
                    users_emails = [user.email for user in users]
                    if users_emails != []:
                        message = MessageSchema(
                        subject = f"Missed message notification!",
                        recipients = users_emails,  # List of recipients, as many as you can pass 
                        body = f'''<h1>Some agent has missed the conversation from the customer. Please attend!</h1>
                                <br>
                                {chats}''',
                        subtype = "html"
                        )
                        await mail.send_message(message)
    
 
#This is the function which sends the mail to the agent or the customers,if they miss the conversation by going offline.
async def sendFallbackEmail(conversation_id,email_to):
    current_time = datetime.now(timezone.utc)
    
    await asyncio.sleep(1*60)  #wait for 1 min and then send the fallback email 
    
    conversation_query = select(Conversation).options(
        selectinload(Conversation.super_admin),
        selectinload(Conversation.assigned_agent),
        selectinload(Conversation.customer).options(
            selectinload(Customers.super_admin).options(
                selectinload(User.account_option)
                )
            )
        ).filter(Conversation.conversation_uuid==conversation_id)
    conv_obj = await fetchSingle(conversation_query)
    
    
    if email_to == 'Customer':
        last_fallback_emailed_time = conv_obj.customer.last_fallback_emailed_time
    else:
        last_fallback_emailed_time = conv_obj.assigned_agent.last_fallback_emailed_time
        
    if last_fallback_emailed_time == None:
        send_email = True
    else:
        
        # if in last 2 mins a fallback email is sent then a new fallback email should not be sent again
        if current_time-timedelta(minutes=2)>=last_fallback_emailed_time:
            send_email = True
        else:
            send_email = False
    
    
    if send_email == True:
        if conv_obj.end_user_conversation_status != 'First-response-pending':
            if conv_obj.super_admin.account_option.send_fall_back_emails==True:
                if email_to == 'Customer':
                    if conv_obj.customer.email !=None:
                        recipients=[conv_obj.customer.email]
                    else:
                        recipients = []
                else: #Agent
                    recipients=[conv_obj.assigned_agent.email]
                    
                chats = await getTimeBasisChats(conv_obj.conversation_uuid,current_time-timedelta(seconds=5))
                mail = FastMail(settings.conf)  
                
                email_query = select(EmailTemplates).filter(EmailTemplates.template_name == 'fallback_email_template')
                mail_data_obj = await fetchSingle(email_query)
                    
                      
                message = MessageSchema(
                            subject=mail_data_obj.message_subject,
                            recipients=recipients,
                            body=mail_data_obj.message_template.format(chats),
                            subtype="html"
                            ) 
                
                await mail.send_message(message)
                
                if email_to == 'Customer':
                    conv_obj.customer.last_fallback_emailed_time = current_time
                    await updateObject(conv_obj)
                else:
                    conv_obj.assigned_agent.last_fallback_emailed_time = current_time
                    await updateObject(conv_obj)
    
                
            
        

    
# =========================== MANUAL CONVERSATION RE-ASSIGNMENT TO TEAM MEMBERS ==================================
#This is when we have to assign a conversation to a team a conversation will be assigned to the person in tht team
async def convReassignToTeam(conv_conn_manager,super_admin_id,team_id: Optional[int] = None):
    log_message(10,f"User trying to access convReassignToTeam function, super_admin_id = {super_admin_id}, team_id={team_id}")
    
    super_admin_query = select(User).options(
        selectinload(User.account_option),
        selectinload(User.default_team).options(
            selectinload(DefaultTeam.teams).options(
                selectinload(Team.conv_rules).options(
                    selectinload(ConversationRules.initial_assignment),
                    selectinload(ConversationRules.user_assigned_when_noone_is_online)
                )
                ),
            selectinload(DefaultTeam.initial_assignment),
            selectinload(DefaultTeam.user_assigned_when_noone_is_online)
            )
        ).filter(User.id==super_admin_id)
    super_admin = await fetchSingle(super_admin_query) 
    
     
    if team_id == None:         
        default_team=super_admin.default_team
        
        #Assign the conv to human based on routing rules
        if default_team.notify_everybody == True:
            #Here we will get the user  who should be assigned initially
            initial_assignment_user = default_team.initial_assignment
            #Now return the agent to be assigned in conv object
            return initial_assignment_user
        
        else: #False
        #Automatic assignment to users who are online on round robin basis
            free_agent = await get_free_agent(conv_conn_manager,super_admin_id)
            
            #If there are online agents
            if free_agent !=None:
                return free_agent
            
            else: #There are no users online
                assignable_user = default_team.user_assigned_when_noone_is_online
                return assignable_user
            
    else: #Team id is present
        all_teams = super_admin.default_team.teams
        team_obj = list(filter(lambda x:x.id == team_id, all_teams))
        
        if team_obj == []:
            raise ValueError
        
        team_obj = team_obj[0]
        #Assign the conv to human based on routing rules
        
        if team_obj.conv_rules.notify_everybody == True:
            #Here we will get the user who should be assigned initially
            initial_assignment_user = team_obj.conv_rules.initial_assignment
            #Now return the agent to be assigned in conv object
            return initial_assignment_user
        
        else: #False
        #Automatic assignment to users who are online on round robin basis
            free_agent = await get_free_agent(conv_conn_manager,super_admin_id,team_obj.id)
            
            #If there are online agents
            if free_agent !=None:
                #Now return the agent to be assigned in conv object
                return free_agent
            
            else: #There are no users online
                #This will be the user whom the conversation will be assigned if no one is online
                assignable_user = team_obj.conv_rules.user_assigned_when_noone_is_online
                return assignable_user
            
        
        



#This is the manually assigning conversation to particular human or team or bot        
async def assignConversationToOthers(conv_conn_manager,input_data):
    try:
        log_message(10,f"User trying to access assignConversationToOthers function, input_data = {input_data}")
        conversation_id = input_data["conversation_id"]
        assignee_type=input_data["assignee_type"]
        assignee_id=input_data["assignee_id"]
        is_default=input_data["is_default"]

            
        try:
            conversation_query = select(Conversation).filter(Conversation.conversation_uuid==conversation_id)
            conversation_obj = await fetchSingle(conversation_query)
        except:
            log_message(40,f"conversation_query fetch error while executing assignConversationToOthers function, input_data = {input_data}")
            return {"success":False,"errormsg":"Some error occured while assigning conversation to others"}
        
        if conversation_obj==None:
            log_message(40,f"There is no conversation object for the requested id while executing assignConversationToOthers function, input_data = {input_data}")
            return {"success":False,"errormsg":"Some error occured while assigning conversation to others"}
            

        if assignee_type == "BOT":
            #fetch the bot object with assignee id
            try:
                assignee_query = select(Bot).filter(Bot.id==assignee_id)
                assignee_obj = await fetchSingle(assignee_query)
            except:
                log_message(40,f"assignee_query fetch error while executing assignConversationToOthers function, input_data = {input_data}")
                return {"success":False,"errormsg":"Some error occured while assigning conversation to others"}
            
            if assignee_obj == None:
                log_message(40,f"There is no bot assignee object for the requested id while executing assignConversationToOthers function, input_data = {input_data}")
                return {"success":False,"errormsg":"Some error occured while assigning conversation to others"}
            
            conversation_obj.assigned_bot =assignee_obj                        
            conversation_obj.conversation_handler = "BOT"
            conversation_obj.conversation_manually_assigned = True
            
        
        elif assignee_type == "HUMAN":
            #fetch the human object with assignee id
            try:
                assignee_query = select(User).filter(User.unique_id==assignee_id)
                assignee_obj = await fetchSingle(assignee_query)
            except:
                log_message(40,f"Some error occured while fetching assignee query while executing assignConversationToOthers function, input_data = {input_data}")
                return {"success":False,"errormsg":"Some error occured while assigning conversation to others"}
            
            if assignee_obj == None:
                log_message(40,f"There is no human assignee object for the requested id while executing assignConversationToOthers function, input_data = {input_data}")
                return {"success":False,"errormsg":"Some error occured while assigning conversation to others"}
            
            conversation_obj.assigned_agent =assignee_obj                        
            conversation_obj.conversation_handler = "HUMAN"
            conversation_obj.conversation_manually_assigned = True
            
        
            
        elif assignee_type == "TEAM": #TEAM
            
            if is_default == True:
                #fetch the default team object and take members from there and assign
                assignable_agent = await convReassignToTeam(conv_conn_manager,conversation_obj.super_admin_id)
            else:
                #fetch the given team object, and take members from that team assign 
                try:
                    assignable_agent = await convReassignToTeam(conv_conn_manager,conversation_obj.super_admin_id,assignee_id)
                except:
                    return {"success":False,"errormsg":"Some error occured while assigning conversation to others"}
            
            conversation_obj.assigned_agent_id =assignable_agent                        
            conversation_obj.conversation_handler = "HUMAN"
            conversation_obj.conversation_manually_assigned = True
                

        else:
            log_message(40,f"Assignee type is undefined while executing assignConversationToOthers function, input_data = {input_data}")
            return {"success":False,"errormsg":"Some error occured while assigning conversation to others"}
        
        try:
            conversation_obj= await updateObject(conversation_obj)
        except:
            log_message(40,f"Some error occured while updating conversation_obj while executing assignConversationToOthers function, input_data = {input_data}")
            return {"success":False,"errormsg":"Some error occured while assigning conversation to others"}
        
        log_message(20,f"assignConversationToOthers function executed successfully!, input_data = {input_data}")
        
        if conversation_obj.conversation_handler=="HUMAN":
            assignee_name = str(conversation_obj.assigned_agent.first_name) + ' ' + str(conversation_obj.assigned_agent.last_name)
        else:
            assignee_name = str(conversation_obj.assigned_bot.bot_name)
        
        return {"success":True,"message":f"Conversation assigned to {assignee_name}"}
    except:
        log_message(40,str(sys.exc_info())+f"Some unknown error while accessing assignConversationToOthers function! , input_data = {input_data}") 
        return {"success":False,"errormsg":"Some error occured while assigning conversation to others"}

 


#This function takes the input customer_id and app id , and then returns the convversation object for that customer
async def getConversation(conv_conn_manager,customer_id:str,app_id:str):
    log_message(10,f"User trying to get conversation object with the inputs, customer_id={customer_id}, app_id={app_id}")
    # try:
    customer_query = select(Customers).filter(Customers.customer_generated_name==customer_id)
    customer_obj = await fetchSingle(customer_query)
    
    #If there is no customer object, (ie.,a new customer enteres) a new customer object is created and a new conversation object is created with the conversation handler assignment based on conversation rules.
    if customer_obj==None:
        
        account_options_query = select(AccountOptions).filter(AccountOptions.app_id==app_id)
        account_options_obj = await fetchSingle(account_options_query)
    
        super_admin_id = account_options_obj.super_admin_id
        
        customer_obj = Customers(super_admin_id=super_admin_id, customer_generated_name=customer_id)
        
        if account_options_obj.show_pseudonyms == True:
            customer_obj.customer_real_name = await generateCustomerName()
        customer_obj = await updateObject(customer_obj)
        
        conv_obj=Conversation(super_admin_id=super_admin_id, conversation_uuid = uuid.uuid4().hex, customer_id = customer_obj.id, end_user_conversation_status = 'First-response-pending')
        
            
        #This returns to whom the conversation to be assigned(ie, Bot or Human and returns that instance)
        conv_asignment = await conversationAssigner(conv_conn_manager,super_admin_id)
        
        if conv_asignment[0]=="HUMAN":
            conv_obj.conversation_handler = conv_asignment[0]
            conv_obj.assigned_agent = conv_asignment[1]
        else: #BOT
            conv_obj.conversation_handler = conv_asignment[0]
            conv_obj.assigned_bot = conv_asignment[1]
            
        conv_obj=await updateObject(conv_obj)
        log_message(20,f"A new conversation object is created, customer_id={customer_id}, conversation_id={conv_obj.conversation_uuid}")
    else:
        #If customer is already present now we will fetch the conversation object for that and we have to update that conversation handler.
        conversation_query = select(Conversation).options(
            selectinload(Conversation.assigned_agent),
            selectinload(Conversation.assigned_bot),
            selectinload(Conversation.super_admin).options(
                selectinload(User.account_option),
                selectinload(User.default_team).options(
                    selectinload(DefaultTeam.user_assigned_when_noone_is_online),
                    selectinload(DefaultTeam.teams).options(
                        selectinload(Team.conv_rules).options(
                            selectinload(ConversationRules.user_assigned_when_noone_is_online)
                            )
                        )
                    )
                )
            ).filter(Conversation.customer_id==customer_obj.id)
        conv_obj = await fetchSingle(conversation_query)
        
        #if the previously handled user is online , then let him handle the conversation
        #if the previously handled user is not online then update the conversation handler with available free agent
        # if conv_obj.conversation_handler == "HUMAN":
        #     assigned_agent = conv_obj.assigned_agent
            
        #     if conv_conn_manager.active_agent_connections.get(assigned_agent.unique_id,None)==None:
                
        #         conv_assignment_option = conv_obj.super_admin.account_option.first_conversation_assignment_option
    
        #         if conv_assignment_option == "DefaultTeam":
        #             free_agent = await get_free_agent(conv_conn_manager,conv_obj.super_admin.id)
        #             if free_agent!=None:
        #                 conv_obj.assigned_agent = free_agent
        #             else:
        #                 conv_obj.assigned_agent = conv_obj.super_admin.default_team.user_assigned_when_noone_is_online
                        
        #         else: #Team
        #             team_id = conv_obj.super_admin.account_option.first_conversation_assignment_id
        #             free_agent = await get_free_agent(conv_conn_manager,conv_obj.super_admin.id, team_id)
        #             if free_agent!=None:
        #                 conv_obj.assigned_agent = free_agent
        #             else:
        #                 all_teams = conv_obj.super_admin.default_team.teams
        #                 team_obj = list(filter(lambda x:x.id == team_id, all_teams))
                        
        #                 if team_obj == []:
        #                     raise ValueError

        #                 team_obj = team_obj[0]
                        
        #                 conv_obj.assigned_agent = team_obj.conv_rules.user_assigned_when_noone_is_online
                    
        #         conv_obj=await updateObject(conv_obj) 
        # log_message(20,f"An old conversation object is fetch and updated, customer_id={customer_id}, conversation_id={conv_obj.conversation_uuid}")
    # log_message(20,f"Executed getConversation function successfully, customer_id={customer_id}, conversation_id={conv_obj.conversation_uuid}") 
                  
    return conv_obj 
    # except:
    #     log_message(40,str(sys.exc_info())+f"Some unknown error while accessing getConversation function!") 
    #     return None


#This function will give the bot details which is used in the conversation handler.
async def get_bot_details(bot_id):
    try:
        log_message(10,f"User trying to access gget_bot_details function with bot_id={bot_id}")
        bot_dict={}
        
        bot_query = select(Bot).filter(Bot.id==bot_id)
        bot_obj = await fetchSingle(bot_query)
        
        bot_dict["bot_id"] = bot_obj.id
        bot_dict["bot_name"] = bot_obj.bot_name
        bot_dict["bot_photo"] = str(bot_obj.bot_photo.decode('utf-8')) if bot_obj.bot_photo!=None else None
        bot_dict["allow_human_handoff"] = bot_obj.allow_human_handoff
        bot_dict["integration_platform"] = bot_obj.integration_platform
        bot_dict["integration_platform_details"] = {}
        
        if bot_obj.integration_platform == 'Dialogflow-ES':
            integrated_platform_obj_query = select(DialogFlowES).filter(DialogFlowES.bot_id==bot_id)
            integrated_platform_obj = await fetchSingle(integrated_platform_obj_query)
            
            bot_dict["integration_platform_details"]["platform_id"] = integrated_platform_obj.id
            
        elif bot_obj.integration_platform == 'Dialogflow-CX':
            integrated_platform_obj_query = select(DialogFlowCX).filter(DialogFlowCX.bot_id==bot_id)
            integrated_platform_obj = await fetchSingle(integrated_platform_obj_query)
            
            bot_dict["integration_platform_details"]["platform_id"] = integrated_platform_obj.id
            
        else: #Custom-Platform
            integrated_platform_obj_query = select(CustomBotPlatform).filter(CustomBotPlatform.bot_id==bot_id)
            integrated_platform_obj = await fetchSingle(integrated_platform_obj_query)
            bot_dict["integration_platform_details"]["platform_id"] = integrated_platform_obj.id
            bot_dict["integration_platform_details"]["platform_name"] = integrated_platform_obj.platform_name
        log_message(20,f"User accessedget_bot_details function successfully with bot_id={bot_id}")
        return bot_dict
    except:
        log_message(40,str(sys.exc_info())+f"Some unknown error while accessing get_bot_details function!")




#This message will give the welcome messages for a particular conversation.
#If the conversation handler is human, when ever a customer gets connected or vists oour website and opens the converstaion , immediately he will get a welcome message  which is stored in database.
async def getWcMsgForConv(conversation_id):
    try:
        log_message(10,f"User trying to access getWcMsgForConv function, conversation_id={conversation_id}!")
        conv_query = select(Conversation).options(
            selectinload(Conversation.super_admin).options(
                selectinload(User.welcome_msg_configuration).options(
                    selectinload(WelcomeMessageConfiguration.welcome_messages)
                    )
                ) 
            ).filter(Conversation.conversation_uuid==conversation_id)
        
        conv_obj = await fetchSingle(conv_query)
        
        welcome_msg_config = conv_obj.super_admin.welcome_msg_configuration
        
        #If show welcome message is turned off, then it will return empty list
        if welcome_msg_config.show_welcome_message == False:
            return []
        
        else: #True 
        #Check for welcome message option from js script and try to give welcome message of that language option
            welcome_message_language = "English" #fetch from conv object
            welcome_message_categories = welcome_msg_config.message_categories

            
            if welcome_message_language in welcome_message_categories:
                welcome_messages = [welcome_msg_obj.welcome_message for welcome_msg_obj in list(filter(lambda x:x.message_category==welcome_message_language ,welcome_msg_config.welcome_messages ))]
                return welcome_messages
            
            else: #If language is not present in categories, then check for default language. Else return empty list
                welcome_message_language = "Default"
                if welcome_message_language in welcome_message_categories:
                    welcome_messages = [welcome_msg_obj.welcome_message for welcome_msg_obj in list(filter(lambda x:x.message_category==welcome_message_language ,welcome_msg_config.welcome_messages ))]
                    return welcome_messages
                else:
                    return []
    except:
        log_message(40,str(sys.exc_info())+f"Some unknown error while accessing getWcMsgForConv function! conversation_id={conversation_id}")
        return None
        
    
    
    
    
#This function stores the chat responses made by either 'SERVER', 'HUMAN', 'CUSTOMER' or 'BOT' in the ChatStorage Table
async def storeChats(sender_type,conversation_id,sender_id:Optional[str]=None,chat_response:Optional[str]=None, confidence_level:Optional[str]=None, intent_detected:Optional[str]=None):
    try:
        conv_obj_query = select(Conversation).filter(Conversation.conversation_uuid==conversation_id)
        conv_obj = await fetchSingle(conv_obj_query)
        
        if conv_obj == None:
            log_message(40,f"There is no conversation id present storing chats , conversation_id={conversation_id}!")
            return False
        else:
            if sender_type == 'CUSTOMER':
                chat_obj = ChatStorage(conversation_id = conv_obj.id, response = chat_response, sender_id = sender_id,sender=sender_type)
                chat_obj = await updateObject(chat_obj)
                
            elif sender_type == 'BOT':
                chat_obj = ChatStorage(conversation_id = conv_obj.id, response = chat_response, sender_id = sender_id,confidence_level=confidence_level,intent_detected=intent_detected,sender=sender_type)
                chat_obj = await updateObject(chat_obj)

            elif sender_type == 'HUMAN':
                chat_obj = ChatStorage(conversation_id = conv_obj.id, response = chat_response, sender_id = sender_id,sender=sender_type)
                chat_obj = await updateObject(chat_obj)
                
            elif sender_type == 'SERVER':
                chat_obj = ChatStorage(conversation_id = conv_obj.id, response = chat_response,sender=sender_type)
                chat_obj = await updateObject(chat_obj)
            else:
                log_message(40,f"Sender type is not proper while storing chats : {sender_type}, conversation_id={conversation_id}!")
                return False
            
            log_message(20,f"The chat is stored successfully for {sender_type}!, conversation_id={conversation_id}!")
            return True
    except:
        log_message(40,str(sys.exc_info())+f"Some unknown error occured while storing chats!")
        return False
        
    
#This is used in the customer side websocket. 
#This will give the chats made by customer when ever he visits the website. If the customer is a new customer then an empty list will be sent, if a customer is old customer, then the chats made by him previously will be sent
async def getConvChats(conversation_id):
    log_message(10,f"User trying to access getConvChats function!. The inputs given are: conversation_id={conversation_id}")
    try:
        all_chats_query = select(ChatStorage).filter(ChatStorage.conversation_id==conversation_id)
        all_chats = await fetchMany(all_chats_query)
        
        
        conversation_obj_query = select(Conversation).options(
            selectinload(Conversation.assigned_agent),
            selectinload(Conversation.assigned_bot)
            ).filter(Conversation.id==conversation_id)
        
        conversation_obj = await fetchSingle(conversation_obj_query)
        
        conversation_replier = {}
        conversation_replier["conversation_id"] = conversation_obj.conversation_uuid
        conversation_replier["conversation_handler"] = conversation_obj.conversation_handler
        
        if conversation_obj.conversation_handler == 'HUMAN':
            replier_obj = conversation_obj.assigned_agent
            conversation_replier["replier_info"]={}
            conversation_replier["replier_info"]["human_name"]=replier_obj.first_name + replier_obj.last_name if replier_obj.last_name not in ('',None) else ''
            conversation_replier["replier_info"]["human_photo"]= replier_obj.profile_photo.decode("utf-8")
            
            
        else: #BOT
            replier_obj = conversation_obj.assigned_bot
            conversation_replier["replier_info"]={}
            conversation_replier["replier_info"]["bot_name"]=replier_obj.bot_name if replier_obj.bot_name not in ('',None) else None
            conversation_replier["replier_info"]["bot_photo"]=str(replier_obj.bot_photo.decode('utf-8')) if replier_obj.bot_photo!=None else None
            
           
        
        if list(all_chats) == []:
            return {"message_type":"initial_customer_message","conversation_replier":conversation_replier,"all_chats_list":[]}
        else:
            all_chats_list = []
            for chat_obj in all_chats:
                all_chats_list.append(json.loads(chat_obj.response))
            return {"message_type":"initial_customer_message","conversation_replier":conversation_replier,"all_chats_list" : all_chats_list}
    except:
        log_message(40,str(sys.exc_info())+f"Some unknown error while accessing getConvChats!")
        
    
    
#This will give the away message which should be sent to a customer if there are no agnets to reply for a customer
async def getAwayMessage(conversation_id):
    conv_query = select(Conversation).options(
        selectinload(Conversation.super_admin).options(
            selectinload(User.away_message)
            ),
        selectinload(Conversation.customer)
        ).filter(Conversation.conversation_uuid==conversation_id)
    conv_obj = await fetchSingle(conv_query)
    
    away_message_obj = conv_obj.super_admin.away_message
    
    #If Swow_away_message is true, then show the away message to customers if no agent is online.
    if away_message_obj.show_away_message == True:
        customer_obj = conv_obj.customer
        #Check whether customer is anonymous or known_user
        if customer_obj.customer_email!=None:
            #Known user
            away_msg_dict = {}
            away_msg_dict["user_type"]="known"
            away_msg_dict["message"]=away_message_obj.away_message_for_known
            return away_msg_dict
        else:
            #anonymous user
            away_msg_dict = {}
            away_msg_dict["user_type"]="known"
            away_msg_dict["collect_email"]=away_message_obj.collect_email_id
            away_msg_dict["message"]=away_message_obj.away_message_for_known
            return away_msg_dict
    else:
        #Return None if show_away_message option is turned off
        return None
    
    
#This function will give all the conversation list to the agent. Which are present in that account with messages., Like Resolved, All, Assigned to this particular agent.
async def getAgentConvList(agent_id):
    log_message(10,f"user trying to access getAgentConvList!, agent_id={agent_id}")
    try:
        agent_obj_query = select(User).filter(User.unique_id==agent_id)
        agent_obj = await fetchSingle(agent_obj_query)
        
        super_admin_id = agent_obj.super_admin_id
        
        
        # here we fetch the conversations of last 30 days
        all_account_conversations_query= select(Conversation).options(
            selectinload(Conversation.conversation_tags).options(
                selectinload(ConversationTags.tag)
                ),
            selectinload(Conversation.customer),
            selectinload(Conversation.assigned_agent),
            selectinload(Conversation.all_chats)
            ).filter(
                Conversation.super_admin_id==super_admin_id,
                Conversation.conversation_deleted==False,
                Conversation.created_time>=settings.conversation_time                        
                )
        all_account_conversations = await fetchMany(all_account_conversations_query)
        
        # ---------------------- ASSIGNED CONVERSATIONS -------------------------
        assigned_conversations = list(filter(
            lambda x:x.conversation_handler=='HUMAN' 
            and x.assigned_agent==agent_obj 
            and x.end_user_conversation_status in ['Open'],
            all_account_conversations))
        
        #----------------------------   ALL CONVERSATIONS ------------------------
        all_conversations = list(filter(
            lambda x:x.end_user_conversation_status in ['Open','First-response-pending'],
            all_account_conversations))
        
        #--------------------------- RESOLVED CONVERSATIONS --------------------------
        resolved_conversations = list(filter(
            lambda x:x.end_user_conversation_status in ['Resolved','Spam'],
            all_account_conversations))
        
        conversations = [assigned_conversations,all_conversations,resolved_conversations]
        result_dict = {"success":True}

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
                conversation_dict["conversation_opened"] = conversation.conversation_opened
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
                if conversation_dict["messages"] != []:
                    conversation_dict["last_message_time"] = conversation_dict["messages"][-1]["created_time"]
                else:
                    conversation_dict["last_message_time"] = None
                    
                result_dict[conv_part].append(conversation_dict)
        log_message(10,f"getAgentConvList executed successfully successfully!, agent_id={agent_id}")        
        return result_dict
    except:
        log_message(40,str(sys.exc_info())+f"Some error occured while accessing getAgentConvList! ")
        return {"success":False}


#Change conversation is opened or not status
async def changeConvOpened(conversation_id:str,status:Boolean):
    try:
        conv_obj_query = select(Conversation).filter(Conversation.conversation_uuid==conversation_id)
        conv_obj = await fetchSingle(conv_obj_query)
        
        conv_obj.conversation_opened = status
        await updateObject(conv_obj)
        
        log_message(10,f"changeConvOpened executed successfully successfully!, conversation_id={conversation_id}, status={status}")
        return True
    except:
        log_message(40,str(sys.exc_info())+f"Some error occured while executing changeConvOpened! conversation_id={conversation_id}, status={status} ")
        return False
        
        

#Generate random names for the  customers
async def generateCustomerName():
    log_message(10,f"User trying to access generateCustomerName function!")
    name_list = ["Boreogadus saida","Atheresthes stomias","Pleurogrammus monopterygius", "Sebastes melanops", "Sebastes mystinus", "Mallotus villosus", "Oncorhynchus keta", "Oncorhynchus kisutch", "Ophiodon elongates", "Clupea pallasi", "Sebastes alutus", "Trichodon trichodon","Lamna ditropis","Oncorhynchus nerka","Lithodes couesi","Spectacled eider","Orcinus orca","Eubalaena glacialis","Phoco vitulina","Enhydra lutris","Formicidae","Loxodonta","Diomedeidae","Vicugna pacos","Elephas maximus","Chiroptera","Boiga irregularis","Bos gaurus","Ursus maritimus", "Antilope cervicapra","Rattus rattus","Bubalus bubalis","Rhopalocera","Felis catus","Acinonyx jubatus","Gazella bennettii","Blattodea","Acridotheres tristis","Bos taurus","Crocodylus palustris","Cetacea","Accipitridae","Elephantidae","Vulpes vulpes","Giraffa camelopardalis","Equus caballus","Mus musculus","Psittaciformes","Python molurus","Panthera leo"]
    random_name = random.choice(name_list)
    return random_name
    
    
#Currently available agent list with socket online status
async def convAssigneeList(conv_conn_manager,agent_id):
    try:
        log_message(10,f"User trying to execute convAssigneeList! agent_id={agent_id}")
        agent_obj_query = select(User).where(User.unique_id==agent_id,User.email_verified==True)
        agent_obj = await fetchSingle(agent_obj_query)
        
        convAssigneeList = {}
        
        available_agents_query = select(User).filter(User.super_admin_id==agent_obj.super_admin_id,User.email_verified==True,or_(User.email_invitation_status==2,User.email_invitation_status==0))
        available_agents = await fetchMany(available_agents_query)
        
        socket_active_agents = list(conv_conn_manager.active_agent_connections.keys())
        
        available_agents = [ {
            "id":agent.id,
            "first_name":agent.first_name,
            "last_name":agent.last_name,
            "availability_status":agent.is_available_status,
            "agent_connected":True if agent.unique_id in socket_active_agents else False} for agent in available_agents]
        log_message(10,f"User trying to accessing the : available_agents================={available_agents}")
        convAssigneeList["available_agents"]=available_agents
        
        superadmin_obj_query = select(User).options(
            selectinload(User.default_team).options(
                selectinload(DefaultTeam.bots),
                selectinload(DefaultTeam.teams)
            )
        ).filter(User.id==agent_obj.super_admin_id,User.email_verified==True)
        superadmin_obj = await fetchSingle(superadmin_obj_query)
        
        available_bots = list(filter(lambda x:x.is_active==True ,superadmin_obj.default_team.bots))
        available_bots = [{
            "id":bot.id,
            "bot_name":bot.bot_name if bot.bot_name!=None else None
        } for bot in available_bots]
        convAssigneeList["available_bots"]=available_bots
        
        
        available_teams = [{"id":superadmin_obj.default_team.id,"is_default":True, "name":"DefaultTeam"}]
        for team_obj in superadmin_obj.default_team.teams:
            team_dict={"id":team_obj.id,"is_default":False, "name":team_obj.team_name}
            available_teams.append(team_dict)
        convAssigneeList["available_teams"]=available_teams
        log_message(20,f"convAssigneeList executed successfully! agent_id={agent_id}")
        return {"success":True,"assignee_list":convAssigneeList}
    except:
        log_message(40,str(sys.exc_info())+f"Some error occured while executing convAssigneeList! agent_id={agent_id}")
        return {"success":False,"errormsg":"Could not fetch the requested resource"}
    
    
    
    

#This function helps in changing the conversation status of the conversation through websocket
async def changeConversationSatus(conversation_id,conversation_status):
    try:
        conversation_query = select(Conversation).filter(
            Conversation.conversation_uuid==conversation_id
            )
        conversation_obj = await fetchSingle(conversation_query)
    except:
        log_message(40,str(sys.exc_info())+f"Couldn't fetch conversation_query while executing changeConversationSatus function! conversation_id:{conversation_id}")
        return {"success":False,"errormsg":"Cannot update conversation status!"}
    
    
    if conversation_obj == None:
        log_message(30,f"Conversation object cannot be None while executing changeConversationSatus function! conversation_id:{conversation_id}")
        return {"success":False,"errormsg":"Cannot update conversation status!"} #No conversation obj
    
    try:
        conversation_obj.end_user_conversation_status = conversation_status
        await updateObject(conversation_obj)
    except:
        log_message(40,str(sys.exc_info()) + f"Cannot update conversation_obj to session while executing changeConversationSatus function! conversation_id:{conversation_id}, conversation_status:{conversation_status}")
        return {"success":False,"errormsg":"Cannot update conversation status!"} 
        
    log_message(20,f"changeConversationSatus function executed successfully conversation_id:{conversation_id}, conversation_status:{conversation_status}")
    return {"success":True,"message":"Conversation status changed to {}!".format(conversation_status)}



#This fuunctions gives the user to be assigned to a conversation when no one is online
async def getNoOneOnlineAssignee(conversation_id):
    try:
        conversation_query = select(Conversation).options(
            selectinload(Conversation.super_admin).options(
                selectinload(User.account_option),
                selectinload(User.default_team).options(
                    selectinload(DefaultTeam.user_assigned_when_noone_is_online)
                    ),
                selectinload(User.teams).options(
                    selectinload(Team.conv_rules).options(
                        selectinload(ConversationRules.user_assigned_when_noone_is_online)
                        )
                )
            )
            ).filter(
            Conversation.conversation_uuid==conversation_id
            )
        conversation_obj = await fetchSingle(conversation_query)
    except:
        log_message(40,str(sys.exc_info())+f"Couldn't fetch conversation_query while executing getNoOneOnlineAssignee function! conversation_id:{conversation_id}")
        return {"success":False,"errormsg":"Cannot execute  getNoOneOnlineAssignee function!"}
    
    if conversation_obj.super_admin.account_option.first_conversation_assignment_option == 'DefaultTeam':
        default_team = conversation_obj.super_admin.default_team
        user_to_be_assigend_id = default_team.user_assigned_when_noone_is_online_id
        agent_name = default_team.user_assigned_when_noone_is_online.first_name + default_team.user_assigned_when_noone_is_online.last_name if default_team.user_assigned_when_noone_is_online.last_name not in ('',None) else ''
        agent_photo = default_team.user_assigned_when_noone_is_online.profile_photo.decode("utf-8")
        agent_unique_id = default_team.user_assigned_when_noone_is_online.unique_id
        
    else: #Team
        teams= conversation_obj.msuper_admin.teams
        
        team_obj = list(filter(lambda x:x.id == conversation_obj.super_admin.account_option.first_conversation_assignment_id, teams))
        
        if team_obj == []:
            log_message(40,f"There is no team object for the given id while executing getNoOneOnlineAssignee function! conversation_id:{conversation_id}")
            return {"success":False,"errormsg":"Cannot execute  getNoOneOnlineAssignee function!"}
        
        team_obj= team_obj[0]
        
        user_to_be_assigend_id = team_obj.conv_rules.user_assigned_when_noone_is_online_id
        agent_name = team_obj.conv_rules.user_assigned_when_noone_is_online.first_name + team_obj.conv_rules.user_assigned_when_noone_is_online.last_name if team_obj.conv_rules.user_assigned_when_noone_is_online.last_name not in ('',None) else ''
        agent_photo = team_obj.conv_rules.user_assigned_when_noone_is_online.profile_photo.decode("utf-8")
        agent_unique_id = team_obj.conv_rules.user_assigned_when_noone_is_online.unique_id
        
    return {"success":True,"agent_id":user_to_be_assigend_id,"agent_unique_id":agent_unique_id ,"agent_name":agent_name,"agent_photo":agent_photo}


#This function gives the list of agents ids under a super_admin account so that we can send the messages to all the agents online at a time
async def getAllAgents(super_admin_id):
    all_agents_query = select(User).filter(User.super_admin_id==super_admin_id, User.email_verified==True)
    all_agents = await fetchMany(all_agents_query)
    all_agents_ids = [agent.unique_id for agent in all_agents]
    return all_agents_ids



#Suppose id the customer disconnects from the websockets, then the auto resolve function will be triggered and  the conversation status will be set to 'Resolved'. (This options considers that the customers left without replying to agent. Then their conversations should be resolved.) Suppose if the customers revisits the website and messages agaain. Then the conversation will be in the opened state.
async def autoResolveConversations(conversation_id:int):
    conversation_query = select(Conversation).options(
        selectinload(Conversation.super_admin).options(
            selectinload(User.account_option)
        )    
    ).filter(Conversation.id==conversation_id)
    conv_obj = await fetchSingle(conversation_query)
    if conv_obj.super_admin.account_option.auto_resolve_conversations == True:
        conv_obj.end_user_conversation_status = 'Resolved'
        await updateObject(conv_obj)
        message  = json.dumps({
                                'type': 'chat_message',  
                                'message': {"fe_type": "auto_resolve_message",
                                            "content": {'text': conv_obj.super_admin.account_option.auto_resolve_message}
                                            }
                            })
        await storeChats(sender_type='SERVER',conversation_id=conv_obj.conversation_uuid, chat_response=message)
        return {"success":True,"message":f"Conversation-{conversation_id} resolved automatically!"}
    else:
        return {"success":True, "message": "Agent donot want to auto resolve the conversation!"}
    
    
#This function is used to add all the email templates to the database from the email templaate filler file.
#This is only for development purpose
async def addEmailTemplates():
    for key in email_templates.keys():
        email_obj = EmailTemplates(template_name = key, 
                                   message_subject = email_templates[key]["subject"],
                                   message_template = email_templates[key]["message"]
        )
        await updateObject(email_obj)
        

class ConversationManager:
    
    def __init__(self):
        self.visitorsWS = {}
        self.agentsWS = {}
        self.initiateAt= time.ctime()
        print(f"Initiated at {self.initiateAt} : {self}")

    def getAll(self):
        AllWS = {'VisitorWS': self.visitorsWS, 'AgentWS': self.agentsWS}
        print(f"Current WS List: {AllWS}") 
        return AllWS

    def getVisitor(self, mid):
        vws = self.visitorsWS.get(mid, None)
        return vws

    def addVisitor(self, mid, ws):
        try:
            print(f"Initiated at {time.ctime()} : {self}")
            vws = self.visitorsWS.get(mid, None)
            if vws:
                vws.append(ws)
                self.visitorsWS[mid] = vws
                print(f"Appending {mid} at {time.ctime()}: [{vws}]")
                self.getAll()
            else:
                self.visitorsWS.update({mid: [ws]})
                print(f"Adding {mid} at {time.ctime()}: [{ws}]")
                self.getAll()
        except Exception as e:
            print(f"Some Error: {e}") # Handle properly
            print(traceback.format_exc())

    def removeVisitor(self, mid, ws):
        try:
            print(f"Initiated at {time.ctime()} : {self}")
            vws = self.visitorsWS.get(mid, None)
            if vws:
                if ws in vws:
                    vws.remove(ws)
                    self.visitorsWS[mid] = vws
                    print(f"Removing [{ws}] for {mid} at {time.ctime()}: So finally {vws}")
                    self.getAll()
                    # if len(vws) == 0:
                    #     self.visitorsWS.pop(mid)
                    # else:
                    #     self.visitorsWS[mid] = vws
            else:
                print("Vistor WS List already empty. Nothing to remove") # Handle properly
        except Exception as e:
            print(f"Some Error: {e}") # Handle properly
            print(traceback.format_exc())
    
    def getAgent(self, mid):
        aws = self.agentsWS.get(mid, None)
        log_message(10,f" awss ={aws}")
        print(f"Getting Agent WS for {mid}")
        self.getAll()
        return aws

    def addAgent(self, mid, ws):
        try:
            aws = self.agentsWS.get(mid, None)
            if aws:
                aws.append(ws)
                self.agentsWS[mid] = aws
                print(f"Appending {mid} at {time.ctime()}: {aws}")
                self.getAll()
            else:
                self.agentsWS.update({mid: [ws]})
                print(f"Adding {mid} at {time.ctime()}: [{ws}]")
                self.getAll()
        except Exception as e:
            print(f"Some Error: {e}") # Handle properly
            print(traceback.format_exc())
    
    def removeAgent(self, mid, ws):
        try:
            aws = self.agentsWS.get(mid, None)
            if aws:
                if ws in aws:
                    aws.remove(ws)
                    self.agentsWS[mid] = aws
                    print(f"Removing WebSocket for {mid} at {time.ctime()}: {aws}")
                    self.getAll()
                    # if len(aws) == 0:
                    #     self.agentsWS.pop(mid)
                    # else:
                        # self.agentsWS[mid] = aws
            else:
                print("Agent WS List already empty. Nothing to remove") # Handle properly
        except Exception as e:
            print(f"Some Error: {e}") # Handle properly
            print(traceback.format_exc())

GlobalConversationManager = ConversationManager()
