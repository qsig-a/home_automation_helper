import requests,re
import os,time

# Auth
v_auth = {
"v_apik" : os.getenv('VESTABOARD_API_KEY'),
"v_apis" : os.getenv('VESTABOARD_API_SECRET'),
"v_subid" : os.getenv('VESTABOARD_SUB_ID')
}

# Common headers and url for sending to Vestaboard
headers = {'X-Vestaboard-Api-Key': v_auth.get("v_apik"),
    'X-Vestaboard-Api-Secret' : v_auth.get("v_apis"),
    'Content-Type': 'application/json'}
url = "https://platform.vestaboard.com/subscriptions/" + v_auth.get("v_subid") + "/message"

#SendArray
def SendArray(data):
    data = {"characters" : data}
    r = requests.post(url=url,headers=headers,json=data)
    if r.status_code == 200:
        return 0
    else:
        return 1

#SendArrayDelay
def SendArrayDelay(data):
    time.sleep(200)
    data = {"characters" : data}
    r = requests.post(url=url,headers=headers,json=data)
    if r.status_code == 200:
        return 0
    else:
        return 1

#SendMessage
def SendMessage(data):
    data = {"text" : data}
    r = requests.post(url=url,headers=headers,json=data)
    if r.status_code == 200:
        return 0
    else:
        return 1