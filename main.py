from flask import Flask,request
import games.boggle as bg
import board
import sayings.sayings_proc as say
import os,time,threading

app = Flask(__name__)

#Boggle 4x4 or 5x5 Game with 3 minute and 20 second timer
@app.route("/games/boggle",methods=['POST'])
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

#GetSingleRandomQuote from local DB
@app.route("/quote",methods=['GET'])
def GetSingleRandomQuote():
    data = say.GetSingleRandQuote()
    if len(data) > 0:
        send = board.SendMessage(data)
        if send == 0:
            return "Random quote queued"
        else:
            return "Error getting quote",500

# Post message to Vestaboard
@app.route("/message",methods=['POST'])
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
        
# Home/Health Check?
@app.route("/")
def home():
    return "Hello, World! I am the vestaboard bot" 

# Run the thing
if __name__ == "__main__":
    app.run(host="0.0.0.0",debug=False,port=int(os.environ.get('PORT', 3020)))