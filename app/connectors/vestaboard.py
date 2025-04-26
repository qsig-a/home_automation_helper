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

# --- Global variable to store the subscription ID ---
_cached_subscription_id = None

def GetSubscriptionId():
    """
    Gets the subscription ID, fetching it via API only if not already cached.
    Returns the subscription ID or None if an error occurs.
    """
    global _cached_subscription_id # Declare intention to modify the global variable

    # Check if already cached
    if _cached_subscription_id is not None:
        print("Using cached subscription ID.")
        return _cached_subscription_id

    # Not cached, fetch it
    print("Fetching subscription ID from API...")
    try:
        r = requests.get(base_url, headers=headers, timeout=10) # Added timeout
        r.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

        content = r.json()
        # Basic validation of response structure
        if "subscriptions" in content and isinstance(content["subscriptions"], list) and len(content["subscriptions"]) > 0 and "_id" in content["subscriptions"][0]:
             v_subid = str(content["subscriptions"][0]["_id"])
             _cached_subscription_id = v_subid # Cache the result
             print(f"Successfully fetched and cached subscription ID: {v_subid}")
             return v_subid
        else:
            print("Error: Unexpected response format from API.")
            return None # Indicate error

    except requests.exceptions.RequestException as e:
        print(f"Error getting subscription ID: {e}")
        return None # Indicate error
    except ValueError: # Includes JSONDecodeError
         print("Error: Could not decode JSON response from API.")
         return None # Indicate error
    except KeyError:
        print("Error: Missing expected keys ('subscriptions' or '_id') in API response.")
        return None # Indicate error

def SendArray(data):
    # Sends the message as an array of characters, see https://docs.vestaboard.com/methods for the 6x22 array

    # Get Subscription ID
    sub_id = GetSubscriptionId()

    data = {"characters" : data}
    msg_url = base_url + "/" + sub_id + "/message"
    r = requests.post(url=msg_url,headers=headers,json=data)
    if r.status_code == 200:
        return 0
    else:
        return 1

def SendArrayDelay(data):
    # Sends a message after 200 seconds, used for ending boggle game

    # Get Subscription ID
    sub_id = GetSubscriptionId()

    msg_url = base_url + "/" + sub_id + "/message"
    time.sleep(200)
    data = {"characters" : data}
    r = requests.post(url=msg_url,headers=headers,json=data)
    if r.status_code == 200:
        return 0
    else:
        return 1

def SendMessage(data):
    # Used for sending a message directly, checks valid characters

    # Get Subscription ID
    sub_id = GetSubscriptionId()

    string = str(data)
    if re.match(r"^[A-Za-z0-9!@$\(\)\-+&=;:\'\"\%,./?° ]*$",string):
        data = {"text" : data}
        msg_url = base_url + "/" + sub_id + "/message"
        r = requests.post(url=msg_url,headers=headers,json=data)
        if r.status_code == 200:
            return 0
        else:
            return 1
    else:
        return 2