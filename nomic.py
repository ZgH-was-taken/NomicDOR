import discord
from discord.ext import commands
from discord.utils import get
intents = discord.Intents.default()
intents.members = True

import random as rnd
import asyncio
import datetime as dt
import math

from classes import *
from data import *

with open("token.txt", 'r') as f:
    token = f.readline()[:-1]
    botID = f.readline()

client = discord.Client()
bot = commands.Bot(command_prefix='~', case_insensitive = True, intents=intents)
bot.remove_command('help')



setup = False
@bot.event
async def on_ready():
    global setup
    if setup: return
    setup = True
    global nomicServer, botMember, botChannel, histBotChannel, updateChannel, votingChannel, playerRole
    #Commonly used channels and roles
    nomicServer = get(bot.guilds, name='NomicDOR')
    botMember = get(nomicServer.members, id=int(botID))

    botChannel = get(nomicServer.channels, name='bot-commands')
    histBotChannel = get(nomicServer.channels, name='historian-bot')
    updateChannel = get(nomicServer.channels, name='game-updates')
    votingChannel = get(nomicServer.channels, name='voting')

    playerRole = get(nomicServer.roles, name='Player')

    global game, players, turns, summaryMsg
    game, players, turns, summaryMsg = loadData(nomicServer)
    if summaryMsg:
        summaryMsg = await votingChannel.fetch_message(int(summaryMsg))

    if game.state == 1:
        global proposalTask
        proposalTask = asyncio.create_task(proposalTimeLimit(game.timerEnd))
    elif game.state == 2:
        await checkVotes(0)
        global voteTask
        voteTask = asyncio.create_task(votingTimeLimit(game.timerEnd))

    print("Bot is ready")



@bot.command()
async def save(ctx):
    if not ctx.channel == histBotChannel: return
    saveData(game, players, summaryMsg)



@bot.command()
async def join(ctx, username=None):
    global players
    if ctx.channel != botChannel: return
    await botChannel.send("{} has joined the game!".format(ctx.author.mention))
    await ctx.author.add_roles(playerRole)
    newPlayerObj = Player(ctx.author)
    if username is not None:
        newPlayerObj.name = username
    else: newPlayerObj.name = ctx.author.display_name
    for stat in newPlayerObj.stats:
        newPlayerObj.stats[stat] = 0
    if game.globalTurn == 1 and game.state == 0:
        players = players + [newPlayerObj]
    else:
        placement = rnd.randint(0,len(players)-1)
        if placement == 0 and rnd.randint(0,1) == 0:
            #The first and last position are equivalent, so there is a 50% chance of each
            placement = len(players)
        if placement <= game.turn and not (game.globalTurn == 1 and game.state == 0):
            game.turn += 1
        if placement == len(players): players = players + [newPlayerObj]
        else: players = players[:placement] + [newPlayerObj] + players[placement:]
        i = placement
        before = players[i-1].name
        if i == len(players)-1: i = -1
        after = players[i+1].name
        if len(players) > 2:
            await botChannel.send("You are player #{} in the turn order, between {} & {}".format(placement+1, before, after))
    
    newPlayerSave(game, players, turns)



@bot.command()
async def ready(ctx):
    global game
    if not (ctx.channel == botChannel and game.state == 0 and get(nomicServer.roles,name='Historian') in ctx.author.roles): return
    if game.globalTurn == 1:
        await randomize()
    #Begin the proposal phase
    game.state = 1
    #Give roles
    await updateChannel.send("Turn #{}! {}'s turn has begun, make a proposal using ~propose".format(game.globalTurn, players[game.turn-1].discord.mention))
    await players[game.turn-1].discord.add_roles(get(nomicServer.roles, name='Current Player'))
    await players[game.turn-1].discord.remove_roles(get(nomicServer.roles, name='Next Player'))
    nextTurn = game.turn + 1
    if nextTurn > len(players):
        nextTurn = 1
    await players[nextTurn-1].discord.add_roles(get(nomicServer.roles, name='Next Player'))
    await botMember.add_roles(get(nomicServer.roles, name='Game State: Proposing'))
    await botMember.remove_roles(get(nomicServer.roles, name='Game State: Waiting'))
    #Begin timer for proposing
    game.timerEnd = dt.datetime.now() + dt.timedelta(seconds = game.proposalTime)
    game.timerEnd.replace(microsecond=0)
    global proposalTask
    proposalTask = asyncio.create_task(proposalTimeLimit(game.timerEnd))
    endPhaseSave(game, players, turns)

async def randomize():
    rnd.shuffle(players)
    newPlayerSave(game,players,turns)
    resourcesChannel = get(nomicServer.channels, name='resources')
    turnOrder = 'Initial Turn Order:\n'
    for player in players:
        turnOrder += player.name + '\n'
    await resourcesChannel.send(turnOrder)




async def proposalTimeLimit(end):
    now = dt.datetime.now()
    if (end - now).total_seconds() > 3601:
        await asyncio.sleep((end - now).total_seconds() -3600)
        await votingChannel.send("{}, you have one hour left to propose".format(players[game.turn-1].discord.mention))
        await asyncio.sleep(3600)
        await updateChannel.send("A proposal was not made in time, waiting for the next turn")
    else:
        await asyncio.sleep((end - now).total_seconds())
        await updateChannel.send("A proposal was not made in time, waiting for the next turn")
    await endTurn(0, 3)

async def votingTimeLimit(end):
    global game
    now = dt.datetime.now()
    if (end - now).total_seconds() > 3601:
        await asyncio.sleep((end - now).total_seconds() -3600)
        toVoteRole = get(nomicServer.roles, name='To Vote')
        await votingChannel.send("{}, you have one hour left to vote".format(toVoteRole.mention))
        await asyncio.sleep(3600)
        await votingChannel.send("Voting time is up")
    else:
        await asyncio.sleep((end - now).total_seconds())
        await votingChannel.send("Voting time is up")
    game.lastVote = None
    await checkVotes(1)

@bot.command()
async def timeout(ctx):
    if not(get(nomicServer.roles, name='Historian') in ctx.author.roles and ctx.channel == botChannel): return
    if game.state == 1:
        await updateChannel.send("A proposal was not made in time, waiting for the next turn")
        global proposalTask
        proposalTask.cancel()
        await endTurn(0, 3)
    elif game.state == 2:
        await votingChannel.send("Voting time is up")
        game.lastVote = None
        global voteTask
        voteTask.cancel()
        await checkVotes(1)


#@bot.command(name='pass')
#async def passTurn(ctx):
#    global game
#    if not(ctx.author == players[game.turn-1].discord and ctx.channel == botChannel and game.state == 1): return
#    await updateChannel.send('The current turn has been passed, waiting for the next turn to start')
#    global proposalTask
#    proposalTask.cancel()
#    await endTurn(0,4)



@bot.command()
async def propose(ctx):
    global players, game
    game.transmute = 0
    if not (ctx.channel == votingChannel and game.state == 1 and (ctx.author == players[game.turn-1].discord or ctx.author == botMember)): return
    game.state = 2
    #FirstVote is whether or not the first vote has been made yet, lastVote is the index of the most recent vote
    game.firstVote = False
    game.lastVote = None
    toVoteRole = get(nomicServer.roles, name='To Vote')
    for player in players:
        player.currentVote = Vote(0, '', '', player)
        await player.discord.add_roles(toVoteRole)
    game.voteNumber = 0
    #End timer
    global proposalTask
    proposalTask.cancel()
    #Begin voting phase
    instPass = math.ceil(len(players)*game.yesProportion[0])
    instFail = math.ceil(len(players)*(1-game.yesProportion[0])+.0001)
    txt = "{} {}'s proposal is available to vote on!\nVote with ~yes or ~no\n{} yes votes will instantly pass the proposal, {} are required to fail it"
    txt = txt.format(playerRole.mention, players[game.turn-1].name, instPass, instFail)
    await votingChannel.send(txt)
    #Give roles
    await botMember.add_roles(get(nomicServer.roles, name='Game State: Voting'))
    await botMember.remove_roles(get(nomicServer.roles, name='Game State: Proposing'))
    #Begin voting timer
    global voteTask
    game.timerEnd = dt.datetime.now() + dt.timedelta(seconds = game.votingTime)
    game.timerEnd.replace(microsecond=0)
    voteTask = asyncio.create_task(votingTimeLimit(game.timerEnd))
    endPhaseSave(game, players, turns)

#@bot.command()
#async def transmute(ctx):
#    global players, game
#    game.transmute = 1
#    if not (ctx.channel == votingChannel and game.state == 1 and ctx.author == players[game.turn-1].discord): return
#    game.state = 2
#    #FirstVote is whether or not the first vote has been made yet, lastVote is the index of the most recent vote
#    game.firstVote = False
#    game.lastVote = None
#    toVoteRole = get(nomicServer.roles, name='To Vote')
#    for player in players:
#        player.currentVote = Vote(0, '', '', player)
#        await player.discord.add_roles(toVoteRole)
#    game.voteNumber = 0
#    #End timer
#    global proposalTask
#    proposalTask.cancel()
#    #Begin voting phase
#    instPass = math.ceil(len(players)*game.yesProportion[1])
#    instFail = math.ceil(len(players)*(1-game.yesProportion[1])+.0001)
#    txt = "{} {}'s proposal is available to vote on!\nVote with ~yes or ~no\n{} yes votes will instantly pass the proposal, {} are required to fail it"
#    txt = txt.format(playerRole.mention, players[game.turn-1].name, instPass, instFail)
#    await votingChannel.send(txt)
#    #Give roles
#    await botMember.add_roles(get(nomicServer.roles, name='Game State: Voting'))
#    await botMember.remove_roles(get(nomicServer.roles, name='Game State: Proposing'))
#    #Begin voting timer
#    global voteTask
#    game.timerEnd = dt.datetime.now() + dt.timedelta(seconds = game.votingTime)
#    game.timerEnd.replace(microsecond=0)
#    voteTask = asyncio.create_task(votingTimeLimit(game.timerEnd))
#    endPhaseSave(game, players, turns)

@bot.command()
async def toggleTransmute(ctx):
    global game
    if not (ctx.channel == votingChannel and game.state == 2 and (ctx.author == players[game.turn-1].discord) or get(nomicServer.roles,name='Historian') in ctx.author.roles): return
    if game.transmute == 0:
        instPass = math.ceil(len(players)*game.yesProportion[1])
        instFail = math.ceil(len(players)*(1-game.yesProportion[1])+.0001)
        txt = 'This proposal involves transmutation.\n{} yes votes will instantly pass the proposal, {} are required to fail it'
        await votingChannel.send(txt.format(instPass,instFail))
        game.transmute = 1
    else:
        instPass = math.ceil(len(players)*game.yesProportion[0])
        instFail = math.ceil(len(players)*(1-game.yesProportion[0])+.0001)
        txt = 'This proposal does not involve transmutation.\n{} yes votes will instantly pass the proposal, {} are required to fail it'
        await votingChannel.send(txt.format(instPass,instFail))
        game.transmute = 0



@bot.command()
async def yes(ctx):
    global players, game
    player = get(players, discord = ctx.author)
    if player is None: return
    if not (ctx.channel == votingChannel and game.state == 2): return
    if player.currentVote.value == 0:
        player.currentVote = Vote(1, game.voteNumber, dt.datetime.now(), player)
        game.voteNumber += 1
        player = get(players, discord=ctx.author)
        await votingChannel.send("{} has voted!".format(player.name))
        toVoteRole = get(nomicServer.roles, name='To Vote')
        await ctx.author.remove_roles(toVoteRole)
    else: await votingChannel.send("You've already voted")
    if players.index(player) != game.turn-1:
        if not game.firstVote:
            game.firstVote = True
            player.stats['firstVotes'] += 1
        game.lastVote = player
    await checkVotes(0)

@bot.command()
async def no(ctx):
    global players, game
    player = get(players, discord=ctx.author)
    if player is None: return
    if not (ctx.channel == votingChannel and game.state == 2): return
    if player.currentVote.value == 0:
        player.currentVote = Vote(2, game.voteNumber, dt.datetime.now(), player)
        game.voteNumber += 1
        await votingChannel.send("{} has voted!".format(player.name))
        toVoteRole = get(nomicServer.roles, name='To Vote')
        await ctx.author.remove_roles(toVoteRole)
    else: await votingChannel.send("You've already voted")
    if players.index(player) != game.turn-1:
        if not game.firstVote:
            game.firstVote = True
            player.stats['firstVotes'] += 1
        game.lastVote = player
    await checkVotes(0)



async def checkVotes(timeUp):
    global game
    allVotes = True
    yesses = 0
    nos = 0
    for player in players:
        if player.currentVote.value == 0:
            allVotes = False
        elif player.currentVote.value == 1: yesses += 1
        elif player.currentVote.value == 2: nos += 1
    if not timeUp:
        global summaryMsg
        if summaryMsg: await summaryMsg.delete()
        txt = 'Current votes for/against are {}/{}   ({}%/{}%)\n{}% of all players have voted yes, {}% of all players have voted no'
        txt = txt.format(yesses, nos, round(yesses*100/(yesses+nos),2), round(nos*100/(yesses+nos),2), round(yesses*100/len(players),2), round(nos*100/len(players),2))
        summaryMsg = await votingChannel.send(txt)

    #All votes have been cast
    if allVotes:
        if yesses/(yesses+nos) >= game.yesProportion[game.transmute] - 0.001:
            await updateChannel.send("All votes have been cast and the proposal has passed. Waiting for the next turn to start")
            await endTurn(1, 0)
        else:
            await updateChannel.send("All votes have been cast and the proposal has failed. Waiting for the next turn to start")
            await endTurn(0, 0)
        return
    #Time is up
    if timeUp:
        if yesses + nos == 0:
            await updateChannel.send("The proposal has failed as no votes were cast, waiting for the next turn to start")
            await endTurn(0, 2)
        elif yesses/(yesses+nos) >= game.timeoutProportion[game.transmute] - 0.001:
            await updateChannel.send("Voting time is up, and the proposal has passed. Waiting for the next turn to start")
            await endTurn(1, 2)
        else:
            await updateChannel.send("Voting time is up, and the proposal has failed. Waiting for the next turn to start")
            await endTurn(0, 2)
        return
    #Enough votes to determine a conclusion
    if yesses/len(players) >= game.yesProportion[game.transmute] - 0.001:
        await updateChannel.send("There are enough yes votes for the proposal to pass. Waiting for the next turn to start")
        await endTurn(1, 1)
    if nos/len(players) > (1-game.yesProportion[game.transmute]) + 0.001:
        await updateChannel.send("There are enough no votes for the proposal to fail. Waiting for the next turn to start")
        await endTurn(0, 1)

async def endTurn(success, endCondition):
    global players, game, summaryMsg
    game.state = 0
    game.timerEnd = None
    yesses = 0
    nos = 0
    for player in players:
        if player.currentVote.value == 1: yesses += 1
        elif player.currentVote.value == 2: nos += 1
    summaryMsg = None
    if endCondition < 3:
        txt = 'Final Votes: {}/{}   ({}%/{}%)   out of {} players'.format(yesses, nos, round(yesses*100/(yesses+nos),2), round(nos*100/(yesses+nos),2), len(players))
        await updateChannel.send(txt)
        await votingChannel.send('Voting is now over')

    if endCondition < 2:
        global voteTask
        voteTask.cancel()

    await endTurnRoles()
    
    if game.lastVote is not None:
        game.lastVote.stats['lastVotes'] += 1

    #Begin waiting phase
    turn = Turn(game.globalTurn)
    turn.proponent = players[game.turn-1]
    turn.passed = success
    turn.end = endCondition
    turn.voteHistory = []
    for player in players:
        turn.voteHistory.append(player.currentVote)
        player.currentVote = Vote(None, '', '', player)
    game.state = 0
    game.firstVote = False
    game.lastVote = None
    game.voteNumber = None
    turns.append(turn)
    
    game.turn += 1
    game.globalTurn += 1
    if game.turn > len(players):
        game.turn = 1

    endPhaseSave(game, players, turns)

async def endTurnRoles():
    toVoteRole = get(nomicServer.roles, name='To Vote')
    for player in players:
        await player.discord.remove_roles(toVoteRole)
    await players[game.turn-1].discord.remove_roles(get(nomicServer.roles, name='Current Player'))
    for player in players:
        await player.discord.remove_roles(toVoteRole)
    await botMember.add_roles(get(nomicServer.roles, name='Game State: Waiting'))
    await botMember.remove_roles(get(nomicServer.roles, name='Game State: Proposing'))
    await botMember.remove_roles(get(nomicServer.roles, name='Game State: Voting'))



@bot.event
async def on_message(ctx):
    await bot.change_presence(activity=None)
    if ctx.author in [x.discord for x in players]:
        player = get(players, discord = ctx.author)
        if player is None: return
        player.lastMessage = dt.datetime.now()
        try:
            if ctx.content[0] != '~':
                player.stats['messages'] += 1
        except IndexError:
            pass
    await bot.process_commands(ctx)


async def loop():
    while True:
        await asyncio.sleep(3600)
        saveData(game, players, summaryMsg)




bot.loop.create_task(loop())

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    raise error

bot.run(token)