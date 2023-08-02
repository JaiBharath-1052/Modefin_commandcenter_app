import os
import jwt
import time
import json
import traceback
from typing import Optional
from fastapi.websockets import WebSocket
from fastapi.responses import HTMLResponse
from fastapi import Cookie, Depends, Query, status
from starlette.endpoints import WebSocketEndpoint, HTTPEndpoint

# Custom Modules
from .redis.additionalfunc import agentactivities
from .rasa_func import rasa_response  # Remove the relative "."
from utils.helpers import GlobalConversationManager

from app_log.logModule import log_message


# TODO: 
# Possible type :- botMessage, agentMessage, visitorMessage, (Not subType)
                #  serverActivity, agentActivity, visitorActivity (Not subType)


def servertime():
    return int(time.time())

async def get_cookie_or_token(
        websocket: WebSocket,
        session: Optional[str] = Cookie(None),
        token: Optional[str] = Query(None),):
    if session is None and token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return session or token


def cleanEmail(email):
    replace_char = ['@','.','+','']
    for char in replace_char:
        if char in email:
            email = email.replace(char, "")
    return email

agentactivities_redis = agentactivities()
# GlobalConversationManager = ConversationManager()

class wsuser(WebSocketEndpoint):
    encoding = 'text'

    # Configuration variables
    bot_name = "Rasa"
    botnassigned = True
    bot_entry = None

    async def group_send(self, websockets, message):
        if isinstance(websockets, list):
            for ws in websockets:
                await ws.send_text(json.dumps(message))
        else:
            await websockets.send_text(json.dumps(message))
    async def on_connect(self, websocket):
        self.cookieVisitorID = websocket.cookies.get('visitorID', None) # in case of user connection
        # TODO: Better queue management
        # log_message(f"response of visitor in additionalfuncccccc={self.cookieVisitorID}")
        temp = agentactivities_redis.visitorTalkto(self.cookieVisitorID) # TODO: 
        # log_message(f"response of visitor in additionalfuncccccc={self.cookieVisitorID}")
        self.talkto = temp['talkto']
        # TODO: Get this from DB
        if self.talkto == 'agent':
            self.agentID = agentactivities_redis.getLastAgent(self.cookieVisitorID)
            self.agentName = 'Bhavana'
        self.sendWelcomeMessage = temp['welcomeMessage']
        del temp
        GlobalConversationManager.addVisitor(self.cookieVisitorID, websocket)
        GlobalConversationManager.getAll()
        await websocket.accept()

    async def on_disconnect(self, websocket, close_code):
        # await self.remove_ws(self.cookieVisitorID, websocket)
        GlobalConversationManager.removeVisitor(self.cookieVisitorID, websocket)

    async def on_receive(self, websocket, text_data):
        text_data_json = json.loads(text_data)
        print(f"text_data_json: {text_data_json}")        
        msgType = text_data_json.get('type', None)
        log_message(10,f" text_data_json ={text_data_json}")        
        agentactivities_redis.updateVisitorLasttime(self.cookieVisitorID)

        
        if msgType == "visitorActivity":
            subType = text_data_json.get('subType', None)
            # Register bot 
            if subType == 'Connection':
                data = text_data_json.get('data', None)
                #Extract from and del data
                self.BotID = data.get('BotID', None)
                self.AppID = data.get('AppID', None)
                # print(self.talkto)
                # Register reply
                if self.talkto == "bot": # TODO - better to extract from DB
                    reply = {
                                'type':'serverActivity',
                                'subType':'botRegistered',
                                'data':{
                                        # 'botName' : 'Diva',
                                        # 'botPhoto' :'data:image/png;base64,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',
                                        'messageTime': servertime(),
                                        'status': 'success'
                                        },
                                }
                    await self.group_send(websocket, reply)
                    
                    if self.sendWelcomeMessage:
                        metadata = {"contentType": "300", "payload": [{"title": "Account Balance", "message": "How can I find out my Account Balance?"}, {"message": "How can I check Mini Statement relating to my account?", "title": "Mini Statement"}, {"message": "How can I check Full Statement relating to my account?", "title": "Full Statement"}, {"message": "How can I apply for Cheque Book?", "title": "Cheque Book"}, {"message": "How can I do a mobile Recharge?", "title": "Mobile Recharge"}, {"title": "Funds Transfer", "message": "What kind of Funds Transfer can I do in mobile banking service?"}, {"message": "What is the detailed process of using Cardless Withdrawal service using ATM", "title": "Cardless Withdrawal"}, {"message": "How do I contact Bank Customer Care?", "title": "Customer Care"}, {"title": "COVID-19", "message": "How do I support for covid-19 fund?"}], "templateId": "6"}
                        self.welcome_message = {
                                'type':'botMessage',
                                'data':{
                                        'message': 'Hi! My name is DIVA and I am a Chatbot.\n I can help you with Miracle Bank related queries',
                                        'messageTime': servertime(),
                                        'metadata': metadata,
                                        },
                                }
                        await self.group_send(websocket, self.welcome_message)

                # From second unhandled message from the user
                elif self.talkto == 'agent':
                    # TODO: Add this josn type in google sheet
                    fe_server_response = {
                                    'type': 'serverActivity',
                                    'subType' : 'agentAssigned',
                                    'data' : {
                                                'agentId': self.agentID,
                                                'agentName': self.agentName,
                                                'message' : f'You are connected to agent {self.agentName}',
                                                'messageTime': servertime(), # Using message time when visitor sent it #servertime(),
                                            }
                                    }
                    await self.group_send(websocket, fe_server_response)
            
            elif subType == 'Others': # Other activity
                pass

        elif msgType == "visitorMessage":
            text = text_data_json.get('data').get('message', None)
            messageTime = text_data_json.get('data').get('messageTime', None)
            ws_list_visitor = GlobalConversationManager.getVisitor(self.cookieVisitorID)
            if self.talkto == "bot":

                # Remove from production
                if text in ["custom_button","custom_button2","custom_link","custom_Sbutton", "custom_form"]:
                    # print("Directory: ", os.getcwd())
                    action = "Custom_Response"
                    # returnJson = {"":""}
                    mycontent = open("ws/richMessages.json", "r").read()
                    myjson = json.loads(mycontent)
                    returnJson = myjson[text]
                    returnJson['data']['messageTime'] = servertime()
                    # print("ReturnJSON: ", returnJson)
                    await self.group_send(ws_list_visitor, returnJson)
                # Till here ---- change below condition to if

                elif self.bot_name == 'Rasa':
                    try:
                        self.response = await rasa_response(text, self.cookieVisitorID)
                        self.response = json.loads(self.response)
                        cond_level = type(self.response)  # [0]
                        action = self.response['queryResult'].get('action', None)
                        log_message(10,f" responseeeeeeee of action ={action}")
                    except:
                        fe_visitor_response = {
                                           'type' : 'serverActivity',
                                           'subType' : 'agentAssigned',
                                           'data' : {
                                                    'agentId': self.agentID,
                                                    'agentName' : self.availableAgent['agentDetails']['name'],
                                                    'agentPhoto' : self.availableAgent['agentDetails']['photo'],
                                                    'messageTime': servertime(), 
                                                    'isOnline' : True,
                                                    'message' : f'You are connected to agent {self.availableAgent["agentDetails"]["name"]}'
                                                    }
                                            }
                        print("Couldn't connect to the bot due to network/other issue.")
                        await self.group_send(ws_list_visitor, fe_visitor_response)
                else:  # Use if else when multiple NLP engines
                    action = None

                # First unhandled message from the user
                if (action in ["input.unknown", "nlu_fallback", "out_of_scope"]) or (action is None):
                    log_message(10,f" responseeeeeeee of 195 line ={action}")
                    # Send the client a notification that we are asking for an agent
                    # Set variables to for upcming messages
                    self.talkto = "agent"  # This variable will make sure all messages after first unknow messages are sent to agent
                    # Server to visitor
                    fe_visitor_response = {
                                           'type' : 'botMessage',
                                                'data': {
                                                    'message': "Could not understand your query, transferring the chat to agent",
                                                    'messageTime': servertime()
                                                }
                                            }
                    await self.group_send(ws_list_visitor, fe_visitor_response)
                    log_message(10,f" ws list visitor ={ws_list_visitor}")

                    self.availableAgent = agentactivities_redis.get_agent()
                    log_message(10,f" self availableAgent ttttttt ={self.availableAgent}")

                    if self.availableAgent['agentAvailable']:
                        self.agentID = self.availableAgent['agentDetails']['id']
                        #self.availableAgent['agentDetails']['id']
                        log_message(10,f" agentID from views.py ={self.agentID}")
                        # TODO: 
                        agentactivities_redis.updateVisitorAgent(self.cookieVisitorID, self.agentID)
                        agent_ws_list = GlobalConversationManager.getAgent(self.agentID)
                        log_message(10,f" agent_ws_listttt ={agent_ws_list}")
                        
                        fe_visitor_response = {
                                           'type' : 'serverActivity',
                                           'subType' : 'agentAssigned',
                                           'data' : {
                                                    'agentId': self.agentID,
                                                    'agentName' : self.availableAgent['agentDetails']['name'],
                                                    'agentPhoto' : self.availableAgent['agentDetails']['photo'],
                                                    'messageTime': servertime(), 
                                                    'isOnline' : True,
                                                    'message' : f'You are connected to agent {self.availableAgent["agentDetails"]["name"]}'
                                                    }
                                            }
                        fe_agent_activity = {
                                           'type' : 'serverActivity',
                                           'subType' : 'visitorAssigned',
                                           'data' : {
                                                    'visitorId': self.cookieVisitorID,
                                                    'visitorPhoto' : 'data:image/jpeg;base64,/9j/4AAQSkZJRgABA',
                                                    'messageTime': messageTime, # Using message time when visitor sent it #servertime(),
                                                    'isOnline' : True,
                                                    'message' : text
                                                    }
                                            }

                        # Send client details to agent dashboard
                        #if agent_ws_list:
                            #await self.group_send(ws_list_visitor, fe_visitor_response)
                            #await self.group_send(agent_ws_list, fe_agent_activity)
                        if self.availableAgent:
                            await self.group_send(ws_list_visitor, fe_visitor_response)				
                            await self.group_send(self.availableAgent, fe_agent_activity)
                        else:
                            fe_visitor_response = {
                                               'type' : 'serverActivity',
                                               'subType' : 'agentAssigned',
                                               'data' : {
                                                        'isOnline' : False,
                                                        'messageTime': servertime() ,
                                                        'message' : 'There are no online agents currently.'
                                                        }
                                                }                            
                            await self.group_send(ws_list_visitor, fe_visitor_response)
                    else: # When agent not available
                        # TODO: This message should come from DB
                        fe_visitor_response = {
                                           'type' : 'serverActivity',
                                           'subType' : 'agentAssigned',
                                           'data' : {
                                                    'isOnline' : False,
                                                    'messageTime': servertime() ,
                                                    'message' : 'Sorry, There are no online agents currently ()'
                                                    }
                                            }
                        # Send only to user (No agent available)
                        await self.group_send(ws_list_visitor, fe_visitor_response)

                # Remove from production
                elif action=='Custom_Response':
                    print("Do Nothing")

                # Cant reply to channel_name
                else:
                    log_message(10,f" response in views.py ={self.response}")
                    # Action will be None then Send the response (if not handled by the bot properly)
                    fe_visitor_response = {
                                        'type': 'botMessage',
                                        'data': {
                                            'message': self.response['queryResult']['fulfillmentMessages'][0]['payload']['message'],
                                            
                                            'messageTime': servertime(),
                                            'metadata': self.response['queryResult']['fulfillmentMessages'][0]['payload']['metadata'],
                                            }
                                        }
                    await self.group_send(ws_list_visitor, fe_visitor_response)

            # From second unhandled message from the user
            # This section is in multiple changes( Check the other section too )
            elif self.talkto == 'agent':
                agent_ws_list = GlobalConversationManager.getAgent(self.agentID)
                fe_agent_response = {
                                'type': 'visitorMessage',
                                'data' : {
                                            'visitorId': self.cookieVisitorID,
                                            'messageTime': messageTime, # Using message time when visitor sent it #servertime(),
                                            'message' : text
                                        }
                                }
                if agent_ws_list:
                    await self.group_send(agent_ws_list, fe_agent_response)
                else:
                    fe_visitor_response = {
                                       'type' : 'serverActivity',
                                       'subType' : 'agentAssigned',
                                       'data' : {
                                                'isOnline' : False,
                                                'messageTime': servertime() ,
                                                'message' : 'Sorry, There are no online agents currently'
                                                }
                                        }
                    await self.group_send(ws_list_visitor, fe_visitor_response)
        
        else:  # When msgType is not sent
            # TODO: Log the instance with visitorID & payload 
            await websocket.send_text(json.dumps({
                "errorcode": 100, "errormsg": "Message type not defined"}))
            await websocket.close()


class wsagent(WebSocketEndpoint):
    encoding = 'text'
    # JWT Key
    jwtsalt = os.getenv("JWTSALT")
    jwtalgo = os.getenv("JWTALGO")

    async def group_send(self, websockets, message):
        if isinstance(websockets, list):
            for ws in websockets:
                await ws.send_text(json.dumps(message))
        else:
            await websockets.send_text(json.dumps(message))

    async def validate_jwt(self, websocket):
        try:
            self.agentID = cleanEmail(jwt.decode(self.jwt, key=self. jwtsalt,algorithms=[self.jwtalgo])['sub'])
            # print(f"AgentID: {self.agentID}")
        except Exception as e :
            # self.agentID = cleanEmail("bhavana4339@gmail.com")
            print(f"Some Error (Environment valiarble no set, jwt expired): {e}") # Handle later
        

    # TODO: Handle in redis for better queue manager
    # connected_visitor = []
    async def on_connect(self, websocket):
        self.jwt = websocket.cookies.get('X-Authorization', None)
        if self.jwt:
            await self.validate_jwt(websocket)
        else: # Remove this in production
            self.agentID = None
            print("Hardcoding the agentID")
        
        if self.agentID is not None:
            GlobalConversationManager.addAgent(self.agentID, websocket)
            GlobalConversationManager.getAll()
            await websocket.accept()
        else: 
            print("No AgentID found")
        

    async def on_disconnect(self, websocket, close_code):
        print(f"TRYING TO DISCONNECT {self.agentID} {websocket}")
        GlobalConversationManager.removeAgent(self.agentID, websocket)

    # Receive message from WebSocket
    async def on_receive(self, websocket, text_data):
        text_data_json = json.loads(text_data)
        msgType = text_data_json.get('type', None)
        ws_list_agent = GlobalConversationManager.getAgent(self.agentID)
        

        if msgType == 'agentMessage':
            visitorID = text_data_json.get('data').get('visitorID', None)
            message = text_data_json.get('data').get('message', None)
            if visitorID:
                visitorWS = GlobalConversationManager.getVisitor(visitorID)
                if (visitorWS is None) or (len(visitorWS) == 0):
                    fe_agent_response = {
                                    'type': 'visitorActivity',
                                    'data' : {
                                        'visitorId': visitorID,
                                        'message': 'Visitor is offline',
                                        'messageTime': servertime()
                                        }
                                    }
                    # Send only to user (No agent available)
                    await self.group_send(ws_list_agent, fe_agent_response)
                else:
                    fe_user_response = {
                                    'type': 'agentMessage',
                                    'data' : {
                                        'message': message,
                                        'messageTime': servertime()
                                        }
                                    }
                    await self.group_send(visitorWS, fe_user_response)
            else:
                print("Agent msg format is wrong: No visitor ID found")

