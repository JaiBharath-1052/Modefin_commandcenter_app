#For creating micro services
import requests
import json



#THIS IS THE BOT API FUNCTION MADE TEMPORARILY SO THAT WE CAN GET BOT REPLIES
async def botApi(message):
    url = "http://127.0.0.1:9999/"
    headers = {'Content-Type': 'application/json'}
    payload = json.dumps({"msg": message})
    response = requests.request("POST", url,headers=headers, data=payload)
    return response.json()
    
