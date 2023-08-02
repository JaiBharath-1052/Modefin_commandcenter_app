import os
import json
import random
import dialogflow
from asgiref.sync import sync_to_async
from google.oauth2 import service_account
from google.protobuf.json_format import MessageToJson
# from channels.db import database_sync_to_async
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods

# Focused
# from .models import GCred #Remove completely

# @sync_to_async


# @database_sync_to_async
def df_response(bot_entry, session_id, inputtext, context_short_name="does_not_matter", language_code="en", parameters=None):
    session_id = str(session_id)
    if bot_entry is None:
        response = json.loads('{"type":"DB response", "message":"No bot found" }')
        response = json.dumps(response)
        return response

    # Retrieve agent credentials
    # bot_entry = GCred.objects.get(bot_id=bot_id)

    # DialogFlow configurations
    project_id = bot_entry.project_id
    credentials_json = json.loads(bot_entry.json_cred)
    credentials = (service_account.Credentials.from_service_account_info(credentials_json))

    # Start conversation
    if parameters is None:
        parameters = dialogflow.types.struct_pb2.Struct()
    else:
        parameters = dialogflow.types.struct_pb2.Struct()

    context_name = "projects/" + project_id + "/agent/sessions/" + session_id + "/contexts/" + context_short_name.lower()

    context = dialogflow.types.context_pb2.Context(name=context_name, lifespan_count=2, parameters=parameters)
    query_params = {"contexts": [context]}
    session_client = dialogflow.SessionsClient(credentials=credentials)
    session = session_client.session_path(project_id, session_id)

    # Transformation
    text_input = dialogflow.types.TextInput(text=inputtext, language_code=language_code)
    query_input = dialogflow.types.QueryInput(text=text_input)
    response = session_client.detect_intent(session=session, query_input=query_input, query_params=query_params)

    response = MessageToJson(response)
    response = json.loads(response)
    response['encode'] = 'utf8'
    return json.dumps(response)


@sync_to_async
def get_bot_settings(bot_id):
    json_setting = '{"type":"settings","code":"SUCCESS","response":{"userName":"Shrewd Oyster","agentId":"vojewo3915@mail2paste.com","agentName":"vojewo","chatWidget":{"popup":true,"position":"right","iconIndex":1,"fileUpload":"awsS3Server","primaryColor":"#00a79d","showPoweredBy":false,"secondaryColor":"","widgetImageLink":"","notificationTone":"subtle","botMessageDelayInterval":1000},"collectFeedback":true,"customerCreatedAt":"2020-08-04T07:27:08.000Z","chatPopupMessage":[{"id":1181,"appSettingId":24388,"templateKey":1,"message":"Hi Vinay","url":null,"delay":5000}]}}'
    json_setting = json.loads(json_setting)
    return json.dumps(json_setting)


@sync_to_async
def get_free_agent(bot_id):
    with open("agent.txt", "r+") as f:
        agent_channel_name = f.read()
    return agent_channel_name


@sync_to_async
def save_channel_name(agent_channel_name, user):
    if user == 'agent':
        with open("agent.txt", "w") as f:
            f.write(agent_channel_name)
    elif user == 'client':
        with open("agent.txt", "w") as f:
            f.write(agent_channel_name)


@sync_to_async
def get_df_ses_id(bot_id):
    # Return string case of session ID
    return "123456789"


@sync_to_async
def get_rand_name():
    # Valid names as it is used as dict key in agent consumer
    # ---No Spaces, special charc
    names = ['Ram', 'Sham', 'Ramesh', 'Suresh', 'Nikita', 'Akansha', 'Pallavi']
    return str(random.choice(list(names)))
