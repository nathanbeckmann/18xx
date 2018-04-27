#!/usr/bin/python3

class Company:
    def __init__(self, id=0, trains=[]):
        self.id = id
        self.trains = trains

    def __repr__(self):
        return "(Company: %s, Trains: %s)" % (self.id, self.trains)
