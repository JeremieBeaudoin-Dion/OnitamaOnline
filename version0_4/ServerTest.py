# coding=utf-8
import random
import unittest
from Server0_4 import Deck

__author__ = 'Jérémie Beaudoin-Dion'


class TestDeck(unittest.TestCase):

    def test_player2fivepreferences(self):
        player2Pref = ["frog", "eel", "goose", "horse", "rabbit"]
        player1Pref = []

        gameCards = Deck().startGame(player2Pref, player1Pref)

        for card in gameCards:
            self.assertEqual(player2Pref.count(card), 1)

    def test_player1fivepreferences(self):
        player1Pref = ["frog", "eel", "goose", "horse", "rabbit"]
        player2Pref = []

        gameCards = Deck().startGame(player2Pref, player1Pref)

        for card in gameCards:
            self.assertEqual(player1Pref.count(card), 1)

    def test_morethanfivedifferentpreferences(self):
        player2Pref = ["frog", "eel", "goose", "horse", "rabbit", "dragon", "tiger"]
        player1Pref = []

        deck = Deck()
        gameCards = deck.startGame(player2Pref, player1Pref)

        for card in gameCards:
            self.assertEqual(player2Pref.count(card), 1)

    def test_player1and2fivedifferentpreferences(self):
        player2Pref = ["frog", "eel", "goose", "horse", "rabbit"]
        player1Pref = ["crane", "boar", "crab", "mantis", "elephant"]

        desireddeck = ["frog", "eel", "goose", "horse", "rabbit", "crane", "boar", "crab", "mantis", "elephant"]
        gameCards = Deck().startGame(player2Pref, player1Pref)

        for card in gameCards:
            self.assertEqual(desireddeck.count(card), 1)

    def test_player1and2indenticalpreferences(self):
        player2Pref = ["frog", "eel", "goose", "horse", "rabbit"]
        player1Pref = ["frog", "boar", "crab", "mantis", "elephant"]

        desireddeck = ["frog", "eel", "goose", "horse", "rabbit", "crane", "boar", "crab", "mantis", "elephant"]
        gameCards = Deck().startGame(player2Pref, player1Pref)

        for card in gameCards:
            self.assertEqual(desireddeck.count(card), 1)

    def test_unusualcards(self):
        player2Pref = ["bonjour", "comment", "ca", "va", "rabbit"]
        player1Pref = ["crane", "boar", "crab", "mantis", "elephant"]

        desireddeck = ["crane", "boar", "crab", "mantis", "rabbit", "elephant"]
        gameCards = Deck().startGame(player2Pref, player1Pref)

        for card in gameCards:
            self.assertEqual(desireddeck.count(card), 1)


suite = unittest.TestLoader().loadTestsFromTestCase(TestDeck)
unittest.TextTestRunner(verbosity=2).run(suite)
