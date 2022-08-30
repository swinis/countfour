from sqlite3 import Row
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid
import json
import sys
import vgdatabase

# start server for api w/ 
#   uvicorn --reload --port 3033 vgserver:vgserver

#
# class VGGameController
# (07/2022) Stefan Windus
#
# implements inferface for API endpoints to game logic

class VGGameController(vgdatabase.GameDB):
    def renderPitch(self, gameID, playerNo):
        # render screen w/ board, additional information and instructions

        # information on current game
        sInfo = ""
        # centered layout should have fixed size in columns and rows to avoid "jumping pitch"
        for i in range(80):
            sInfo = sInfo + " "

        sInfo = sInfo + "\nHi Player #" + str(playerNo) + ", rou're playing game: " + str(gameID) + "\n\n"
        if self.isGameActive(gameID):
            if self.isItMyTurn(gameID, playerNo):
                sInfo = sInfo + "It's your turn, please select your column\n\n\n\n"
            else:
                sInfo = sInfo + "Please wait, it's others players turn...\n\n\n\n"
        else:
            if self.getGameStatus(gameID) == "WAITING":
                sInfo = sInfo + "Waiting for second player to join\n\n\n\n"
            elif self.getGameStatus(gameID) == "CANCELED":
                sInfo = sInfo + "Your opponent was scared? - He quit\n\nPress 's' to start a new game\n\n"
            elif self.getGameStatus(gameID) == "STALEMATE":
                sInfo = sInfo + "Did not know that this could even happen... ;) - STALEMATE\n\nPress 's' for next try...\n\n"
            else:
                if self.didIWin(gameID, playerNo):
                    sInfo = sInfo + "YIPEEE - You WON :)\n\nPress 's' because it feels good...\n\n"
                else:
                    sInfo = sInfo + "YIP... mpffff - seems, you lost. Need a hankie?\n\nPress 's' to try better...\n\n"

        # render board
        arrBoard = self.getGameBoard(gameID)
        board = ""
        prepend = "   "
        for x in range(self.boardRows):
            for y in range(self.boardColumns):
                sField = " "
                if arrBoard[x][y] == 1:
                    sField = "X"
                if arrBoard[x][y] == 2:
                    sField = "O"
                board += prepend  + " | " + sField
                prepend = ""
            board += " |\n"
            prepend = "   "
        board += prepend + "------------------------------\n"
        board += prepend + "   1   2   3   4   5   6   7"
        
        return sInfo + board
        
    def __init__(self):
        super().__init__()

## START Gameserver
gameController = VGGameController()

### GameServer API
vgserver = FastAPI()

@vgserver.get("/registersession")
def get_registersession():
    # client requests for a new session token
    global gameController
    sSessionToken = str(uuid.uuid1())
    gameController.registerSession(sSessionToken)
    return {"token": sSessionToken }

@vgserver.get("/requestgame/{session}")
def get_requestgame(session: str):
    # already registered client requests for a new game
    # checks, if session is valid (already registered)
    global gameController
    if not gameController.isSessionRegistered(session):
        return False
    else:
        # returns { "gameid": gameID, "playerno": playerNo, "status": gameStatus }
        return gameController.attachPlayerToFreeGameSlot(session)

@vgserver.get("/gamestatus/{gameid}")
def get_gamestatus(gameid: int, playerno: int):
    global gameController
    status = gameController.getGameStatus(gameid)
    pitch = gameController.renderPitch(gameid, playerno)

    return { "gameid": gameid, "status": status, "pitch": pitch }

@vgserver.post("/dropCoin/{gameid}")
def post_setcolumn(gameid: int, playerno: int, key: str):
    global gameController
    # returns { "status": Statustext }
    return gameController.dropCoin(gameid, playerno, key)

@vgserver.post("/quitgame/{gameid}")
def post_quitgame(gameid: int):
    global gameController
    return gameController.setGameStatus(gameid, "CANCELED")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(vgserver, host="0.0.0.0", port=3033, log_level="info")

