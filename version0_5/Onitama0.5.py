# coding=utf-8
from PodSixNet.Connection import ConnectionListener, connection
import pygame
import sys
import traceback
import logging


class Game(ConnectionListener):
    '''
    The Game class handles flow control of the game and fps
    '''
    def __init__(self):
        # Current version of the game
        self.version = 0.5

        self.FPS = 30

        # server variables
        self.gameid = None
        self.num = None  # my ID according to the server
        self.turn = False  # the players can act when it's their turn
        self.won = False
        self.lost = False

        # Game State
        self.state = "server"

        # host, port = "localhost", 8888

        self.host = "localhost"
        self.port = 8888
        # Connects to the server
        self.serverID = None  # The id to send to the server when connecting to game rooms
        self.findserver()

        self.allert = "Connecting to server..."

        # game variables
        self.clock = pygame.time.Clock()

    def findserver(self):
        # Connects to a server game
        self.Connect((self.host, int(self.port)))

    def quit(self):
        """
        Quits the game and makes sure the action is send to server
        """
        # Makes sure to send the right command to server
        if self.state == "inqueue":
            self.Send({"action": "queueQUIT", "id": self.serverID})
        elif self.state == "ingame":
            self.Send({"action": "gameQUIT", "gameid": self.gameid, "num": self.num, "id": self.serverID})
        else:
            self.Send({"action": "QUIT", "id": self.serverID})

        connection.Pump()
        self.Pump()
        pygame.quit()
        sys.exit(0)

    def Network_connecting(self, data):
        """
        Trying to connect to the server
        """
        self.serverID = data["id"]
        serverVersion = float(data["version"])

        if serverVersion > self.version:
            self.state = "refused"
            self.allert = "Your version is outdated. Please download the new one"
        else:
            # Get the player to the menu
            self.state = "menu"
            # The game message to display -> informs the player of what the game is doing
            self.allert = "Card preferences (optionnal)"

    def Network_startgame(self, data):
        """
        Instanciates all variables of the current game and starts the game
        """
        self.num = data["player"]
        self.gameid = data["gameid"]
        allcards = data["cards"]

        # Player number decides who starts the game
        if self.num == 0:
            self.turn = True
        else:
            self.turn = False

        # get the cards of the game -> the order is important
        Deck.hand.append(allcards[0])
        Deck.hand.append(allcards[1])
        Deck.enemy.append(allcards[2])
        Deck.enemy.append(allcards[3])
        Deck.hold.append(allcards[4])

        # Finally changes the game state
        self.state = "ingame"

    def Network_nextturn(self, data):
        '''
        The network notices that it is your turn
        '''
        # First change the enemies cards
        # Find the ID of the card that the enemy used
        cardchange = data["card"]
        cardid = 0
        for i in range(len(Deck.enemy)):
            if Deck.enemy[i] == cardchange:
                cardid = i
                break

        # Switch card in enemy's hand with hold
        temp = Deck.enemy[cardid]
        Deck.enemy[cardid] = Deck.hold[0]
        Deck.hold[0] = temp

        # Update current board
        Mapping.grid = data["board"]

        # Start your turn
        self.turn = True

        # Checks if the opponent won the game
        self.lost = Mapping.checkLoss()
        if self.lost:
            # Tells the player and changes the game state
            self.allert = "You lost. Click to go back to Menu."
            self.state = "tomenu"

    def Network_enemyleft(self, data):
        """
        The Network sends that the other player has left the game.
        """

        # Make sure you are still in a game
        if self.state == "ingame":

            # If an enemy leaves the game, you win the game.
            self.won = True
            self.lost = False

            # Informs the player
            self.allert = "The enemy has left the game. He so salty..."

            # Change game state
            self.state = "tomenu"

            # Closes the connection to the game
            self.Send({"action": "endgame", "gameid": self.gameid, "num": self.num})

    def Network_hello(self, data):
        HelloServer.server_hello()

    def say_hello(self):
        self.Send({"action": "hello", "hello": "server", "id": self.serverID})

    def endturn(self):
        """
        Finishes the turn and sends the action to the server
        """
        # Finish the turn
        self.turn = False

        # change the board to be send
        board = Mapping.changeBoard()

        # Send info to server -> the game info, the card used for the turn and the current board
        # That card is currently in Deck.hold instead of hand
        self.Send({"action": "endturn", "gameid": self.gameid, "num": self.num,
                   "card": Deck.hold[0], "board": board})
        self.Pump()
        connection.Pump()

        # You can only win at the end of a turn
        self.won = Mapping.checkWin()
        if self.won:
            # Sends to the server to close the current game
            self.Send({"action": "endgame", "gameid": self.gameid, "num": self.num})
            # Tells the player and changes the game state
            self.allert = "You won! Click to go back to Menu."
            self.state = "tomenu"

    def toMenu(self):
        """
        Changes game state and game variables to logg of to the menu
        """
        # Game variables
        self.won = False
        self.lost = False

        self.gameid = None
        self.num = None
        self.turn = False
        self.state = "menu"

        self.allert = "Card preferences (optionnal)"

        # Deletes all current cards in the hand
        Deck.clear()

        # Clears the board for next game
        Mapping.clearBoard()

    def toQueue(self):
        """
        Changes game state and game variables to connect to the queue
        """
        self.Send({"action": "toqueue", "id": self.serverID, "preferences": Deck.chosenCards})

        # What to display to inform the player
        self.allert = "Searching for player..."

        # Change the current game state
        self.state = "inqueue"

    def update(self):
        """
        Controls game flow
        """
        # Connects to the server
        self.Pump()
        connection.Pump()

        # Updates the display
        Display.update(self.state)

        # Get's player input
        Action.update()

        # Ensures connection with server
        HelloServer.update()

        # Ensures a 30 fps
        self.clock.tick_busy_loop(self.FPS)


class HelloServer():
    def __init__(self):
        self.time_between_hello = Game.FPS  # * 120
        self.max_wait_server_time = Game.FPS  # * 60

        self.time_since_last_hello = 0
        self.current_response_time = 0

        self.said_hello = False

    def update(self):
        if self.said_hello:
            self.current_response_time += 1

            if self.current_response_time > self.max_wait_server_time:
                # Game.quit()
                pass

        elif self.time_since_last_hello > self.time_between_hello:
            self.say_hello()

        else:
            self.time_since_last_hello += 1

    def server_hello(self):
        self.said_hello = False
        self.current_response_time = 0

    def say_hello(self):
        if not self.said_hello and self.time_since_last_hello > self.time_between_hello:
            self.time_since_last_hello = 0
            self.said_hello = True
            Game.say_hello()


class Action():
    """
    Handles player input
    """
    def __init__(self):
        # Mouse events. Checks if out of bounds before calling input
        self.isoutofbounds = True

    def update(self):
        """
        Checks the entry from the player
        """

        # Gets all events
        for event in pygame.event.get():
            # To quit the game
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    Game.quit()
            elif event.type == pygame.QUIT:
                Game.quit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                # Gets current mouse position
                mouse = pygame.mouse.get_pos()
                mousex = mouse[0]
                mousey = mouse[1]

                # Sends it to selector
                Selector.click(mousex, mousey)

            if event.type == pygame.VIDEORESIZE:
                width, height = event.size
                if width < 400:
                    width = 400
                if height < 400:
                    height = 400

                if width != height:
                    minvalue = min(width, height)
                    width = minvalue
                    height = minvalue

                Display.update_screen_size(width, height)


class Display():
    """
    Handles frame of the game and images
    """
    def __init__(self):
        # Window attribute
        pygame.init()

        infoObject = pygame.display.Info()
        windowX = infoObject.current_w
        windowY = infoObject.current_h
        self.init_width = 800
        self.init_height = 800

        self.dimWindowx = 1
        self.dimWindowy = 1

        self.width = self.init_width
        self.height = self.init_height

        if self.width > int(windowX) or self.height > int(windowY):
            self.dimWindowx = 0.6
            self.dimWindowy = 0.6
            self.width = 800 * self.dimWindow
            self.height = 800 * self.dimWindow

        if self.width > int(windowX) or self.height > int(windowY):
            self.dimWindowx = 0.6
            self.dimWindowy = 0.6
            self.width = 800 * self.dimWindowx
            self.height = 800 * self.dimWindowy

        # Instantiate all variables concerning colours and pixel positions
        self.set_coordonates_values()

        # Creates game Canvas
        screen = pygame.display.set_mode((int(self.width), int(self.height)), pygame.RESIZABLE)
        self.screen = screen

        # Sets up the display info
        pygame.display.set_caption("Onitama Online")
        # icon = pygame.image.load("Items/icon.png")
        # pygame.display.set_icon(icon)

        # Text font
        pygame.font.init()
        self.set_font()

    def update_screen_size(self, width, height):

        Display.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)

        self.width = width
        self.height = height

        self.dimWindowx = float(width) / float(self.init_width)
        self.dimWindowy = float(height) / float(self.init_height)

        self.set_font()

        self.set_coordonates_values()

    def set_font(self):
        self.fSizeIngame = int(18 * self.dimWindowx)
        self.fSizeInmenu = int(30 * self.dimWindowx)
        self.fSizeTitle = int(40 * self.dimWindowx)
        self.fSizeCurrent = int(30 * self.dimWindowx)

        self.fontTitle = pygame.font.Font("Font.ttf", self.fSizeTitle)
        self.fontBig = pygame.font.Font("Font.ttf", self.fSizeInmenu)
        self.fontSmall = pygame.font.Font("Font.ttf", self.fSizeIngame)

    def set_coordonates_values(self):
        """
        Creates all variables concerning display in pixels
        """
        # All game colours
        self.colourEnemy = (140, 0, 0)
        self.colourPlayer = (0, 0, 140)
        self.colourWhite = (255, 255, 255)
        self.colourBlack = (0, 0, 0)
        self.colourlightBlack = (60, 60, 60)
        self.colourGold = (255, 215, 0)
        self.colourOrange = (185, 126, 50)
        self.colourGrey = (140, 140, 140)
        self.colourDarkGrey = (100, 100, 100)
        self.colourDarkOrange = (165, 80, 0)

        # Card's choice colours
        self.colourGreen = (131, 143, 116)
        self.colourGreenDark = (74, 81, 66)
        self.colourRed = (153, 82, 72)
        self.colourRedDark = (112, 60, 53)
        self.colourBlue = (83, 122, 141)
        self.colourBlueDark = (57, 84, 96)

        # All game positions -> COOrdonates
        # Followed by their width and height -> DIMentions
        '''Game board'''
        self.dimSquares = [int(100 * self.dimWindowx), int(100 * self.dimWindowy)]
        self.cooBoard = [int(100 * self.dimWindowx), int(150 * self.dimWindowy)]
        self.dimSquaresinBoard = [5, 5]
        self.dimBoard = [int(100 * self.dimSquaresinBoard[0] * self.dimWindowx),
                         int(100 * self.dimSquaresinBoard[1] * self.dimWindowy)]

        self.dimYLines = [int(self.dimSquares[0] * self.dimSquaresinBoard[0] + 5 * self.dimWindowy),
                          int(5 * self.dimWindowy)]
        self.dimXLines = [self.dimYLines[1], self.dimYLines[0]]

        self.dimCircles = [int(self.dimSquares[0]/2)]
        self.dimPlayerCircles = [int(self.dimSquares[0]/2.5)]
        self.cooEnemyCircles = [int(self.cooBoard[0] + int(2.5 * self.dimSquares[0]) + self.dimXLines[0]/2),
                                int(self.cooBoard[1])]
        self.cooPlayerCircles = [self.cooEnemyCircles[0],
                                 int(self.cooBoard[1] + self.dimSquaresinBoard[1] * self.dimSquares[1])]

        '''Cards'''
        self.cooPlayerCard = [[int(125 * self.dimWindowx), int(700 * self.dimWindowy)],
                              [int(425 * self.dimWindowx), int(700 * self.dimWindowy)]]
        self.cooEnemyCard = [[int(125 * self.dimWindowx), int(50 * self.dimWindowy)],
                             [int(425 * self.dimWindowx), int(50 * self.dimWindowy)]]
        self.cooHoldCard = [[int(625 * self.dimWindowx), int(275 * self.dimWindowy)],
                            [int(625 * self.dimWindowx), int(475 * self.dimWindowy)]]
        self.dimCards = [int(150 * self.dimWindowx), int(70 * self.dimWindowy)]
        self.cooCardSeparation = [int(80 * self.dimWindowx)]
        self.dimSmallSquares = [int(12 * self.dimWindowx), int(12 * self.dimWindowy)]

        self.dimSmallXLines = [1, int(61 * self.dimWindowx)]
        self.dimSmallYLines = [int(61 * self.dimWindowy), 2]

        self.dimFlipCard = [int(60 * self.dimWindowx)]

        '''Menu buttons'''
        self.cooButtons = [int(100 * self.dimWindowx), int(self.width/2.6 + 10 * self.dimWindowy)]
        self.dimButtons = [int(135 * self.dimWindowx), int(50 * self.dimWindowy)]
        self.dimButtonSpace = [int(self.dimButtons[0] + 20 * self.dimWindowx),
                                   int(self.dimButtons[1] + 10 * self.dimWindowy)]
        self.dimButtonPlay = [int(140 * self.dimWindowx), int(60 * self.dimWindowy)]
        self.cooButtonPlay = [int(self.width/2 - self.dimButtonPlay[0]/2), int(self.height/6)]

    def blitCards(self):
        """
        Handles the display of the cards when in a game
        """
        # Player's cards
        # rect(Surface, color, (x, y, width, height), width=0)
        for i in range(len(Deck.hand)):
            # Position and background color of card
            posx = self.cooPlayerCard[i][0]
            posy = self.cooPlayerCard[i][1]
            maincolor = (255 * i, 255 * i, 255 * i)
            opositecolor = (255 - 255 * i, 255 - 255 * i, 255 - 255 * i)

            # Frame of the card
            pygame.draw.rect(self.screen, maincolor, (posx, posy, self.dimCards[0], self.dimCards[1]))

            # Name of the card
            text = self.fontSmall.render(Deck.hand[i], 1, opositecolor)
            self.screen.blit(text, (posx + (self.dimCards[0]/3 - len(Deck.hand[i])/2 * self.fSizeIngame/2),
                                    posy + self.dimCards[1]/3))

            # representation of the squares
            for y in range(5):
                for x in range(5):
                    color = (150, 150, 150)  # grey
                    if Deck.card[Deck.hand[i]][y][x] == 1:  # can move here
                        color = maincolor
                    elif Deck.card[Deck.hand[i]][y][x] == 2:  # player's place
                        color = (0, 0, 140)
                    pygame.draw.rect(self.screen, color, (posx + self.cooCardSeparation[0] + x * self.dimSmallSquares[0],
                                                          posy + self.dimXLines[0] + y * self.dimSmallSquares[1],
                                                          self.dimSmallSquares[0], self.dimSmallSquares[1]))

            # print the lines
            for j in range(6):
                # x lines
                pygame.draw.rect(self.screen, opositecolor, (posx + self.cooCardSeparation[0] + self.dimSmallSquares[0] * j,
                                                             posy + self.dimXLines[0],
                                                             self.dimSmallXLines[0], self.dimSmallXLines[1]))
                # y lines
                pygame.draw.rect(self.screen, opositecolor, (posx + self.cooCardSeparation[0],
                                                             posy + self.dimXLines[0] + self.dimSmallSquares[1] * j,
                                                             self.dimSmallYLines[0], self.dimSmallYLines[1]))

        # Enemy's cards -> they are flipped
        for i in range(len(Deck.enemy)):
            posx = self.cooEnemyCard[i][0]
            posy = self.cooEnemyCard[i][1]
            # The colors were reversed
            opositecolor = (255 * i, 255 * i, 255 * i)
            maincolor = (255 - 255 * i, 255 - 255 * i, 255 - 255 * i)

            # Frame of card
            pygame.draw.rect(self.screen, maincolor, (posx, posy, self.dimCards[0], self.dimCards[1]))

            # Name of the card
            text = self.fontSmall.render(Deck.enemy[i], 1, opositecolor)
            # 60 were added to the x position in order to flip it with the grid
            self.screen.blit(text, (posx + self.dimFlipCard[0] +
                                    (self.dimCards[0]/3.5 - len(Deck.hand[i])/2 * self.fSizeIngame/2),
                                    posy + self.dimCards[1]/3.5))

            # representation of the squares
            for y in range(5):
                for x in range(5):
                    color = (150, 150, 150)  # grey
                    if Deck.card[Deck.enemy[i]][4-y][4-x] == 1:  # can move here
                        color = maincolor
                    elif Deck.card[Deck.enemy[i]][4-y][4-x] == 2:  # enemy's place
                        color = (140, 0, 0)
                    pygame.draw.rect(self.screen, color, (posx + self.dimXLines[0] + x * self.dimSmallSquares[0],
                                                          posy + self.dimXLines[0] + y * self.dimSmallSquares[1]
                                                          , self.dimSmallSquares[0], self.dimSmallSquares[1]))

            # print the lines
            for j in range(6):
                # x lines
                pygame.draw.rect(self.screen, opositecolor, (posx + self.dimXLines[0] + self.dimSmallSquares[0] * j,
                                                             posy + self.dimXLines[0],
                                                             self.dimSmallXLines[0], self.dimSmallXLines[1]))
                # y lines
                pygame.draw.rect(self.screen, opositecolor, (posx + self.dimXLines[0],
                                                             posy + self.dimXLines[0] + self.dimSmallSquares[1] * j,
                                                             self.dimSmallYLines[0], self.dimSmallYLines[1]))

        # The middle card
        for i in range(len(Deck.hold)):
            # Position and background color of card
            posx = self.cooHoldCard[1][0]
            posy = self.cooHoldCard[1][1]
            if not Game.turn:
                posx = self.cooHoldCard[0][0]
                posy = self.cooHoldCard[0][1]
            maincolor = self.colourGold
            opositecolor = (0, 0, 0)

            # Frame of the card
            pygame.draw.rect(self.screen, maincolor, (posx, posy, self.dimCards[0], self.dimCards[1]))

            # Name of the card
            text = self.fontSmall.render(Deck.hold[i], 1, opositecolor)
            if Game.turn:
                self.screen.blit(text, (posx + (self.dimCards[0]/3.5 - len(Deck.hand[i])/2 * self.fSizeIngame/2),
                                        posy + self.dimCards[1]/3.5))
            else:
                self.screen.blit(text, (posx + self.dimFlipCard[0] +
                                        (self.dimCards[0]/3.5 - len(Deck.hand[i])/2 * self.fSizeIngame/2),
                                        posy + self.dimCards[1]/3.5))

            if Game.turn:
                # representation of the squares
                for y in range(5):
                    for x in range(5):
                        color = (150, 150, 150)  # grey
                        if Deck.card[Deck.hold[i]][y][x] == 1:  # can move here
                            color = maincolor
                        elif Deck.card[Deck.hold[i]][y][x] == 2:  # player's place
                            color = (0, 0, 140)
                        pygame.draw.rect(self.screen, color, (posx + self.cooCardSeparation[0] +
                                                              x * self.dimSmallSquares[0],
                                                              posy + self.dimXLines[0] + y * self.dimSmallSquares[1],
                                                              self.dimSmallSquares[0], self.dimSmallSquares[1]))

                # print the lines
                for j in range(6):
                    # x lines
                    pygame.draw.rect(self.screen, opositecolor, (posx + self.cooCardSeparation[0] +
                                                                 self.dimSmallSquares[0] * j,
                                                                 posy + self.dimXLines[0],
                                                                 self.dimSmallXLines[0], self.dimSmallXLines[1]))
                    # y lines
                    pygame.draw.rect(self.screen, opositecolor, (posx + self.cooCardSeparation[0],
                                                                 posy + self.dimXLines[0] + self.dimSmallSquares[1] * j,
                                                                 self.dimSmallYLines[0], self.dimSmallYLines[1]))
            else:
                # representation of the squares
                for y in range(5):
                    for x in range(5):
                        color = (150, 150, 150)  # grey
                        if Deck.card[Deck.hold[i]][4-y][4-x] == 1:  # can move here
                            color = maincolor
                        elif Deck.card[Deck.hold[i]][4-y][4-x] == 2:  # enemy's place
                            color = (140, 0, 0)
                        pygame.draw.rect(self.screen, color, (posx + self.dimXLines[0] + x * self.dimSmallSquares[0],
                                                              posy + self.dimXLines[0] + y * self.dimSmallSquares[1]
                                                              , self.dimSmallSquares[0], self.dimSmallSquares[1]))

                # print the lines
                for j in range(6):
                    # x lines
                    pygame.draw.rect(self.screen, opositecolor, (posx + self.dimXLines[0] + self.dimSmallSquares[0] * j,
                                                                 posy + self.dimXLines[0],
                                                                 self.dimSmallXLines[0], self.dimSmallXLines[1]))
                    # y lines
                    pygame.draw.rect(self.screen, opositecolor, (posx + self.dimXLines[0],
                                                                 posy + self.dimXLines[0] + self.dimSmallSquares[1] * j,
                                                                 self.dimSmallYLines[0], self.dimSmallYLines[1]))

    def blitGame(self):
        """
        send all images of the game to the display for double buffer
        """

        # Add all cards
        # This section is quite long, it has been implemented in a method
        self.blitCards()

        # Draws the board game
        # It has a 5x5 board consisting of lines and squares

        # Two gold circles to represent the throne
        mythronecolor = self.colourPlayer
        enemythronecolor = self.colourEnemy
        # the player's turns are represented by their throne. If the color is theirs, it's their turn
        if Game.turn:
            mythronecolor = self.colourGold
        else:
            enemythronecolor = self.colourGold

        # circle(Surface, color, pos, radius, width=0)
        pygame.draw.circle(self.screen, enemythronecolor, (self.cooEnemyCircles[0], self.cooEnemyCircles[1]),
                           self.dimCircles[0])
        pygame.draw.circle(self.screen, mythronecolor, (self.cooPlayerCircles[0], self.cooPlayerCircles[1]),
                           self.dimCircles[0])

        # filling the squares
        # rect(Surface, color, Rect, width=0) -> Rect
        for y in range(5):
            for x in range(5):
                # Add all squares
                squarecolor = self.colourGrey
                if Selector.movespaces[y][x] == 1:
                    squarecolor = self.colourlightBlack
                elif Selector.movespaces[y][x] > 1:
                    squarecolor = self.colourWhite

                # Prints the single square
                pygame.draw.rect(self.screen, squarecolor, (self.cooBoard[0] + self.dimSquares[0] * x,
                                                            self.cooBoard[1] + self.dimSquares[1] * y,
                                                            self.dimSquares[0], self.dimSquares[1]))

                # If the case is shared by 2 cards, add a triangle to represent the second card
                if Selector.movespaces[y][x] == 3:
                    pygame.draw.polygon(self.screen, self.colourlightBlack,
                                        [(self.cooBoard[0] + self.dimSquares[0] * x,
                                          self.cooBoard[1] + self.dimSquares[1] * y),
                                         (self.cooBoard[0] + self.dimSquares[0] * x + self.dimSquares[0],
                                          self.cooBoard[1] + self.dimSquares[1] * y),
                                         (self.cooBoard[0] + self.dimSquares[0] * x,
                                          self.cooBoard[1] + self.dimSquares[1] * y + self.dimSquares[1])])

                # Adding all pieces
                color = 140
                # Changing color if unit is selected
                if Selector.unitselected is not None:
                    if Selector.unitselected[0] == x and Selector.unitselected[1] == y:
                        color = 255

                if Mapping.grid[y][x] == 10:
                    # Blue normal piece for player
                    # (start of grid + width of squares * x + position + adjust because of lines, idem for y)
                    pygame.draw.rect(self.screen, (0, 0, color), (self.cooBoard[0] + self.dimSquares[0] * x
                                                                  + self.dimSquares[0]/4 + self.dimXLines[0]/2,
                                                                  self.cooBoard[1] + self.dimSquares[0] * y
                                                                  + self.dimSquares[1]/4 + self.dimYLines[1]/2,
                                                                  self.dimSquares[0]/2, self.dimSquares[1]/2))
                elif Mapping.grid[y][x] == 20:
                    # Red normal piece for enemy
                    pygame.draw.rect(self.screen, (color, 0, 0), (self.cooBoard[0] + self.dimSquares[0] * x
                                                                  + self.dimSquares[0]/4 + self.dimXLines[0]/2,
                                                                  self.cooBoard[1] + self.dimSquares[0] * y
                                                                  + self.dimSquares[1]/4 + self.dimYLines[1]/2,
                                                                  self.dimSquares[0]/2, self.dimSquares[1]/2))
                elif Mapping.grid[y][x] == 11:
                    # Blue king for player
                    pygame.draw.circle(self.screen, (0, 0, color), (self.cooBoard[0] + self.dimSquares[0] * x
                                                                  + self.dimSquares[0]/2 + self.dimXLines[0]/2,
                                                                  self.cooBoard[1] + self.dimSquares[0] * y
                                                                  + self.dimSquares[1]/2 + self.dimYLines[1]/2),
                                                                    self.dimPlayerCircles[0])
                elif Mapping.grid[y][x] == 22:
                    # Red king for enemy
                    pygame.draw.circle(self.screen, (color, 0, 0), (self.cooBoard[0] + self.dimSquares[0] * x
                                                                  + self.dimSquares[0]/2 + self.dimXLines[0]/2,
                                                                  self.cooBoard[1] + self.dimSquares[0] * y
                                                                  + self.dimSquares[1]/2 + self.dimYLines[1]/2),
                                                                    self.dimPlayerCircles[0])

        # All the black lines, seperating the squares
        for i in range(6):
            # x lines
            pygame.draw.rect(self.screen, 0, (self.cooBoard[0] + self.dimSquares[0] * i, self.cooBoard[1],
                                              self.dimXLines[0], self.dimXLines[1]))
            # y lines
            pygame.draw.rect(self.screen, 0, (self.cooBoard[0], self.cooBoard[1] + self.dimSquares[1] * i,
                                              self.dimYLines[0], self.dimYLines[1]))

    def blitChoice(self):
        """
        In Menus, display different buttons
        """
        # Play button
        pygame.draw.rect(self.screen, self.colourPlayer, (self.cooButtonPlay[0], self.cooButtonPlay[1],
                                                          self.dimButtonPlay[0], self.dimButtonPlay[1]))

        text = self.fontBig.render("Play!", 1, self.colourWhite)
        self.screen.blit(text, (self.cooButtonPlay[0] + self.dimButtonPlay[0]/2 - len("Play!")/2 * self.fSizeInmenu/2,
                                self.cooButtonPlay[1] + self.dimButtonPlay[1]/6))

        # Preference of cards
        counterx = 0
        countery = 0

        counterx, countery = self.blit_all_menu_card(Deck.card_green, self.colourGreen, counterx, countery)
        counterx, countery = self.blit_all_menu_card(Deck.card_blue, self.colourBlue, counterx, countery)
        counterx, countery = self.blit_all_menu_card(Deck.card_red, self.colourRed, counterx, countery)
        counterx, countery = self.blit_all_menu_card(Deck.extension_card_green, self.colourGreenDark, counterx, countery)
        counterx, countery = self.blit_all_menu_card(Deck.extension_card_blue, self.colourBlueDark, counterx, countery)
        counterx, countery = self.blit_all_menu_card(Deck.extension_card_red, self.colourRedDark, counterx, countery)

    def blit_all_menu_card(self, deck, colour, counterx, countery):

        for name in deck:
            card_colour = colour

            for card in Deck.chosenCards:
                if name == card:
                    card_colour = self.colourWhite
                    break

            self.blit_menu_card(card_colour, name, counterx, countery)

            counterx += 1
            if counterx >= 4:
                countery += 1
                counterx %= 4

        return counterx, countery

    def blit_menu_card(self, colour, name, counterx, countery):
        # Draws the backgound of the card
        pygame.draw.rect(self.screen, colour, (self.cooButtons[0] + self.dimButtonSpace[0] * counterx,
                                                        self.cooButtons[1] + self.dimButtonSpace[1] * countery,
                                                        self.dimButtons[0], self.dimButtons[1]))

        # Writes the text of the card
        text = self.fontSmall.render(name, 1, self.colourBlack)
        self.screen.blit(text, (self.cooButtons[0] + self.dimButtonSpace[0] * counterx +
                                self.dimButtons[0]/2 - len(name)/2 * self.fSizeIngame/2,
                                self.cooButtons[1] + self.dimButtonSpace[1] * countery + self.dimButtons[1]/4))

    def update(self, state):
        """
        Updates the display depending on the game state
        """

        # Clears the screen and fills it with a colour
        backcolour = self.colourOrange
        # if you lost, fill it with red
        if Game.lost:
            backcolour = self.colourEnemy
        # if you won, fill it with blue
        if Game.won:
            backcolour = self.colourPlayer

        self.screen.fill(backcolour)

        # Displays the game depending on the state
        if state == "ingame":
            self.blitGame()
        elif state == "menu":
            text1 = self.fontTitle.render("Onitama Online", 1, self.colourBlack)
            self.screen.blit(text1, (self.width/2 - len("Onitama Online")/2 * self.fSizeTitle/2,
                                     int(self.dimSquares[0]/1.5)))

            text2 = self.fontBig.render(Game.allert, 1, self.colourBlack)
            self.screen.blit(text2, (self.width/2 - len(Game.allert)/2 * self.fSizeInmenu/2,
                                     int(self.height/3)))

            self.blitChoice()
        else:
            # inqueue or tomenu
            text = self.fontBig.render(Game.allert, 1, self.colourBlack)
            self.screen.blit(text, (self.width/2 - len(Game.allert)/2 * self.fSizeInmenu/2,
                                    self.height/2 + 50))

        # Updates the display
        pygame.display.flip()


class Mapping():
    """
    Handles pieces and their positions. It is useless to create classes for the pieces
    so Mapping takes charge of that
    """
    def __init__(self):
        # The Grid is the representation of the game.
        # 0 is empty
        # 10 is a player's piece, 11 is the player's king
        # 20 is an enemy's piece, 22 is the enemy's king
        self.grid = []
        for y in range(5):
            line = []
            for x in range(5):
                # Fill in enemy's pieces
                if y == 0:
                    if x == 2:
                        line.append(22)
                    else:
                        line.append(20)
                # Player's pieces
                elif y == 4:
                    if x == 2:
                        line.append(11)
                    else:
                        line.append(10)
                else:
                    line.append(0)
            # Adds the current line to the grid
            self.grid.append(line)

    def clearBoard(self):
        """
        Empties the current board and sets it up for next game
        """
        self.grid = []
        for y in range(5):
            line = []
            for x in range(5):
                # Fill in enemy's pieces
                if y == 0:
                    if x == 2:
                        line.append(22)
                    else:
                        line.append(20)
                # Player's pieces
                elif y == 4:
                    if x == 2:
                        line.append(11)
                    else:
                        line.append(10)
                else:
                    line.append(0)
            # Adds the current line to the grid
            self.grid.append(line)

    def changepiece(self, oldx, oldy, newx, newy):
        """
        Change a piece's position on the board

        :param oldx: the old piece x position in grid (0 to 5)
        :param oldy: the old piece y position (0 to 5)
        :param newx: the new piece x position (0 to 5)
        :param newy: the new piece y position (0 to 5)
        """
        # Checks the current piece to change and stores it
        piece = Mapping.grid[oldy][oldx]
        Mapping.grid[oldy][oldx] = 0

        # Puts the piece in the new position
        Mapping.grid[newy][newx] = piece

    def changeBoard(self):
        """
        Changes the board to send to opponent
        :return: tempgrid -> a representation of the grid, adapted to the enemy
        """
        tempgrid = [[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0]]
        # Switch the ID of the pieces and flip the y coordonate
        for y in range(5):
            for x in range(5):
                if self.grid[y][x] == 22:
                    tempgrid[4 - y][4 - x] = 11
                elif self.grid[y][x] == 20:
                    tempgrid[4 - y][4 - x] = 10
                elif self.grid[y][x] == 11:
                    tempgrid[4 - y][4 - x] = 22
                elif self.grid[y][x] == 10:
                    tempgrid[4 - y][4 - x] = 20

        return tempgrid

    def checkWin(self):
        """
        Checks the lost conditions to end the game

        :return: Boolean
        """
        # if your king has entered the throne
        if self.grid[0][2] == 11:
            return True

        # if the enemy's king is dead
        # Though it could have been argued that checkWin be done in another function to simplify this for loop,
        # I prefer this way, just to make sure the game didn't miss it
        for y in range(5):
            for x in range(5):
                if self.grid[y][x] == 22:
                    return False

        return True

    def checkLoss(self):
        """
        Checks the lost conditions to end the game

        :return: Boolean
        """
        # Much of the same as checkWin
        if Mapping.grid[4][2] == 22:
            return True

        # TODO: Add a "you can't do anything"

        # if the enemy's king is dead
        # Though it could have been argued that checkWin be done in another function to simplify this for loop,
        # I prefer this way, just to make sure the game didn't miss it
        for y in range(5):
            for x in range(5):
                if Mapping.grid[y][x] == 11:
                    return False

        return True


class Selector():
    """
    Handles clicks on the board and sends the corresponding action to Mapping
    """
    def __init__(self):
        self.unitselected = None
        self.movespaces = [[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0]]

    def click_ingame(self, mousex, mousey):
        """
        Checks for the action of the mouse in Game
        :param mousex: X position of mouse
        :param mousey: Y position of mouse
        """
        # We need both int and float type to see if the top half of a square is selected
        posx = mousex
        posy = mousey
        x = int((mousex - Display.cooBoard[0]) / Display.dimSquares[0])
        y = int((mousey - Display.cooBoard[1]) / Display.dimSquares[1])

        # Checks if the position of the cursor is within bounds of the board
        if 0 <= x <= 4 and 0 <= y <= 4:
            # Selects a unit
            if Mapping.grid[y][x] in (10, 11):
                # If you click on a selected unit, it deselects it
                if self.unitselected is not None:
                    if self.unitselected[0] == x and self.unitselected[1] == y:
                        self.unitselected = None
                        self.movespaces = [[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0]]
                    else:
                        self.unitselected = [x, y]
                        self.movespaces = Deck.cardspace(x, y)
                else:
                    self.unitselected = [x, y]
                    self.movespaces = Deck.cardspace(x, y)

            # Finishes the turn and sends the command to the unit
            elif self.unitselected is not None:
                if self.movespaces[y][x] != 0:
                    # Moves the unit
                    Mapping.changepiece(self.unitselected[0], self.unitselected[1], x, y)

                    # Chose the card and modify it
                    cardid = 0
                    if self.movespaces[y][x] != 3:
                        # The card is indicated in the number of movespaces. 1 = 0 and 2 = 1
                        cardid = self.movespaces[y][x] - 1
                    else:
                        # The square is represented by both cards. The player must chose the card with the cursor
                        # The square is put back in space 0,0 and we see if the cursor is above the triangular line
                        if posy - y * 100 - 150 < 100 - (posx - x * 100 - 100):
                            cardid = 0
                        else:
                            cardid = 1

                    # Switch card in hand with hold
                    temp = Deck.hand[cardid]
                    Deck.hand[cardid] = Deck.hold[0]
                    Deck.hold[0] = temp

                    # Change the turn
                    self.unitselected = None
                    Game.endturn()
                    self.movespaces = [[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0]]

    def click_inmenu(self, mousex, mousey):
        """
        Checks for the action of the mouse in Menus
        :param mousex: X position of mouse
        :param mousey: Y position of mouse
        """
        posx = mousex
        posy = mousey

        # Checks for play button
        if Display.cooButtonPlay[0] < posx < Display.cooButtonPlay[0] + Display.dimButtonPlay[0] and \
            Display.cooButtonPlay[1] < posy < Display.cooButtonPlay[1] + Display.dimButtonPlay[1]:
            Game.toQueue()
            # Ignores unnecessary checking
            return

        # Checks for click on preference button
        counterx = 0
        countery = 0

        all_cards_in_order = Deck.card_green + Deck.card_blue + Deck.card_red + Deck.extension_card_green + \
            Deck.extension_card_blue + Deck.extension_card_red

        for card in all_cards_in_order:
            if Display.cooButtons[0] + Display.dimButtonSpace[0] * counterx < posx \
                    < Display.cooButtons[0] + Display.dimButtonSpace[0] * counterx + Display.dimButtons[0] and \
                Display.cooButtons[1] + Display.dimButtonSpace[1] * countery < posy \
                    < Display.cooButtons[1] + Display.dimButtonSpace[1] * countery + Display.dimButtons[1]:

                Deck.preferences(card)
                return

            counterx += 1
            if counterx >= 4:
                countery += 1
                counterx %= 4

    def click(self, mousex, mousey):
        """
        Handles all click for different game states.

        :param mousex: the x pixel position of the mouse
        :param mousey: the y pixel position of the mouse
        """
        if Game.state == "ingame":
            if Game.turn:
                self.click_ingame(mousex, mousey)
        elif Game.state == "tomenu":
            Game.toMenu()
        elif Game.state == "menu":
            self.click_inmenu(mousex, mousey)


class Deck():
    """
    All the cards on board
    """
    def __init__(self):
        # All cards of the game // 1 is a space in which you can go, 2 is the piece's space
        self.card = {"crane":       [[0,0,0,0,0],[0,0,1,0,0],[0,0,2,0,0],[0,1,0,1,0],[0,0,0,0,0]],
                     "elephant":    [[0,0,0,0,0],[0,1,0,1,0],[0,1,2,1,0],[0,0,0,0,0],[0,0,0,0,0]],
                     "boar":        [[0,0,0,0,0],[0,0,1,0,0],[0,1,2,1,0],[0,0,0,0,0],[0,0,0,0,0]],
                     "dragon":      [[0,0,0,0,0],[1,0,0,0,1],[0,0,2,0,0],[0,1,0,1,0],[0,0,0,0,0]],

                     "crab":        [[0,0,0,0,0],[0,0,1,0,0],[1,0,2,0,1],[0,0,0,0,0],[0,0,0,0,0]],
                     "tiger":       [[0,0,1,0,0],[0,0,0,0,0],[0,0,2,0,0],[0,0,1,0,0],[0,0,0,0,0]],
                     "mantis":      [[0,0,0,0,0],[0,1,0,1,0],[0,0,2,0,0],[0,0,1,0,0],[0,0,0,0,0]],
                     "monkey":      [[0,0,0,0,0],[0,1,0,1,0],[0,0,2,0,0],[0,1,0,1,0],[0,0,0,0,0]],

                     "frog":        [[0,0,0,0,0],[0,1,0,0,0],[1,0,2,0,0],[0,0,0,1,0],[0,0,0,0,0]],
                     "eel":         [[0,0,0,0,0],[0,1,0,0,0],[0,0,2,1,0],[0,1,0,0,0],[0,0,0,0,0]],
                     "goose":       [[0,0,0,0,0],[0,1,0,0,0],[0,1,2,1,0],[0,0,0,1,0],[0,0,0,0,0]],
                     "horse":       [[0,0,0,0,0],[0,0,1,0,0],[0,1,2,0,0],[0,0,1,0,0],[0,0,0,0,0]],

                     "rabbit":      [[0,0,0,0,0],[0,0,0,1,0],[0,0,2,0,1],[0,1,0,0,0],[0,0,0,0,0]],
                     "cobra":       [[0,0,0,0,0],[0,0,0,1,0],[0,1,2,0,0],[0,0,0,1,0],[0,0,0,0,0]],
                     "rooster":     [[0,0,0,0,0],[0,0,0,1,0],[0,1,2,1,0],[0,1,0,0,0],[0,0,0,0,0]],
                     "ox":          [[0,0,0,0,0],[0,0,1,0,0],[0,0,2,1,0],[0,0,1,0,0],[0,0,0,0,0]],

                     "panda":       [[0,0,0,0,0],[0,0,1,1,0],[0,0,2,0,0],[0,1,0,0,0],[0,0,0,0,0]],
                     "mouse":       [[0,0,0,0,0],[0,0,1,0,0],[0,0,2,0,0],[0,0,0,1,0],[0,1,0,0,0]],
                     "sable":       [[0,0,0,0,0],[0,0,0,1,0],[1,0,2,0,0],[0,1,0,0,0],[0,0,0,0,0]],
                     "fox":         [[0,0,0,0,0],[0,0,0,1,0],[0,0,2,1,0],[0,0,0,1,0],[0,0,0,0,0]],
                     "sea snake":   [[0,0,0,0,0],[0,0,1,0,0],[0,0,2,0,1],[0,1,0,0,0],[0,0,0,0,0]],
                     "tanuki":      [[0,0,0,0,0],[0,0,1,0,0],[0,0,2,1,0],[0,0,1,0,0],[0,0,0,0,0]],

                     "iguana":      [[0,0,0,0,0],[1,0,1,0,0],[0,0,2,0,0],[0,0,0,1,0],[0,0,0,0,0]],
                     "bear":        [[0,0,0,0,0],[0,1,1,0,0],[0,0,2,0,0],[0,0,0,1,0],[0,0,0,0,0]],
                     "rat":         [[0,0,0,0,0],[0,0,1,0,0],[0,1,2,0,0],[0,0,0,1,0],[0,0,0,0,0]],
                     "viper":       [[0,0,0,0,0],[1,0,1,0,0],[0,0,2,1,0],[0,0,0,1,0],[0,0,0,0,0]],
                     "dog":         [[0,0,0,0,0],[0,1,0,0,0],[0,1,2,0,0],[0,1,0,0,0],[0,0,0,0,0]],
                     "otter":       [[0,0,0,0,0],[0,1,0,0,0],[0,0,2,0,1],[0,0,0,1,0],[0,0,0,0,0]],

                     "turtle":      [[0,0,0,0,0],[0,0,0,0,0],[1,0,2,0,1],[0,1,0,1,0],[0,0,0,0,0]],
                     "giraffe":     [[0,0,0,0,0],[1,0,0,0,1],[0,0,2,0,0],[0,0,1,0,0],[0,0,0,0,0]],
                     "phoenix":     [[0,0,0,0,0],[0,1,0,1,0],[1,0,2,0,1],[0,0,0,0,0],[0,0,0,0,0]],
                     "kirin":       [[0,1,0,1,0],[0,0,0,0,0],[0,0,2,0,0],[0,0,0,0,0],[0,0,1,0,0]]}

        self.card_green = ["crane", "elephant", "boar", "dragon", "crab", "tiger", "mantis", "monkey"]
        self.card_blue = ["frog", "eel", "goose", "horse"]
        self.card_red = ["rabbit", "cobra", "rooster", "ox"]

        self.extension_card_green = ["turtle", "giraffe", "phoenix", "kirin"]
        self.extension_card_blue = ["iguana", "bear", "rat", "viper", "dog", "otter"]
        self.extension_card_red = ["panda", "mouse", "sable", "fox", "sea snake", "tanuki"]

        self.hand = []
        self.enemy = []
        self.hold = []

        self.chosenCards = []

    def clear(self):
        """
        Clears the hand of the player, the enemy's and the hold card
        """
        self.hand = []
        self.enemy = []
        self.hold = []

    def preferences(self, key):
        """
        Changes preference of the game. If the preferences are more than 4, ignore the click
        :param key: The card's name (String)
        """

        # If the card is already selected, deselect it
        for i in reversed(range(len(self.chosenCards))):
            if self.chosenCards[i] == key:
                del self.chosenCards[i]
                return

        # Else, add it to prefered cards
        self.chosenCards.append(key)

    def cardspace(self, posx, posy):
        """
        Checks if the spaces are available to move with a card

        :return: moveid -> a representation of the board with 1, 2 or 3 if the piece can move there
        """
        moveid = [[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0]]

        for i in range(len(self.hand)):
            for myy in range(-2, 3):
                for myx in range(-2, 3):
                    if not (myy == 0 and myx == 0) and 0 <= posy + myy <= 4 and 0 <= posx + myx <= 4:
                        moveid[posy + myy][posx + myx] += self.card[self.hand[i]][2 + myy][2 + myx] * (i + 1)

        return moveid


Display = Display()
Action = Action()
Game = Game()
Mapping = Mapping()
Selector = Selector()
Deck = Deck()
HelloServer = HelloServer()

while True:
    try:
        Game.update()
    except Exception as e:
        logging.error(traceback.format_exc())
        Game.quit()
