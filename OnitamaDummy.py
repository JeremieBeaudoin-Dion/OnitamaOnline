from PodSixNet.Connection import ConnectionListener, connection
from time import sleep

class Game(ConnectionListener):
    '''
    The Game class handles flow control of the game and fps
    '''
    def __init__(self):
        # server variables
        self.gameid = None
        self.num = None  # my ID according to the server
        self.turn = False  # the players can act when it's their turn
        self.won = False
        self.lost = False

        # Game State
        self.state = "menu"

        self.host = "localhost"
        self.port = 8888

        # The game message to display -> informs the player of what the game is doing
        self.allert = "Card preferences (optionnal)"

        # Connects to a server game
        self.Connect((self.host, int(self.port)))

    def Network_startgame(self, data):
        print("Starting game number: " + str(data["gameid"]))

    def Network_connecting(self, data):
        print("Connected to server")

        self.Send({"action": "toqueue", "id": data["id"], "preferences": ["hello", "darkness", "my", "old", "friend"]})

    def update(self):
        # Connects to the server
        self.Pump()
        connection.Pump()

        sleep(0.1)


Game = Game()

while True:
    Game.update()