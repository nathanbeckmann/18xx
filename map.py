#!/usr/bin/python

import json
import hex

class Map:
    def __init__(self):
        self.tiles = {}
        self.hexes = []

    def load(self, filename):
        with open(filename, 'r') as f:
            obj = json.load(f)
            print(obj)

        map = obj["Map"]
        self.tiles = obj["Tiles"]

        for row in map:
            hexrow = []
            for col in row:
                print (col)
                if col == "":
                    h = hex.Hex(type=None)
                elif col not in self.tiles.keys():
                    h = hex.Hex(type="City", label=tile)
                else:
                    tile = self.tiles[col]
                    h = hex.Hex(**tile)
                hexrow.append(h)
            self.hexes.append(hexrow)

        self.height = len(self.hexes)
        self.width = max([ len(row) for row in self.hexes ])

import tkinter
        
class MapWindow:
    def __init__(self, map, hexsize=50):
        self.map = map
        self.hexsize = 30

    def run(self):
        self.root = tkinter.Tk()
        self.draw()
        self.root.mainloop()

    def draw(self):
        print (self.map.width, self.map.height)

        width=int((self.map.width + 1) * 2 * self.hexsize)
        height=int((self.map.height + 1) * 3 * self.hexsize / 2)

        print (width, height)

        frame = tkinter.Frame(self.root, width=width, height=height)
        frame.pack()
        frame.place(width=width, height=height)

        for ri, row in enumerate(self.map.tiles):
            for ci, col in enumerate(row):
                hw = hex.HexWindow(self.map.hexes[ri][ci],
                                   ci, ri, self.hexsize)
                hw.draw(frame)
