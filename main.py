from flask import Flask,request
import games.boggle as bg
import connectors.vestaboard as board
import connectors.octranspo as octranspo
import sayings.sayings as say
import os,time,threading

app = Flask(__name__)

@app.route("/games/boggle",methods=['POST'])
#Boggle 4x4 or 5x5 Game with 3 minute and 20 second timer
def boggle4():
    data = request.form
    if "size" in data:
        size = data.get("size")
        if len(size) > 0:
            if size in ("4","5"):
                start,end = bg.Boggle(size)    
                def endgame(end):
                    time.sleep(200)
                    board.SendArray(end)
                if len(start) > 0:
                    send = board.SendArray(start)
                    if send == 0:
                        x = threading.Thread(target=endgame,args=(end,))
                        x.start()
                        return "Game queued"
                    else:
                        return "Error creating game"
                else:
                    return "Error creating game"
            else:
                return "Wrong size boggle game!",400

@app.route("/sfw_quote",methods=['GET'])
# Get random SFW saying from local DB
def GetSingleRandomQuoteSFW():
    if os.environ['SAYING_DB_ENABLE'] == "1":
        data = say.GetSingleRandSfwS()
        if len(data) > 0:
            send = board.SendMessage(data)
            if send == 0:
                return "Random sfw quote queued"
            else:
                return "Error getting sfw quote",500
    else:
        return "Sayings DB Not Enabled",405

@app.route("/nsfw_quote",methods=['GET'])
# Get random NSFW saying from local DB
def GetSingleRandomQuoteNsfw():
    if os.environ['SAYING_DB_ENABLE'] == "1":
        data = say.GetSingleRandNsfwS()
        if len(data) > 0:
            send = board.SendMessage(data)
            if send == 0:
                return "Random nsfw saying queued"
            else:
                return "Error getting nsfw quote",500
    else:
        return "Sayings DB Not Enabled",405

@app.route("/message",methods=['POST'])
# Post message to Vestaboard
def message():
    data = request.form
    if "message" in data:
        message = data.get("message")
        if len(message) > 0:
            send = board.SendMessage(message)
            if send == 0:
                return "Message sent",200
            elif send == 1:
                return "Error sending message",500
            elif send == 2:
                return "Invalid characters, please see https://docs.vestaboard.com/characters",422
        else:
            return "No data in message",400
    else:
        return "No message was receieved",400

@app.route("/octranspo_stop",methods=['POST'])
# Get OC Transpo Stop Info
def octranspo_stop():
    if os.environ['OC_ENABLE'] == "1":
        data = request.form
        if "stop" in data:
            stop = data.get("stop")
            format = data.get("format")
            if stop.isdigit() and len(stop) == 4 and format in ['table','json']:
                stop_data = octranspo.GetOCTranspoStopInfo(stop, format)
                if stop_data == 1:
                    return "Error obtaining stop information",500
                else:
                    return stop_data, 200
    else:
        return "OCTranspo Not Enabled",405
            
        
@app.route("/")
# Home/Health Check?
def home():
    return "Hello, World! I am the home automation helper" 

# Run the thing
if __name__ == "__main__":
    #Get Vestaboard Subscription first
    v_subid = board.GetSubscriptionId()
    if len(v_subid) == 0:
        print("Error getting subscription ID from Vestaboard API!")
    else:
        os.environ["VESTABOARD_SUB_ID"] = v_subid
    app.run(host="0.0.0.0",debug=False,port=int(os.environ.get('PORT')))