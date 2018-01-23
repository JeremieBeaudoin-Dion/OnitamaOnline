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
    def Network_gameQUIT(self, data):
        gameid = data["gameid"]
        num = data["num"]
        playerid = data["id"]

        self._server.leavingGame(gameid, num)
        self._server.kickPlayer(playerid)

    def Network_endturn(self, data):
        gameid = data["gameid"]
        num = data["num"]
        card = data["card"]
        board = data["board"]

        # send info to server
        self._server.nextturn(num, gameid, card, board)

    def Network_endgame(self, data):
        gameid = data["gameid"]
        num = data["num"]

        self._server.leavingGame(gameid, num)

    # InQueue
    def Network_toqueue(self, data):
        playerid = data["id"]
        preferences = data["preferences"]

        self._server.Queue(playerid, preferences)

    def Network_queueQUIT(self, data):
        playerid = data["id"]

        self._server.stopqueue()
        self._server.kickPlayer(playerid)

    # Leaves the server
    def Network_QUIT(self, data):
        playerid = data["id"]

        self._server.kickPlayer(playerid)


class Server(PodSixNet.Server.Server):  # classe du serveur comme tel

    def __init__(self, *args, **kwargs):
        # Server data
        PodSixNet.Server.Server.__init__(self, *args, **kwargs)
        self.versionNeeded = "0.3"  # The versions that can run the game
        self.games = []  # represent games
        self.player = dict()  # All players currently on the server
        self.queue = None  # represent if their is a queue currently
        self.currentIndex = 0  # current index of games
        self.currentPlayerID = 0

        self.pendingpreferences = []  # There is never more than one player in queue

    channelClass = ClientChannel

    def Connected(self, channel, addr):
        print 'new connection:', channel
        self.player.update({self.currentPlayerID: channel})
        self.player[self.currentPlayerID].Send({"action": "connecting", "id": self.currentPlayerID, "version": "0.3"})
        self.currentPlayerID += 1

    def kickPlayer(self, id):
        del self.player[id]

    def Queue(self, ID, preferences):
        # connect player to a new queue
        if self.queue is None:
            self.queue = Game(self.player[ID], self.currentIndex)  # Starts a new Game object
            self.pendingpreferences = preferences
        else:
            # Gets the correct info to start the game
            self.player[ID].gameid = self.currentIndex
            self.queue.player1 = self.player[ID]

            # Gets the cards of the game
            gamecard = Deck.startGame(preferences, self.pendingpreferences)

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
        # Makes sure that there is not many games with the same ID
        if len(game) == 1:
            game[0].nextturn(num, card, board)  # on part la fonction "next turn" dans game

    # Has left the game
    def leavingGame(self, gameid, num):
        for i in range(len(self.games)):
            if self.games[i].gameid == gameid:
                self.games[i].leaving(num)
                del self.games[i]
                break


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

        self.numberOfCardsInGame = 5

    def getCardDeckAccordingToPreferences(self, player2pref, player1pref):
        """
        Fills the desired cardDeck with cards from player's preferences

        :param gamecards: String[] -> the deck to fill
        :param player1pref: String[] -> the current prefered cards of player 1
        :param player2pref: String[] -> the current prefered cards of player 2
        """
        gamecards = []

        cardHelper = DeckBuilderHelper(player1pref, player2pref, self.cardnames)

        # Fill the gamecards
        for i in range(self.numberOfCardsInGame):

            nextcard = 0
            canaddnextcard = False

            while not canaddnextcard:
                nextcard = cardHelper.nextCard()

                if gamecards.count(nextcard) == 0:
                    canaddnextcard = True

            gamecards.append(nextcard)

        return gamecards

    def startGame(self, player2pref, player1pref):
        """
        Returns all the cards of the game

        :param player1pref: String[] -> the current prefered cards of player 1
        :param player2pref: String[] -> the current prefered cards of player 2

        :return: String[] gamecards -> all the cards of the game in order : player1, player2, hold
        """

        gamecards = self.getCardDeckAccordingToPreferences(player2pref, player1pref)

        # randomise the gamecard's order
        random.shuffle(gamecards)

        return gamecards


class DeckBuilderHelper:

    def __init__(self, player1pref, player2pref, allcardnames):
        self.possibleCardStack = list(allcardnames)

        self.player1pref = [x for x in player1pref if self.possibleCardStack.count(x) == 1]
        self.player2pref = [x for x in player2pref if self.possibleCardStack.count(x) == 1]

        self.nextplayertoserve = "player2"
        random.shuffle(self.possibleCardStack)

    def nextCard(self):

        nextcard = 0

        if (self.nextplayertoserve == "player2" or len(self.player1pref) <= 0) and len(self.player2pref) > 0:
            nextcard = self.player2pref.pop()
            self.nextplayertoserve = "player1"
        elif len(self.player1pref) > 0:
            nextcard = self.player1pref.pop()
            self.nextplayertoserve = "player2"

        if nextcard != 0 and self.possibleCardStack.count(nextcard) > 0:
            self.possibleCardStack.remove(nextcard)
        else:
            nextcard = self.possibleCardStack.pop()

        return nextcard


# stuff to run always here such as class/def
def main():
    pass

if __name__ == "__main__":
    # stuff only to run when not called via 'import' here
    print "STARTING SERVER ON LOCALHOST"
    address = raw_input("Host:Port (localhost:8888): ")
    if not address:
        host, port = "localhost", 8888
    else:
        host, port = address.split(":")

    # Objects
    Server = Server(localaddr=(host, int(port)))
    Deck = Deck()

    while True:
        Server.Pump()
        sleep(0.001)
