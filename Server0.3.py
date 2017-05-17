# coding=utf-8
import PodSixNet
from PodSixNet.Channel import Channel
import PodSixNet.Server
from time import sleep
import random


class ClientChannel(Channel):  # cette classe sert de pont entre le client et le serveur

    def Network(self, data):
        print data

    # InGAME

    def Network_inqueueQUIT(self, data):

        self._server.stopqueue()

    def Network_endturn(self, data):
        gameid = data["gameid"]
        num = data["num"]
        card = data["card"]
        board = data["board"]

        # send info to server
        self._server.nextturn(num, gameid, card, board)

    # Has left the game

    def Network_leaving(self, data):
        gameid = data["gameid"]
        num = data["num"]

        self._server.leaving(gameid, num)


class Server(PodSixNet.Server.Server):  # classe du serveur comme tel

    def __init__(self, *args, **kwargs):
        # Server data
        PodSixNet.Server.Server.__init__(self, *args, **kwargs)
        self.games = []  # represent games
        self.queue = None  # represent if their is a queue currently
        self.currentIndex = 0  # current index of games

    channelClass = ClientChannel

    def Connected(self, channel, addr):
        print 'new connection:', channel

        # connect player to a new queue
        if self.queue is None:
            self.queue = Game(channel, self.currentIndex)  # Starts a new Game object
        else:
            # Gets the correct info to start the game
            channel.gameid = self.currentIndex
            self.queue.player1 = channel

            # Gets the cards of the game
            gamecard = Deck.startGame()

            # Sends the info to the players // TODO: randomise player 0 and 1
            self.queue.player0.Send({"action": "startgame", "player": 0, "gameid": self.queue.gameid,
                                     "cards": gamecard})
            # Change gamecard for the other player
            for i in range(2):
                temp = gamecard[i]
                gamecard[i] = gamecard[i + 2]
                gamecard[i + 2] = temp
            self.queue.player1.Send({"action": "startgame", "player": 1, "gameid": self.queue.gameid,
                                     "cards": gamecard})

            # Start the game
            self.games.append(self.queue)
            self.queue = None
            self.currentIndex += 1

    # InQueue
    def stopqueue(self):

        self.queue = None

    # InGame
    def nextturn(self, num, gameid, card, board):
        # on trouve la game correspondante
        game = [a for a in self.games if a.gameid == gameid]
        if len(game) == 1:
            game[0].nextturn(num, card, board)  # on part la fonction "next turn" dans game

    # Has left the game
    def leaving(self, gameid, num):
        game = [a for a in self.games if a.gameid == gameid]
        if len(game) == 1:
            game[0].leaving(num)


class Game:
    def __init__(self, player0, currentIndex):
        self.turn = 0

        # initialises players
        self.player0 = player0
        self.player1 = None

        self.gameid = currentIndex

    def nextturn(self, num, card, board):
        if num == 1:
            self.player0.Send({"action": "nextturn", "card": card, "board": board})
        if num == 0:
            self.player1.Send({"action": "nextturn", "card": card, "board": board})

    def leaving(self, num):
        if num == 1:
            self.player0.Send({"action": "enemyleft"})
        if num == 0:
            self.player1.Send({"action": "enemyleft"})


class Deck:
    """
    Handles the game's info concerning cards and distrubutes them to start games
    """
    def __init__(self):
        # All cards in the game
        self.cardnames = ["frog", "eel", "goose", "horse", "rabbit", "cobra", "rooster", "ox",
                          "crane", "boar", "crab", "mantis", "elephant", "dragon", "tiger", "monkey"]

    def startGame(self):
        """
        Returns all the cards of the game in order
        :return: String[] gamecards -> all the cards of the game in order : player1, player2, hold
        """
        gamecards = []
        cardnumbers = []

        # Implement the number of cards to improve random
        for i in range(len(self.cardnames)):
            cardnumbers.append(i)

        # Every game has 5 cards
        for i in range(5):
            cardid = random.randint(0, len(cardnumbers)-1)
            gamecards.append(self.cardnames[cardnumbers[cardid]])
            # Every card must be chosen only once
            del cardnumbers[cardid]

        return gamecards


print "STARTING SERVER ON LOCALHOST"
address = raw_input("Host:Port (localhost:8888): ")
if not address:
    host, port = "localhost", 8888
    # host, port = "162.248.95.140", 8888
else:
    host, port = address.split(":")

# Objects
Server = Server(localaddr=(host, int(port)))
Deck = Deck()

while True:
    Server.Pump()
    sleep(0.01)
