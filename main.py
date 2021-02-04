from flask import Flask,request
import games.boggle as bg
import board
import os
app = Flask(__name__)

@app.route("/games/boggle4",methods=['POST'])
def boggle4():
    data = bg.Boggle4x4()
    if len(data) > 0:
        send_board = board.SendArray(data)
        if send_board == 0:
            return "Game queued"
        else:
            return "Error creating game"
    else:
        return "Error creating game"

@app.route("/message",methods=['POST'])
def message():
    data = request.form
    if "message" in data:
        message = data.get("message")
        if len(message) > 0:
            send_msg = board.SendMessage(message)
            if send_msg == 0:
                return "Message sent",200
            elif send_msg == 1:
                return "Error sending message",500
            elif send_msg == 2:
                return "Invalid characters, please see https://docs.vestaboard.com/characters",422
        else:
            return "No data in message",400
    else:
        return "No message was receieved",400
        
@app.route("/")
def home():
    return "Hello, World! I am the vestaboard bot" 


if __name__ == "__main__":
    app.run(host="0.0.0.0",debug=False,port=int(os.environ.get('PORT', 3020)))