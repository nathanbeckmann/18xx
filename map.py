#!/usr/bin/python3

import math
import json
import hex
import copy
import upgrade
from misc import *

class Map:
    def __init__(self):
        self.tiles = {}
        self.hexes = []

        # undo log of hexes field
        self.history = []
        self.undoLog = []
        self.undoPosition = -1

    def load(self, filename):
        with open(filename, 'r') as f:
            obj = json.load(f)

        map = obj["Map"]
        self.tiles = obj["Tiles"]

        def processTiles(keys):
            for tile in self.tiles.values():
                if "cities" not in tile.keys(): continue
                newcities = []
                for citysize in tile["cities"]:
                    newcities += [ [None] * citysize ]
                tile["cities"] = newcities

            def makeHex(type):
                if type == "":
                    h = hex.Hex(type=None)
                elif type not in self.tiles.keys():
                    h = hex.Hex(type="base", label=type, cities=[[None]])
                else:
                    tile = copy.deepcopy(self.tiles[type])
                    if "num" in tile.keys(): del tile["num"]
                    h = hex.Hex(**tile)
                return h

            processedTiles = {}
            for key in keys:
                if key in processedTiles.keys(): continue
                processedTiles[key] = makeHex(key)
            self.tiles = processedTiles

            for t in self.tiles.values():
                processedUpgradesTo = []
                for u in t.upgradesTo:
                    processedUpgradesTo += [ self.tiles[str(u)] ]
                t.upgradesTo = processedUpgradesTo

        processTiles(set(self.tiles.keys()).union(set(flatten(map))))

        for row in map:
            hexrow = []
            for col in row:
                hexrow.append(copy.deepcopy(self.tiles[col]))
            self.hexes.append(hexrow)

        self.height = len(self.hexes)
        self.width = max([ len(row) for row in self.hexes ])

        self.history = [ self.hexes ]
        self.undoLog = [ self.hexes ]

    def undo(self):
        self.undoPosition = max(-len(self.undoLog), self.undoPosition - 1)
        self.hexes = self.undoLog[self.undoPosition]
        print("Undo! @", self.undoPosition)

    def redo(self):
        self.undoPosition = min(-1, self.undoPosition + 1)
        self.hexes = self.undoLog[self.undoPosition]
        print("Redo! @", self.undoPosition)

    def log(self):
        if self.undoPosition < -1:
            self.undoLog = self.undoLog[:self.undoPosition+1]
        self.undoPosition = -1
        self.undoLog += [ self.hexes ]
        self.history += [ self.hexes ]

    def upgradeTo(self, row, col, choice):
        self.hexes = copy.deepcopy(self.hexes)
        self.hexes[row][col] = copy.deepcopy(choice)
        
        self.log()

import tkinter
        
class MapWindow:
    PADDING = 20
    HEXSIZE = 50
    
    def __init__(self, map, hexsize=50):
        self.map = map
        self.upgradeWindow = None

    def run(self):
        self.root = tkinter.Tk()
        self.root.wm_title("18xx")
        self.root.bind("<Key>", lambda event: self.key(event))
        self.root.bind("<Left>", lambda event: self.undo())
        self.root.bind("<Right>", lambda event: self.redo())
        self.root.bind("<Button-1>", lambda event: self.click(event))
        self.draw()
        # self.root.after(10000, lambda: exit(0))
        self.root.mainloop()

    def key(self, event):
        print ('Key press: ' + repr(event.char))
        if event.char == 'q' or event.char == 'Q': exit(0)

    def undo(self):
        self.map.undo()
        self.redraw()
        
    def redo(self):
        self.map.redo()
        self.redraw()

    COS60 = math.cos(math.pi/3)
    SIN60 = math.sin(math.pi/3)

    def pixelToHex(self, x, y):
        # we want to map (x,y) to new basis vectors
        #
        # x = ix x' + jx y'
        # y = iy x' + jy y'
        #
        # x' = (jy x - jx y) / (iy jx - ix jy)
        # y' = (ix y - iy x) / (iy jx - ix jy)
        
        ix, iy = 1, 0
        jx, jy = self.COS60, self.SIN60
        det = ix * jy - iy * jx
        invdet = 1. / det

        hx, hy = hex.HexWindow.hexcoords(0,0,self.HEXSIZE)
        xx, yy = x - hx, y - hy
        
        hexx = (jy * xx - jx * yy) * invdet / (2 * self.HEXSIZE * self.SIN60)
        hexy = (ix * yy - iy * xx) * invdet / (2 * self.HEXSIZE * self.SIN60)

        hexx = int(hexx + 0.5 if hexx > 0 else hexx - 0.5)
        hexy = int(hexy + 0.5 if hexy > 0 else hexy - 0.5)

        row = hexy
        col = hexx + int(hexy/2)

        return row, col

    def click(self, event):
        print ("Click at: %d, %d" % (event.x, event.y))

        r, c = self.pixelToHex(event.x, event.y)

        if r < len(self.map.hexes) and c < len(self.map.hexes[r]):
            if self.upgradeWindow != None:
                print("Closing window")
                self.upgradeWindow.close()
            self.upgradeWindow = upgrade.UpgradeWindow(self, r, c)
            self.upgradeWindow.go()

    def draw(self):
        self.width=int((self.map.width) * 2 * math.cos(math.pi/6) * self.HEXSIZE) + self.PADDING
        self.height=int(((self.map.height) * 1.5 + 1) * self.HEXSIZE) + self.PADDING

        self.frame = tkinter.Frame(self.root) # , width=width, height=height)
        self.frame.pack(fill="both", expand=True)
        
        self.canvas = tkinter.Canvas(self.frame,
                                     width=self.width, height=self.height,
                                     background="#888888")
        self.redraw()
        # self.canvas.pack(fill="both", expand=True) # place(x=0,y=0)

    def redraw(self):
        self.canvas.destroy()

        self.canvas = tkinter.Canvas(self.frame,
                                     width=self.width, height=self.height,
                                     background="#888888")
        self.canvas.pack(fill="both", expand=True) # place(x=0,y=0)

        for ri, row in enumerate(self.map.hexes):
            for ci, col in enumerate(row):
                hw = hex.HexWindow(self.map.hexes[ri][ci],
                                   ci, ri, self.HEXSIZE)
                hw.draw(self.canvas)
