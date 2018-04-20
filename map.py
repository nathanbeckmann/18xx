#!/usr/bin/python

import math
import json
import hex

class Map:
    def __init__(self):
        self.tiles = {}
        self.hexes = []

    def load(self, filename):
        with open(filename, 'r') as f:
            obj = json.load(f)

        map = obj["Map"]
        self.tiles = obj["Tiles"]

        for tile in self.tiles.values():
            if "cities" not in tile.keys(): continue
            newcities = []
            for citysize in tile["cities"]:
                newcities += [ [None] * citysize ]
            tile["cities"] = newcities

        for row in map:
            hexrow = []
            for col in row:
                if col == "":
                    h = hex.Hex(type=None)
                elif col not in self.tiles.keys():
                    h = hex.Hex(type="base", label=col, cities=[[None]])
                else:
                    tile = self.tiles[col]
                    h = hex.Hex(**tile)
                hexrow.append(h)
            self.hexes.append(hexrow)

        self.height = len(self.hexes)
        self.width = max([ len(row) for row in self.hexes ])

import tkinter
        
class MapWindow:
    PADDING = 10
    HEXSIZE = 60
    
    def __init__(self, map, hexsize=50):
        self.map = map

    def run(self):
        self.root = tkinter.Tk()
        self.root.bind("<Key>", lambda event: self.key(event))
        self.draw()
        # self.root.after(10000, lambda: exit(0))
        self.root.mainloop()

    def key(self, event):
        print ('Key press: ' + repr(event.char))
        if event.char == 'q' or event.char == 'Q': exit(0)

    def draw(self):
        width=int((self.map.width) * 2 * math.cos(math.pi/6) * self.HEXSIZE) + self.PADDING
        height=int((self.map.height) * 1.5 * self.HEXSIZE) + self.PADDING

        frame = tkinter.Frame(self.root) # , width=width, height=height)
        frame.pack(fill="both", expand=True)
        
        canvas = tkinter.Canvas(frame, width=width, height=height, background="#888888")
        canvas.pack(fill="both", expand=True) # place(x=0,y=0)

        for ri, row in enumerate(self.map.hexes):
            for ci, col in enumerate(row):
                hw = hex.HexWindow(self.map.hexes[ri][ci],
                                   ci, ri, self.HEXSIZE)
                hw.draw(canvas)
