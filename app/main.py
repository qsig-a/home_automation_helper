from fastapi import FastAPI
from app.models import MessageClass, BoggleClass
import app.games.boggle as bg
import app.connectors.vestaboard as board
import app.sayings.sayings as say
import os
import time
import threading

# Get Sayings DB Info
db_user = os.environ['SAYING_DB_USER']
db_passwd = os.environ['SAYING_DB_PASS']
db_host = os.environ['SAYING_DB_HOST']
db_port = os.environ['SAYING_DB_PORT']
db_db = os.environ['SAYING_DB_NAME']

app = FastAPI()

@app.post("/games/boggle")
#Boggle 4x4 or 5x5 Game with 3 minute and 20 second timer
async def boggle4(item: BoggleClass):
    if item.size in (4,5):
        start,end = bg.generate_boggle_grids(item.size)    
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

@app.get("/sfw_quote")
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

@app.get("/nsfw_quote")
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

@app.post("/message")
# Post message to Vestaboard
async def message(item: MessageClass):
    if item.message != None:
        if len(item.message) > 0:
            send = board.SendMessage(item.message)
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
        
@app.get("/")
# Home/Health Check?
async def home():
    return "Hello, World! I am the home automation helper" 
