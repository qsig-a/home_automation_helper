import requests, re, os, time

# Vestaboard Auth
v_auth = {
"v_apik" : os.getenv('VESTABOARD_API_KEY'),
"v_apis" : os.getenv('VESTABOARD_API_SECRET'),
}

# Common headers and url for sending to Vestaboard
headers = {'X-Vestaboard-Api-Key': v_auth.get("v_apik"),
    'X-Vestaboard-Api-Secret' : v_auth.get("v_apis"),
    'Content-Type': 'application/json'}
base_url = "https://platform.vestaboard.com/subscriptions"

def GetSubscriptionId():
    # Get subscription ID for sending messages
    r = requests.get(base_url,headers=headers)
    if r.status_code != 200:
        print("Error getting subscription ID!")
        v_subid = ''
        return v_subid
    else:
        content = r.json()
        v_subid = str(content["subscriptions"][0]["_id"])
        return v_subid

def SendArray(data):
    # Sends the message as an array of characters, see https://docs.vestaboard.com/methods for the 6x22 array
    data = {"characters" : data}
    msg_url = base_url + "/" + os.getenv('VESTABOARD_SUB_ID') + "/message"
    r = requests.post(url=msg_url,headers=headers,json=data)
    if r.status_code == 200:
        return 0
    else:
        return 1

def SendArrayDelay(data):
    # Sends a message after 200 seconds, used for ending boggle game
    msg_url = base_url + "/" + os.getenv('VESTABOARD_SUB_ID') + "/message"
    time.sleep(200)
    data = {"characters" : data}
    r = requests.post(url=msg_url,headers=headers,json=data)
    if r.status_code == 200:
        return 0
    else:
        return 1

def SendMessage(data):
    # Used for sending a message directly, checks valid characters
    string = str(data)
    if re.match("^[A-Za-z0-9!@$\(\)\-+&=;:\'\"\%,./?° ]*$",string):
        data = {"text" : data}
        msg_url = base_url + "/" + os.getenv('VESTABOARD_SUB_ID') + "/message"
        r = requests.post(url=msg_url,headers=headers,json=data)
        if r.status_code == 200:
            return 0
        else:
            return 1
    else:
        return 2