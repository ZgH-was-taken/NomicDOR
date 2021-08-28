import datetime as dt

class Player(object):
    def __init__(self, discObj):
        self.discord = discObj
        self.name = None
        self.points = 0
        self.currentVote = Vote(None, None, self)
        statNames = ['messages','daysPlaying']
        self.stats = {i : 0 for i in statNames}
    def __repr__(self):
        return self.name
    def convert(self):
        if isinstance(self.points,str): self.points = int(self.points)
        for stat in self.stats:
            if isinstance(self.stats[stat],str): self.stats[stat] = int(self.stats[stat])

class Vote(object):
    def __init__(self, value, order, player):
        self.value = value
        self.order = order
        self.player = player
    def __repr__(self):
        if self.value == 0: return self.player.name + ' - No Vote'
        elif self.value == 1: return self.player.name + ' - #' + str(self.order) + ': Yes'
        elif self.value == 2: return self.player.name + ' - #' + str(self.order) + ': No'
        elif self.value == -2: return self.player.name + ' - Inactive'
        else: return self.player.name + ' - None'



class Turn(object):
    def __init__(self, turn):
        self.turnNumber = turn
        self.proponent = None
        self.passed = None
        self.end = None
        self.voteHistory = None
    def __repr__(self):
        return str(self.turnNumber) + ': ' + str(self.proponent.name)
    def convert(self):
        for var in ['passed', 'end']:
            value = getattr(self,var)
            if isinstance(value,str): setattr(self,var,int(value))



class Parameters(object):
    def __init__(self):
        self.turn = None
        self.globalTurn = None
        self.state = None
        self.proposalTime = None
        self.votingTime = None
        self.yesProportion = [None,None]     #Second number for transmutation
        self.timeoutProportion = [None,None]
        self.transmute = None
        self.timerEnd = None
    def __repr__(self):
        return 'Turn:' + str(self.globalTurn) + '  State:' + str(self.state)
    def convert(self):
        for var in ['turn', 'globalTurn', 'state', 'proposalTime', 'votingTime', 'transmute']:
            value = getattr(self,var)
            if isinstance(value,str): setattr(self,var,int(value))
        for var in ['yesProportion', 'timeoutProportion']:
            value = [getattr(self,var)[0],getattr(self,var)[1]]
            if isinstance(value[0],str): setattr(self,var,[float(value[0]),float(value[1])])
        if isinstance(self.timerEnd,str):
            self.timerEnd = dt.datetime.fromisoformat(self.timerEnd)




'''
player.currentVote [x,y]
x:
0 : Non-vote
1 : Yes
2 : No
-1 : Forfeit
-2 : Inactive player

y: Order of votes

Turn is the index of the current players turn, or the next player in the case where the game is between turns
It skips players who have left the game, and loops back to 0
globalTurn is the actual turn of the game. It only increments by 1

state
0 : The previous turn has ended, and the bot is waiting for historians to formalise the end of the turn and start the next
1 : The current player is writing a proposal to to be discussed and voted on
2 : A proposal has been made and players can vote for it


turn.end
0 : All votes
1 : Sufficient votes
2 : Out of voting time
3 : Out of proposal time
4 : Passed turn
'''