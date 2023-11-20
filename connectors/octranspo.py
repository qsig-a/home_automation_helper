import requests as re
import os
from prettytable import PrettyTable

oc_appID = os.getenv('OCTRANSPO_APPID')
oc_apiKey = os.getenv('OCTRANSPO_APIKEY')

def GetOCTranspoStopInfo(stopNo):

    base_stop_url = "https://api.octranspo1.com/v2.0/GetNextTripsForStop"
    
    query_params = {
    'appID': oc_appID,
    'apiKey': oc_apiKey,
    'stopNo': stopNo
    }

    next_busses_dict = {}

    table = PrettyTable()
    table.field_names = ["Route Number", "Bus Times"]

    response = re.get(base_stop_url, params=query_params)

    if response.status_code == 200:
        data = response.json()
        for route in data['GetNextTripsForStopResult']['Route']['RouteDirection']:
            routeNo = route['RouteNo']
            
            # Check if the routeNo key exists in the dictionary, if not, initialize it with an empty list
            if routeNo not in next_busses_dict:
                next_busses_dict[routeNo] = []
            
            for trip in route['Trips']['Trip']:
                if len(trip['GPSSpeed']) > 0:
                    next_busses_dict[routeNo].append(trip['AdjustedScheduleTime'] + "*")
                else:
                    next_busses_dict[routeNo].append(trip['AdjustedScheduleTime'])

    else:
        table = 1

    for route, bus_times in next_busses_dict.items():
        table.add_row([route, ', '.join(bus_times)])

    return(table)