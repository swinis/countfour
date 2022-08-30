from multiprocessing.util import is_abstract_socket_namespace
import sqlite3
import os 
import sys
import json
from typing import IO

#
# class GameDB
# (07/2022) Stefan Windus
#
# implements handling of data, status related data for Connect 4 game


class GameDB():
    boardColumns:int = 7
    boardRows:int = 6

    def createDB(self):
        # creates tables in GameDB

        sSQLScript = """
        DROP TABLE IF EXISTS games;
        DROP TABLE IF EXISTS players;
        CREATE TABLE games (
            game_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player1 INTEGER NOT NULL,
            player2 INTEGER DEFAULT 1,
            status VARCHAR(20) DEFAULT 'WAITING',
            board JSON,
            CHECK (status in ('WAITING','PLAYER1','PLAYER2', '1WON', '2WON', 'STALEMATE', 'CANCELED')));
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_token VARCHAR(40));
        /* create dummy entry in dbs */
        INSERT INTO players (player_token) values ('dummy');
        INSERT INTO players (player_token) values ('block');
        INSERT INTO games (player1, player2) values (2, 2);
        """
        self.dbC.executescript(sSQLScript)
        self.dbSession.commit()
        return True

    def getGameBoard(self, gameID):
        # fetches current set board from database and returns it as an array
        sSQL = "SELECT board FROM games WHERE game_id = " + str(gameID) + ";"
        self.dbC.execute(sSQL)
        rResult = self.dbC.fetchone()
        if rResult is None:
            return False
        else:
            return json.loads(rResult[0])

    def setGameBoard(self, gameID, arrBoard):
        # stores current board for game gameID to database

        jsonBoard = json.dumps(arrBoard)
        sSQL = "UPDATE games set board=? WHERE game_id=?;"
        self.dbC.execute(sSQL, (json.dumps(arrBoard), gameID))
        self.dbSession.commit()

    def isItMyTurn(self, gameID, playerNo):
        sGameStatus = self.getGameStatus(gameID)
        if ((playerNo == 1 and sGameStatus == "PLAYER2") or
            (playerNo == 2 and sGameStatus == "PLAYER1") or 
            (sGameStatus != "PLAYER1" and sGameStatus != "PLAYER2")):
                return False
        return True

    def didIWin(self, gameID, playerNo):
        sGameStatus = self.getGameStatus(gameID)
        if ((playerNo == 1 and sGameStatus == "1WON") or
            (playerNo == 2 and sGameStatus == "2WON")):
                return True
        return False

    def isGameActive(self, gameID):
        sGameStatus = self.getGameStatus(gameID)
        if sGameStatus != "PLAYER1" and sGameStatus != "PLAYER2":
            return False
        return True

    def isGameFinished(self, gameID):
        # check if a player connected 4 tiles
        arrBoard = self.getGameBoard(gameID)

        # not wanted from anyone, but probably stalemate?
        # as both players played same amount of moves, we simply can add them up and compare with max possible
        iSum=0
        iStaleMate = self.boardColumns*self.boardRows/2*3
        for i in range(0, self.boardRows):
            iSum = iSum + sum(arrBoard[i])
        if iSum == iStaleMate:
            self.setGameStatus(gameID, "STALEMATE")
            return True

        # now check for 4 in a row
        countPlayer1 = 0
        countPlayer2 = 0
        sStatus = ""
        for iRow in range(0, self.boardRows):
            for iColumn in range (0, self.boardColumns):
                if arrBoard[iRow][iColumn] == 1:
                    countPlayer1 += 1
                    countPlayer2 = 0
                elif arrBoard[iRow][iColumn] == 2:
                    countPlayer1 = 0
                    countPlayer2 += 1
                else:
                    countPlayer1 = countPlayer2 = 0
                if countPlayer1 == 4:
                    sStatus = "1WON"
                if countPlayer2 == 4:
                    sStatus = "2WON"
            countPlayer1 = countPlayer2 = 0
        if sStatus != "":
            self.setGameStatus(gameID, sStatus)
            return True

        # did not find a winner yet, need to check for 4 in a column
        for iColumn in range (0, self.boardColumns):
            for iRow in range(0, self.boardRows):
                if arrBoard[iRow][iColumn] == 1:
                    countPlayer1 += 1
                    countPlayer2 = 0
                elif arrBoard[iRow][iColumn] == 2:
                    countPlayer1 = 0
                    countPlayer2 += 1
                else:
                    countPlayer1 = countPlayer2 = 0
                if countPlayer1 == 4:
                    sStatus = "1WON"
                if countPlayer2 == 4:
                    sStatus = "2WON"
            countPlayer1 = countPlayer2 = 0
        if sStatus != "":
            self.setGameStatus(gameID, sStatus)
            return True

        # still no winner yet, have to check the diagonals :(
        for iRow in range(0, self.boardRows - 3):
            for iColumn in range(0, self.boardColumns - 3):
                for iOffset in range(0, 4):
                    if arrBoard[iRow + iOffset][iColumn + iOffset] == 1:
                        countPlayer1 += 1
                        countPlayer2 = 0
                    elif arrBoard[iRow + iOffset][iColumn + iOffset] == 2:
                        countPlayer1 = 0
                        countPlayer2 += 1
                    else:
                        countPlayer1 = countPlayer2 = 0
                    if countPlayer1 == 4:
                        sStatus = "1WON"
                    if countPlayer2 == 4:
                        sStatus = "2WON"
                countPlayer1 = countPlayer2 = 0
        if sStatus != "":
            self.setGameStatus(gameID, sStatus)
            return True

        # and last but not least ... the diagonals backwards...
        for iRow in range(0, self.boardRows - 3):
            for iColumn in range(self.boardColumns - 1, 2, -1):
                for iOffset in range(0, 4):
                    if arrBoard[iRow + iOffset][iColumn - iOffset] == 1:
                        countPlayer1 += 1
                        countPlayer2 = 0
                    elif arrBoard[iRow + iOffset][iColumn - iOffset] == 2:
                        countPlayer1 = 0
                        countPlayer2 += 1
                    else:
                        countPlayer1 = countPlayer2 = 0
                    if countPlayer1 == 4:
                        sStatus = "1WON"
                    if countPlayer2 == 4:
                        sStatus = "2WON"
                countPlayer1 = countPlayer2 = 0
        if sStatus != "":
            self.setGameStatus(gameID, sStatus)
            return True
        return False        

    def dropCoin(self, gameID, playerNo, column):
        # player playerNo dropped his coin into column 

        if not self.isGameActive(gameID):
            return { "status": "Not an active Game" }
        if not self.isItMyTurn(gameID, playerNo):
            return { "status": "ITs. NOT. YOUR. TURN. ...\n\n DON'T PRESS BUTTONS" }

        # force typecast of column as it was a str
        iColumn:int = int(column)
        if iColumn not in range(1, self.boardColumns + 1):
            return { "status": "Selected column out of range" }
        
        arrBoard = self.getGameBoard(gameID)

        # align selected column to be array index
        iColumn -= 1

        for iRow in range((self.boardRows - 1), -1, -1):
            if arrBoard[iRow][iColumn] == 0:
                arrBoard[iRow][iColumn] = playerNo
                playerNo = 0

        if playerNo > 0:
            return { "status": "Column is full, coin would fall onto your desktop...\n\nTry again" }
        
        self.setGameBoard(gameID, arrBoard)

        # check, if there is a winner (or stalemate)
        if self.isGameFinished(gameID):
            return { "status": "ok" }

        sPlayer = "PLAYER1"
        if sPlayer == self.getGameStatus(gameID):
            sPlayer = "PLAYER2"
        self.setGameStatus(gameID, sPlayer)
        return { "status": "ok" }

    def setGameStatus(self, gameID, sStatus):
        # sStatus is not validated, application would throw exception because of constraint on respective column
        sSQL = "UPDATE games SET status = '" + sStatus + "' WHERE game_id = " + str(gameID) + ";"
        self.dbC.execute(sSQL)
        self.dbSession.commit()
        # debug sw - return gameid new status
        return { "status": "exit" }

    def getGameStatus(self, gameID):
        # get status of game gameID
        sSQL = "SELECT status FROM games WHERE game_id = " + str(gameID) + ";"
        self.dbC.execute(sSQL)
        rResult = self.dbC.fetchone()
        if rResult is None:
            return False
        else:
            return rResult[0]

    def isSessionRegistered(self, sSessionToken):
        sSQL = "SELECT player_id from players where player_token='" + sSessionToken + "';"
        self.dbC.execute(sSQL)
        rResult = self.dbC.fetchone()
        if rResult is None:
            return False
        else:
            return True

    def registerSession(self, sSessionToken):
        # selects id for sSessionToken, creates new record in DB if not already in list
        # and returns ID of it

        # don't hijack sessions
        if self.isSessionRegistered(sSessionToken):
            return False

        sSQL = "SELECT player_id from players where player_token='" + sSessionToken + "';"
        self.dbC.execute(sSQL)
        rResult = self.dbC.fetchone()
        if rResult is None:
            # create new record for session
            sSQL = "INSERT INTO players (player_token) values ('" + sSessionToken + "');"
            self.dbC.execute(sSQL)
            return self.dbC.lastrowid
        else:
            return rResult[0]

    def attachPlayerToFreeGameSlot(self, sSessionToken):
        # assign player to next free game and 
        # return status of attached game

        # get player-id for given session token
        playerID = self.registerSession(sSessionToken)
        gameID = 0
        playerNo = 0
        gameStatus = "WAITING"

        # search for a game with second free slot
        sSQL= """
        SELECT games.game_id from games, players
            WHERE games.player2 = players.player_id
            AND players.player_token='dummy';
        """
        self.dbC.execute(sSQL)
        rResult = self.dbC.fetchone()
        if rResult is None:
            # no open game left, therefore start new game with status WAITING for 2nd player
            playerNo = 1
            arrBoard = [[0 for x in range(self.boardColumns)] for y in range(self.boardRows)]

            sSQL="INSERT INTO games (player1, board) values (?, ?)"
            self.dbC.execute(sSQL, (playerID, json.dumps(arrBoard)))
            self.dbSession.commit()
            gameID = self.dbC.lastrowid
        else:    
            # assign player to already open game
            # and set status to be players 1 turn
            playerNo = 2
            gameStatus = "PLAYER1"
            gameID = rResult[0]
            sSQL = "UPDATE games set player2=" + str(playerID) + ", status='PLAYER1' WHERE game_id=" + str(gameID) + ";"
            self.dbC.execute(sSQL)
            self.dbSession.commit()
        return { "gameid": gameID, "playerno": playerNo, "status": gameStatus }

    def __init__(self,sFilename='/db/gameserver.sqlite'):
        # GAMEDB constructor:
        #   check, if path for db exists, if not, create it
        #   create database and add tables, when needed

        # split path from filename
        sPath = os.path.split(sFilename)[0].replace('..','') # ensure, that path is inside current directory
        sFilename = os.path.split(sFilename)[1]
        
        # if path is not in current directory ...
        if sPath and sPath != '.':
            try:
                # ... try to create it, if not yet exists
                os.makedirs('./' + sPath, exist_ok=True)
                sFilename = sPath + '/' + sFilename
            except OSError as error:
                print('Failed to create directory for storing db', error)
            
        ## finaly open/create GameDB
        try:
            self.dbSession = sqlite3.connect('./' + sFilename, check_same_thread=False)
        except sqlite3.Error as error:
            print('Failed to connect to SQLite3 db with error', error)

        # check, if database was just created when starting the app
        self.dbC = self.dbSession.cursor()
        sSQL = """
        SELECT name FROM sqlite_schema 
        WHERE type='table';
        """
        self.dbC.execute(sSQL)

        if not next(self.dbC, [None])[0]:
            # GameDB is empty, tables need to be created 
            self.createDB()


    def __del(self):
        self.dbC.close()



