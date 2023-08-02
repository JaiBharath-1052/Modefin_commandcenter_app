import json
import string
import random
import requests as r
# from asgiref.sync import sync_to_async

N = 7
username = "me"

# Server One
#base_url = 'http://{ip}'
#password = "{password}"


base_url='http://192.168.145.76'
password='modefin@123'



# @sync_to_async
async def get_token(username, password):
    auth_url = base_url + '/api/auth'
    data = {"username": username, "password": password}
    access_token = r.post(auth_url, data=json.dumps(data)).text
    return access_token


def get_key(mylist, keys):
    if isinstance(mylist, list):
        for item in mylist:
            result = item.get(keys, None)
            if result is not None:
                return result
    elif isinstance(mylist, dict):
        return mylist.get(keys, None)
    else:
        return None
    return None

# @sync_to_async


async def rasa_response(message="Hi", sender = None):
    response_url = base_url + '/webhooks/rest/webhook/'

    token = await get_token(username, password)
    hearders = {'Authorization': 'Bearer {0}'.format(token)}
    if sender is None:
        sender = ''.join(random.choices(string.ascii_uppercase + string.digits, k=N))
    data = {"sender": sender, "message": message}
    response = r.post(response_url, data=json.dumps(data)).text
    # response = r.post(response_url, json=data).text
    print(f"Data: {data}")
    response = json.loads(response)
    print("##### RASA RESPONSE ####: ", response)

    # When no intent found then the intent shuld be "input.unknown"
    # REWRITE THIS SECTION
    if len(response) > 0:
        custom = get_key(response, "custom")
        if custom is not None:
            intentName = custom.get('intent', "Other")
            intentDetectionConfidence = custom.get('Conf', 100)
        else:
            intentName = "Other"
            intentDetectionConfidence = 100

        text = get_key(response, "text")
        # print(text)
        # rasa_msg = rasa_response.get('text', None)

        # if rasa_msg == None:
        #rasa_response = json.loads(response)[1]
        #rasa_msg = rasa_response.get('text', None)
        #intentDetectionConfidence = json.loads(response)[0]['custom']['Confidence']

        # else:
        #intentDetectionConfidence = json.loads(response)[1]['custom']['Confidence']
        # intentDetectionConfidence = intentDetectionConfidence.get('custom',{'Confidence':0}).get('Confidence', 0)

    else:
        text = "I'm sorry, I didn't quite understand that. ;)"
        intentName = "out_of_scope"
        intentDetectionConfidence = 100

    # Prepare Dialogflow like response
    # metadata = {"contentType": "300", "payload": [{"title": "Account Balance", "message": "How can I find out my Account Balance?"}, {"message": "How can I check Mini Statement relating to my account?", "title": "Mini Statement"}, {"message": "How can I check Full Statement relating to my account?", "title": "Full Statement"}, {"message": "How can I apply for Cheque Book?", "title": "Cheque Book"}, {"message": "How can I do a mobile Recharge?", "title": "Mobile Recharge"}, {"title": "Funds Transfer", "message": "What kind of Funds Transfer can I do in mobile banking service?"}, {"message": "What is the detailed process of using Cardless Withdrawal service using ATM", "title": "Cardless Withdrawal"}, {"message": "How do I contact Bank Customer Care?", "title": "Customer Care"}, {"title": "COVID-19", "message": "How do I support for covid-19 fund?"}], "templateId": "6"}
    metadata = {}
    response = {"queryResult": {"fulfillmentMessages": [{"payload": {"metadata": metadata, "message": text}}], "action": intentName}, "intentDetectionConfidence": intentDetectionConfidence, "encode": "utf8"}

    return json.dumps(response)
