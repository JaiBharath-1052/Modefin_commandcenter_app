import json
import functools
import traceback
from sys import intern # To remove disconnecting websocket - Build a better way
from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket
from .layers import get_channel_layer

# TODO: self group excluding self (If visitor sends a msg the, then other connect ws should get that message too)
# TODO: 

class InvalidChannelLayerError(ValueError):
    """
    Raised when a channel layer is configured incorrectly.
    """
    pass


def get_handler_name(message):
    """
    Looks at a message, checks it has a sensible type, and returns the
    handler name for that type.
    """
    # Check message looks OK
    if "type" not in message:
        raise ValueError("Incoming message has no 'type' attribute")
    if message["type"].startswith("_"):
        raise ValueError("Malformed type in message (leading underscore)")
    # Extract type and replace . with _
    return message["type"].replace(".", "_")

class MyWebSocketEndpoint2(WebSocketEndpoint): # Before implementing conversation 
    # wsuuid = uuid.uuid4()
    encoding = 'bytes'
    channel_layer_alias = 'default'
    # groups = []
    ws_connection = {'visitors':{},
                    'agents':{}}

    async def get_layer(self, channel_name = None):
        self.channel_layer = get_channel_layer(self.channel_layer_alias)
        if self.channel_layer is not None:
            if channel_name is not None: 
                self.channel_receive = functools.partial(self.channel_layer.receive, self.channel_name)
            else:
                self.channel_name = await self.channel_layer.new_channel()
                self.channel_receive = functools.partial(self.channel_layer.receive, self.channel_name)


    async def on_connect(self, websocket: WebSocket) -> None:
        # Initialize layer
        prev_msg = None

        # If the channel_name is saved in cookies then connect to the chat
        self.channel_name = websocket.cookies.get('visitorID', None) # in case of user connection
        self.cookieVisitorID = websocket.cookies.get('visitorID', None) # in case of user connection
        self.jwt = websocket.cookies.get('X-Authorization', None) # in case of agent connection
        # print(f"########COOKIES############### \n {websocket.cookies}")
        # if self.visitorID is None:
        #     self.visitorID = self.channel_name = "Kunal"

    async def on_receive(self, websocket, data):
        pass

    async def on_disconnect(self, websocket, close_code):
        try:
            pass
        except AttributeError:
            raise ValueError("Some error while disconnecting")

    async def add_ws(self, uniqueid, websocket, addtype='visitor'):
        # Add websocket connection 
        if addtype == 'visitor': 
            try:
                visitor = self.ws_connection['visitors'].get(self.cookieVisitorID, None)
                if visitor:
                    visitor.append(websocket)
                    self.ws_connection['visitors'][self.cookieVisitorID] = visitor
                else:
                    self.ws_connection['visitors'].update({self.cookieVisitorID: [websocket]})
            except Exception as e:
                print(f"Some Error: {e}") # Handle properly
                print(traceback.format_exc())

        if addtype == 'agent':
            try:
                agent = self.ws_connection['agents'].get(self.agentID, None)
                print(f"AGENT in ADD_WS: {agent}")
                if agent:
                    agent.append(websocket)
                    self.ws_connection['agents'][self.agentID] = agent
                else:
                    self.ws_connection['agents'].update({self.agentID: [websocket]})
            except Exception as e:
                print(f"Some Error: {e}") # Handle properly
                print(traceback.format_exc())
    
    async def remove_ws(self, uniqueid, websocket, addtype = 'visitor'):
        # Remove the ws from ws_connection not the 
        if addtype == 'visitor':
            try:
                visitor = self.ws_connection['visitors'].get(self.cookieVisitorID, None)
                if visitor:
                    if websocket in visitor:
                        visitor.remove(websocket)
                        if len(visitor) == 0:
                            self.ws_connection['visitors'].pop(self.cookieVisitorID)
                    self.ws_connection['visitors'][self.cookieVisitorID] = visitor
            except Exception as e:
                print(f"Some Error: {e}") # Handle properly
                print(traceback.format_exc())

        if addtype == 'agent':
            try:
                agent = self.ws_connection['agents'].get(self.agentID, None)
                if agent:
                    if websocket in agent:
                        agent.remove(websocket)
                        if len(agent) == 0:
                            self.ws_connection['agents'].pop(self.agentID)
                        else: 
                            self.ws_connection['agents'][self.agentID] = agent
            except Exception as e:
                print(f"Some Error: {e}") # Handle properly
                print(traceback.format_exc())

    async def group_send(self, websockets, message):
        # TODO: Retry if websocket isn't present
        print(f"MESSAGE: {message}")
        # print("SEND FROM GROUP SEND")
        if isinstance(websockets, list):
            for ws in websockets:
                await ws.send_text(json.dumps(message))
        else:
            await websockets.send_text(json.dumps(message))


# import urllib.parse as urlparse
# from django.http import JsonResponse
# from asgiref.sync import async_to_sync
# from channels.db import database_sync_to_async
# from channels.generic.websocket import WebsocketConsumer, AsyncJsonWebsocketConsumer

# # Focused
# from .dialogflow_func import df_response, get_bot_settings, get_free_agent, get_df_ses_id, save_channel_name, get_rand_name  # Remove the relative "."
# from madmin.models import GCred


# @database_sync_to_async
# def get_bt_obj(bot_id):
#     bt_obj = GCred.objects.get(bot_id=bot_id)
#     return bt_obj


# class ChatAsyncConsumer(AsyncJsonWebsocketConsumer):
#     async def connect(self):
#         # self.room_name = self.scope['url_route']['kwargs']['room_name']
#         # self.room_group_name = 'chat_%s' % self.room_name

#         # Client randon name
#         self.client_name = await get_rand_name()
#         self.room_group_name = 'chat_%s' % self.client_name

#         # Configuration variables
#         self.talkto = "bot"
#         self.botnassigned = True
#         self.bot_entry = None

#         # Extract query Params {bot_id}
#         # self.params = urlparse.parse_qs(self.scope['query_string'].decode("utf-8"))
#         # self.bot_id = self.params.get("bot_id", None)
#         # self.bot_id = self.bot_id[0]

#         # Join room group
#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name
#         )

#         # Accept the connection
#         await self.accept()

#         # Sending the bot setting on connect
#         # self.bot_settings = await get_bot_settings(self.bot_id)
#         # await self.send(text_data=self.bot_settings)

#     async def disconnect(self, close_code):
#         # Leave room group
#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )

#     # Receive message from WebSocket
#     async def receive(self, text_data):
#         print("User Scope: ", self.scope)
#         # print(dir(self))
#         # print(self.channel_name)
#         # print(self.room_group_name)
#         text_data_json = json.loads(text_data)
#         msg_type = text_data_json.get('type', None)

#         if msg_type == "register_bot":
#             print("botnassigned: ", self.botnassigned)
#             if self.botnassigned:
#                 # Get bot details
#                 self.bot_id = text_data_json.get('bot_id', None)

#                 if self.bot_id is not None:
#                     self.bot_name = 'Dialogflow'
#                     self.response = {'message': 'Dafault'}

#                     print("Here: ", self.bot_entry)

#                     # Set Dialogflow variables
#                     if self.bot_name == 'Dialogflow':
#                         if self.bot_entry is None:
#                             print("Setting Gcred")
#                             self.bot_entry = await get_bt_obj(self.bot_id)
#                             print(self.bot_entry)
#                         print("bot_name: ", self.bot_entry)
#                         # Session ID for dialogflow integration
#                         self.df_ses_id = await get_df_ses_id(self.bot_id)
#                         # Getting the welcome message from dialogflow
#                         self.response = await df_response(self.bot_entry, self.df_ses_id, "Hello")

#                     # Sending the welcome message
#                     await self.send(text_data=json.dumps({
#                         'fe_type': 'df_chat_message',
#                         'content': json.loads(self.response)
#                     }))
#                     self.botnassigned = not self.botnassigned
#                     print("botnassigned: ", self.botnassigned)
#                 else:
#                     self.disconnect()

#         elif msg_type == "chat_message":
#             text = text_data_json.get('text', None)

#             if self.talkto == "bot":
#                 # Functoin coming from dialogflow_func
#                 if self.bot_name == 'Dialogflow':
#                     self.response = await df_response(self.bot_entry, self.df_ses_id, text)
#                     self.response = json.loads(self.response)
#                     action = self.response['queryResult'].get('action', None)

#                 elif self.bot_name == 'RASA':
#                     self.response = {
#                         'text': 'Connect Rasa when needed'
#                     }

#                 else:  # Use if else when multiple NLP engines
#                     action = None

#                 # First unhandled message from the user
#                 if action == "input.unknown":
#                     # Send the client a notification that we are asking for an agent
#                     await self.send(
#                         text_data=json.dumps({
#                             'fe_type': 'agent_searching',
#                             'content': {
#                                 'text': "Could not understand you query, transferring the chat to agent",
#                                 'notification': 'Searching an human agent for you'
#                             }
#                         })
#                     )

#                     self.talkto = "agent"  # This variable will make sure all messages after first unknow messages are sent to agent
#                     self.agent_channel_name = await get_free_agent(self.bot_id)

#                     print("Client Sender: ", self.channel_name)
#                     # Send client details to agent dashboard
#                     await self.channel_layer.group_send(
#                         self.agent_channel_name,
#                         {
#                             'type': 'register_client',  # Calling function
#                             'message': {
#                                 "fe_type": "new_user",
#                                 'content': {
#                                     "client_name": str(self.client_name),
#                                     "client_channel_name": str(self.room_group_name)
#                                 }
#                             }
#                         }
#                     )

#                     await self.channel_layer.group_send(
#                         self.agent_channel_name,
#                         {
#                             'type': 'chat_message',  # Calling function
#                             'message': {"fe_type": "usr_chat_message",
#                                         "content": {'text': text,
#                                                     'client_name': self.client_name
#                                                     }
#                                         }
#                         }
#                     )
#                     # Cant reply to channel_name

#                 else:
#                     print("Client Sender: ", self.channel_name)
#                     # If action is None the Send the response usually if properly handled by the bot
#                     await self.send(text_data=json.dumps(
#                         {
#                             'fe_type': 'df_chat_message',
#                             'content': self.response
#                         }
#                     ))

#             # From second unhandled message from the user
#             else:
#                 await self.channel_layer.group_send(
#                     self.agent_channel_name,
#                     {
#                         'type': 'chat_message',  # Calling function
#                         'message': {
#                             'fe_type': 'usr_chat_message',
#                             'content': {'text': text,
#                                                  'client_name': self.client_name
#                                         }
#                         }
#                     }
#                 )
#         else:  # When msg_type is not sent
#             await self.send(text_data=json.dumps({"errorcode": 100, "errormsg": "Message type not defined"}))

#     # Send message to the same client/Websocket
#     async def chat_message(self, event):
#         message = event.get('message', None)

#         print("Client Receiver: ", self.channel_name)
#         print("Client Receiver: ", self.room_group_name)

#         # Send message to WebSocket
#         if self.room_group_name == self.channel_name:
#             print("True condition")

#         await self.send(text_data=json.dumps(message))


# class AgentAsyncConsumer(AsyncJsonWebsocketConsumer):

#     async def connect(self):
#         self.room_name = self.scope['url_route']['kwargs']['room_name']
#         self.room_group_name = 'agent_%s' % self.room_name
#         self.client_dict = {}

#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name
#         )

#         await self.accept()
#         await save_channel_name(self.room_group_name, "agent")
#         print("Agent Scope: ", self.scope)

#     async def disconnect(self, close_codee):
#         # Leave room group
#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )

#     # Receive message from WebSocket
#     async def receive(self, text_data):
#         # print(text_data)
#         # print('Text: ', text_data)
#         text_data_json = json.loads(text_data)
#         message = text_data_json.get('message', None)
#         client_name = text_data_json.get('client_name', None)
#         client_channel_name = self.client_dict[client_name]
#         # print(client_channel_name)
#         print(client_channel_name)
#         # print("Channel Name", client_channel_name)

#         # Send message to the same client/Websocket
#         # Send message to room group
#         await self.channel_layer.group_send(
#             client_channel_name,
#             {
#                 'type': 'chat_message',  # Caling function
#                 'message': {'fe_type': 'ag_chat_message',
#                             'content': {
#                                 'text': message
#                             }
#                             }
#             }
#         )

#     # Receive message from room group
#     async def chat_message(self, event):
#         message = event.get('message', None)

#         print("Agent Receiver: ", self.channel_name)
#         print("Agent Receiver: ", self.room_group_name)

#         # Send message to WebSocket
#         if self.room_group_name == self.channel_name:
#             print("True condition")
#         await self.send(text_data=json.dumps(message))

#     async def register_client(self, event):
#         print(dir(self))
#         # Parse variables
#         message = event.get('message', None)
#         content = event['message'].get('content', None)  # message coming from client consumer with unknown intent
#         client_name = content.get('client_name', None)
#         client_channel_name = content.get('client_channel_name', None)

#         print("Client Name: %s channel_name: %s " % (client_name, client_channel_name))
#         self.client_dict[client_name] = client_channel_name
#         # print(self.client_dict)
#         # print(message, client_name)
#         # Send client details to WebSocket (Frontend)

#         # Removing agent channel before sending to client
#         if content.get('client_channel_name') is not None:
#             message['content'].pop('client_channel_name')

#         # Sending agent the first unhandled message from client
#         await self.send(text_data=json.dumps(message))

#         # Send alloted agent details to client [client_name] (Channel Layer)
#         if client_channel_name is not None:
#             await self.channel_layer.group_send(
#                 client_channel_name,
#                 {
#                     'type': 'chat_message',
#                     'message': {
#                             'fe_type': 'agent_assigned',
#                             'content': {
#                                 # 'agent_channel' : self.channel_name,
#                                 'agent_name': self.room_name,
#                                 'notification': "You are connected to agent (%s)" % self.room_name,
#                             }
#                     }
#                 }
#             )
#         else:
#             await self.send(
#                 text_data=json.dumps(
#                     {
#                         'fe_type': 'error',
#                         'content': {
#                             'error_code': 100,  # client channel not found
#                             'error': "Could not send it to client perhaps due to client left/invalid client address."
#                         }
#                     }
#                 )
#             )


# # class AsyncConsumer:
# #     """
# #     Base consumer class. Implements the ASGI application spec, and adds on
# #     channel layer management and routing of events to named methods based
# #     on their type.
# #     """

# #     _sync = False
# #     channel_layer_alias = DEFAULT_CHANNEL_LAYER

# #     def __init__(self, scope):
# #         self.scope = scope

# #     async def __call__(self, receive, send):
# #         """
# #         Dispatches incoming messages to type-based handlers asynchronously.
# #         """
# #         # Initialize channel layer
# #         self.channel_layer = get_channel_layer(self.channel_layer_alias)
# #         if self.channel_layer is not None:
# #             self.channel_name = await self.channel_layer.new_channel()
# #             self.channel_receive = functools.partial(
# #                 self.channel_layer.receive, self.channel_name
# #             )
# #         # Store send function
# #         if self._sync:
# #             self.base_send = async_to_sync(send)
# #         else:
# #             self.base_send = send
# #         # Pass messages in from channel layer or client to dispatch method
# #         try:
# #             if self.channel_layer is not None:
# #                 await await_many_dispatch(
# #                     [receive, self.channel_receive], self.dispatch
# #                 )
# #             else:
# #                 await await_many_dispatch([receive], self.dispatch)
# #         except StopConsumer:
# #             # Exit cleanly
# #             pass

# #     async def dispatch(self, message):
# #         """
# #         Works out what to do with a message.
# #         """
# #         handler = getattr(self, get_handler_name(message), None)
# #         if handler:
# #             await handler(message)
# #         else:
# #             raise ValueError("No handler for message type %s" % message["type"])

# #     async def send(self, message):
# #         """
# #         Overrideable/callable-by-subclasses send method.
# #         """
# #         await self.base_send(message)
