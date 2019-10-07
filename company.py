#!/usr/bin/python3

class Company:
    def __init__(self, id, name, colors, trains=[]):
        self.id = id
        self.name = name
        self.colors = colors
        self.trains = trains

    def __repr__(self):
        return "(Company: %s, Trains: %s)" % (self.id, self.trains)
