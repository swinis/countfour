from asyncore import loop
from re import I
from unittest import case
from textual.app import App
from textual.widgets import Placeholder, Header, Footer
from textual.views import DockView
from rich.panel import Panel
from rich.align import Align
import requests
import json
from dotenv import load_dotenv
import os
import sys
import asyncio 

#
# class VGClientApp
# (07/2022) Stefan Windus
#
# Connect 4 Client
# 
# class based on textual app providing UI and game_loop for connecting via API to gameserver

# get settings variables from .env
load_dotenv()

# read game settings from .env file - needs to be located in current directory
GAMESERVER = str(os.getenv("GAMESERVER"))

class VGPitch(Placeholder):
    renderContent="""
Welcome to Connect Four - REST version.

Press 'S' to start a new game.
"""   
    def on_mount(self):
        self.set_interval(1, self.refresh)
    def render(self,) -> Panel:
        return Panel(Align.center(self.renderContent, vertical="middle"))

class VGClient(App):
    iPollAPIFrequence:int = 3

    SESSIONTOKEN = None
    GAMEID = None
    bGameActive = False
    sGameStatus = None
    iPlayerNo = 0

    ### create UI
    async def on_mount(self) -> None:
        # create UI
        # bind keys for footer
        await self.bind("q", "quit", "Quit")
        await self.bind("s", "startgame", "Start Game")

        # render page incl. header, pitch and footer
        header = Header(tall=False)
        footer = Footer()
        await self.view.dock(footer, edge="bottom")
        await self.view.dock(header)
        await self.view.dock(VGPitch(name="pitch"), edge="top")

    async def game_loop(self, gameID, playerNo):
        # request and render current running game status to pitch every self.iPollAPIFrequence seconds
        url = GAMESERVER + "/gamestatus/" + str(gameID) + "?playerno" + str(playerNo)

        self.bGameActive = True
        self.iPlayerNo = playerNo

        while self.bGameActive:
            url = GAMESERVER + "/gamestatus/" + str(gameID) + "?playerno=" + str(playerNo)
            myResponse = requests.get(url)
            if(myResponse.ok):
                jData = json.loads(myResponse.content)
                self.sGameStatus = jData["status"]
                VGPitch.renderContent = jData["pitch"] 
                if jData["status"] == "1WON" or jData["status"] == "2WON" or jData["status"] == "STALEMATE" or jData["status"] == "CANCELED":
                    self.bGameActive = False
                await asyncio.sleep(self.iPollAPIFrequence)
            else:
                myResponse.raise_for_status()
                self.bGameActive = False
        return 

    def request_game(self, sSessionToken):
        url = GAMESERVER + "/requestgame/" + sSessionToken
        myResponse = requests.get(url)
        if(myResponse.ok):
            # new game can be started
            jData = json.loads(myResponse.content)
            self.GAMEID = jData["gameid"]
            # start game loop to periodically poll game status from gameserver and render it to pitch
            event_loop = asyncio.get_event_loop()
            asyncio.ensure_future(self.game_loop(jData["gameid"], jData["playerno"] ), loop=event_loop)
        else:
            # failed to request for a new game -> quit
            myResponse.raise_for_status()
        return

    ### keys pressed actions
    async def action_startgame(self):
        # User wants to start a new game w/ pressing "s" key
        # but only allowed, if no game already active
        if self.bGameActive:
            return False

        VGPitch.renderContent="Game will be started, give me some seconds to initialize"

        if self.SESSIONTOKEN == None:
            # Create Session Token for game, as not yet registered at server
            url = GAMESERVER + "/registersession"
            myResponse = requests.get(url)
            if(myResponse.ok):
                jData = json.loads(myResponse.content)
                self.SESSIONTOKEN = jData["token"]
            else:
                # fetch token failed -> quit
                myResponse.raise_for_status()

        # session token is available, new game can be started
        self.request_game(self.SESSIONTOKEN)

    def on_key(self, event):
        # only during ongoing Game, wait for keys pressed
        if not self.bGameActive:
            return False

        # start move
        url = GAMESERVER + "/dropCoin/" + str(self.GAMEID) + "?playerno=" + str(self.iPlayerNo) + "&key="

        # restrict columns that can be selected
        allowedColumns= ["1","2","3","4","5","6","7"]
        if event.key in allowedColumns:
            VGPitch.renderContent = "... please wait ..."
            url += str(event.key)
            # and now let's drop the coin...
            myResponse = requests.post(url)
            if(myResponse.ok):
                jData = json.loads(myResponse.content)
                # if something went wrong, i.e. column full, render to pitch to inform player
                if jData["status"] != "ok":
                    VGPitch.renderContent = jData["status"]
            else:
                myResponse.raise_for_status()

    async def close_all(self) -> None:
        # exit app and try to be graceful
        url = GAMESERVER + "/quitgame/" + str(self.GAMEID)
        myResponse = requests.post(url)
        if(myResponse.ok):
            jData = json.loads(myResponse.content)
            if jData["status"] != "ok":
                VGPitch.renderContent = jData["status"]
        else:
            myResponse.raise_for_status()
        return await super().close_all() 

VGClient.run(title="Connect Four")