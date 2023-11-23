import requests as re
import os
from prettytable import PrettyTable
import json

oc_appID = os.getenv('OCTRANSPO_APPID')
oc_apiKey = os.getenv('OCTRANSPO_APIKEY')

def GetOCTranspoStopInfo(stopNo, output_format):
    base_stop_url = "https://api.octranspo1.com/v2.0/GetNextTripsForStop"
    
    query_params = {
        'appID': oc_appID,
        'apiKey': oc_apiKey,
        'stopNo': stopNo
    }

    next_busses_dict = {}

    response = re.get(base_stop_url, params=query_params)

    if response.status_code == 200:
        data = response.json()
        for route in data['GetNextTripsForStopResult']['Route']['RouteDirection']:
            routeNo = route['RouteNo']
            routeLabel = route['RouteLabel']
            key = (routeNo, routeLabel)
            if key not in next_busses_dict:
                next_busses_dict[key] = ([], routeLabel)
            
            for trip in route['Trips']['Trip']:
                if len(trip['GPSSpeed']) > 0:
                    next_busses_dict[key][0].append(trip['AdjustedScheduleTime'] + "*")
                else:
                    next_busses_dict[key][0].append(trip['AdjustedScheduleTime'])
    else:
        error_message = {"error": f"{response.status_code}, {response.text}"}
        return json.dumps(error_message, indent=2) if output_format == "json" else str(error_message)

    if output_format == "json":
        result_dict = {}
        for (routeNo, routeLabel), (bus_times, _) in next_busses_dict.items():
            result_dict[routeNo] = {
                "RouteLabel": routeLabel,
                "BusTimes": bus_times
            }
        return json.dumps(result_dict, indent=2)
    elif output_format == "table":
        table = PrettyTable()
        table.field_names = ["Route Number", "Route Label", "Bus Times"]
        for (routeNo, routeLabel), (bus_times, _) in next_busses_dict.items():
            table.add_row([routeNo, routeLabel, ', '.join(bus_times)])
        return table.get_string()
    else:
        return "Invalid output format. Please use 'json' or 'table'."
