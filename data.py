import discord
from discord.utils import get
import datetime as dt
from classes import *

import gspread
gs = gspread.service_account(filename='.json')
sh = gs.open('NomicDOR')
ws1 = sh.worksheet('Player Stats')
ws2 = sh.worksheet('Turns')
ws3 = sh.worksheet('Misc Bot Stuff')


def loadData(nomicServer):
    players = []
    turns = []
    game = None

    game = Parameters()
    game.turn = ws3.acell('B3').value
    game.globalTurn = ws3.acell('B4').value
    game.state = ws3.acell('B5').value
    game.voteNumber = ws3.acell('B7').value
    game.proposalTime = ws3.acell('B9').value
    game.votingTime = ws3.acell('B10').value
    game.yesProportion = [float(i) for i in ws3.acell('B11').value.split(',')]
    game.timeoutProportion = [float(i) for i in ws3.acell('B12').value.split(',')]
    game.transmute = ws3.acell('B13').value
    game.timerEnd = ws3.acell('B14').value
    summaryMsg = ws3.acell('B16').value
    game.convert()

    for i in range(int(ws3.acell('B1').value)):
        nextPlayer = get(nomicServer.members, id=int(ws1.cell(2, i+2).value))
        nextPlayer = Player(nextPlayer)
        if nextPlayer.discord is None:
            nextPlayer.discord = ws1.cell(1, i+2).value
        nextPlayer.name = ws1.cell(1, i+2).value
        nextPlayer.points = ws1.cell(4, i+2).value
        vote = ws1.cell(5,i+2).value
        if vote is None:
            nextPlayer.currentVote = Vote(None, '', nextPlayer)
        else:
            vote = vote.split(',')
            vote[0] = int(vote[0])
            if vote[1] != '':
                vote[1] = int(vote[1])
            nextPlayer.currentVote = Vote(vote[0], vote[1], nextPlayer)
        j = 8
        for k in nextPlayer.stats:
            nextPlayer.stats[k] = ws1.cell(j, i+2).value
            j += 1
        nextPlayer.convert()
        players.append(nextPlayer)

    for i in range(game.globalTurn-1):
        nextTurn = Turn(i+1)
        nextTurn.proponent = get(players, discord__id=int(ws2.cell(i+4, 2).value))
        if nextTurn.proponent is None:
            nextTurn.proponent = ws2.cell(i+4, 3).value
        nextTurn.passed = ws2.cell(i+4, 4).value
        nextTurn.end = ws2.cell(i+4, 5).value
        for j in range(len(players)):
            vote = ws2.cell(i+4,j+6).value
            if vote is None:
                nextTurn.voteHistory[j] = Vote(None, '', players[j])
            else:
                vote = vote.split(',')
                vote[0] = int(vote[0])
                if vote[1] != '':
                    vote[1] = int(vote[1])
                nextTurn.voteHistory[j] = Vote(vote[0], vote[1], players[j])
        nextTurn.convert()
        turns.append(nextTurn)
    
    return game, players, turns, summaryMsg



def saveData(game, players, summaryMsg):
    ws3.update('B7',game.voteNumber)
    ws3.update('B13',game.transmute)
    if summaryMsg: ws3.update('B16',str(summaryMsg.id))
    else: ws3.update('B16',None)
    for player in players:
        i = players.index(player)
        ws1.update_cell(4, i+2, player.points)
        if player.currentVote.value is None:
            ws1.update_cell(5, i+2, None)
        else:
            ws1.update(5, i+2, str(player.currentVote.value) + ',' + str(player.currentVote.order))

    for player in players:
        i = 8
        for stat in player.stats.values():
            ws1.cell(i, players.index(player)+2, stat)
            i += 1
    print("Common Save " + str(dt.datetime.now()))


def endPhaseSave(game, players, turns):
    ws3.update('B3',game.turn)
    ws3.update('B4',game.globalTurn)
    ws3.update('B5',game.state)
    ws3.update('B7',game.voteNumber)
    ws3.update('B13',game.transmute)
    ws3.update('B14',game.timerEnd.isoformat())
    ws3.update('B16',None)
    for player in players:
        i = players.index(player)
        ws1.update_cell(4, i+2, player.points)
        ws1.update_cell(5, i+2, None)

    i = game.globalTurn-1
    j = 6
    for vote in turns[i].voteHistory:
        if vote.value is None:
            ws2.update_cell(i+4, j, None)
        else:
            ws2.update_cell(i+4, j, str(vote.value) + ',' + str(vote.order))
        j += 1
    ws2.update_cell(i+4, 1, turns[i].turnNumber)
    proponent = turns[i].proponent
    if not isinstance(proponent, str):
        ws2.update_cell(i+4, 2, str(proponent.discord.id))
    ws2.update_cell(i+4, 3, proponent.name)
    ws2.update_cell(i+4, 4, turns[i].passed)
    ws2.update_cell(i+4, 5, turns[i].end)
    for player in players:
        i = 8
        for stat in player.stats.values():
            ws1.cell(i, players.index(player)+2, stat)
            i += 1
    print("End Phase Save " + str(dt.datetime.now()))


def newPlayerSave(game, players, turns):
    ws3.update('B1',len(players))
    for player in players:
        i = players.index(player)
        ws1.update_cell(1, i+2, player.name)
        ws2.update_cell(3, i+6, player.name)
        ws1.update_cell(2, i+2, str(player.discord.id))
        ws1.update_cell(4, i+2, player.points)
        if player.currentVote.value is None:
            ws1.update_cell(5, i+2, None)
        else:
            ws1.update(5, i+2, str(player.currentVote.value) + ',' + str(player.currentVote.order))

    for i in range(game.globalTurn-1):
        j = 6
        for vote in turns[i].voteHistory:
            if vote.value is None:
                ws2.update_cell(i+4, j, None)
            else:
                ws2.update_cell(i+4, j, str(vote.value) + ',' + str(vote.order))
            j += 1
    for player in players:
        i = 8
        for stat in player.stats.values():
            ws1.cell(i, players.index(player)+2, stat)
            i += 1
    print("New Player Save " + str(dt.datetime.now()))