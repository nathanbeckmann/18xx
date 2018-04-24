#!/usr/bin/python3

import math
import json
import hex
import copy
import upgrade
import solver, company
from misc import *

class Map:
    class State:
        def __init__(self):
            self.hexes = []
            self.phase = 0
            self.tileLimits = {}
    
    def __init__(self):
        self.tiles = {}
        self.state = self.State()

        # undo log of hexes field
        self.history = [] # append-only log
        self.undoLog = [] # truncated upon change
        self.undoPosition = -1
        self.historyPosition = -1

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

            for tile in self.tiles.values():
                if "extends" in tile.keys():
                    assert tile["extends"] in self.tiles.keys()
                    for k, v in self.tiles[tile["extends"]].items():
                        if k not in tile.keys():
                            tile[k] = v
                    del tile["extends"]

            for key, tile in self.tiles.items():
                if "num" in tile.keys():
                    self.state.tileLimits[key] = tile["num"]
                    del tile["num"]

            def makeHex(key):
                if key == "":
                    # empty off-board locations
                    h = hex.Hex(self, key="", type=None)
                elif key not in self.tiles.keys():
                    # 1st special case for basic cities to make
                    # writing map files easier...
                    h = hex.Hex(self, key=key, label=key, **self.tiles["base-city"])
                elif "label:" == key[:6]:
                    # 2nd special case for basic cities to make
                    # writing map files easier...
                    print (key, self.tiles[key])
                    h = hex.Hex(self, key=key[6:], label=key[6:], **self.tiles[key])
                    print (h.key, h.label, h.upgradeCost)
                else:
                    # normally described tiles
                    h = hex.Hex(self, key=key, **self.tiles[key])
                return h

            processedTiles = {}
            for key in keys:
                if key in processedTiles.keys(): continue
                hx = makeHex(key)
                processedTiles[hx.key] = hx
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
            self.state.hexes.append(hexrow)

        self.height = len(self.state.hexes)
        self.width = max([ len(row) for row in self.state.hexes ])

        self.history = [ self.state ]
        self.undoLog = [ self.state ]

    def undo(self):
        self.undoPosition = max(-len(self.undoLog), self.undoPosition - 1)
        self.state = self.undoLog[self.undoPosition]
        print("Undo! @", self.undoPosition)

    def redo(self):
        self.undoPosition = min(-1, self.undoPosition + 1)
        self.state = self.undoLog[self.undoPosition]
        print("Redo! @", self.undoPosition)

    def backward(self):
        self.historyPosition = max(-len(self.history), self.historyPosition - 1)
        self.state = self.history[self.historyPosition]
        print("Backwards! @", self.historyPosition)

    def forward(self):
        self.historyPosition = min(-1, self.historyPosition + 1)
        self.state = self.history[self.historyPosition]
        print("Forwards! @", self.historyPosition)
        
    def log(self):
        if self.undoPosition < -1:
            self.undoLog = self.undoLog[:self.undoPosition+1]
        self.undoPosition = -1
        self.historyPosition = -1
        self.undoLog += [ self.state ]
        self.history += [ self.state ]

    def getHexes(self):
        return [ (ri, ci, self.getHex(ri, ci)) \
                 for ri in range(len(self.state.hexes)) \
                 for ci in range(len(self.state.hexes[ri])) ]

    def getHex(self, row, col):
        if row < len(self.state.hexes) and col < len(self.state.hexes[row]):
            return self.state.hexes[row][col]
        else:
            return None

    def getPhase(self):
        return self.state.phase

    def getNumTilesAvailable(self, key):
        if key in self.state.tileLimits:
            return self.state.tileLimits[key]
        else:
            return 1000000 # unlimited

    def updateHex(self, row, col, choice):
        if self.getNumTilesAvailable(choice.key) <= 0:
            print ("No valid tile of type: %s remaining!" % choice.label)
            return
        
        # map state is immutable. always copy before modifying
        self.state = copy.deepcopy(self.state)

        # check if the hex is an upgrade and we should track what it
        # downgraded to
        newHex = copy.deepcopy(choice)
        oldHex = self.getHex(row, col)
        if oldHex.isUpgrade(newHex):
            newHex.downgradesTo = oldHex

        # decrement new tile type and increment the old
        if newHex.key in self.state.tileLimits.keys(): self.state.tileLimits[newHex.key] -= 1
        if oldHex.key in self.state.tileLimits.keys(): self.state.tileLimits[oldHex.key] += 1

        # finally, update the hex and log the new game state
        self.state.hexes[row][col] = newHex
        self.state.phase = max( \
            [x.type for row in self.state.hexes \
             for x in row \
             if isinstance(x.type,int) ] \
            ) - 1
        
        self.log()

import tkinter
        
class MapWindow:
    PADDING = 20
    HEXSIZE = 50
    
    def __init__(self, map, hexsize=50):
        self.map = map
        self.upgradeWindow = None
        self.useMemo = True

    def run(self):
        self.root = tkinter.Tk()
        self.root.wm_title("18xx")
        self.root.bind("<Key>", lambda event: self.key(event))
        self.root.bind("<Escape>", lambda event: exit(0))
        self.root.bind("<Left>", lambda event: self.undo())
        self.root.bind("<Right>", lambda event: self.redo())
        self.root.bind("<Down>", lambda event: self.backward())
        self.root.bind("<Up>", lambda event: self.forward())
        self.root.bind("<Button-1>", lambda event: self.click(event))
        self.draw()
        # self.root.after(10000, lambda: exit(0))
        self.root.mainloop()

    def key(self, event):
        # pass
        # print ('Key press: ' + repr(event.char))
        if event.char == 'q' or event.char == 'Q': exit(0)

        if event.char == 's': self.solve()

        if event.char == 'm': self.useMemo = not self.useMemo

    def solve(self):
        # hx = self.map.getHex(2,13)
        # hx.cities[0][0] = 0
        s = solver.MapSolver(self.map, self.useMemo)
        s.solve(company.Company(0, [4,5,5]))

    def undo(self):
        self.map.undo()
        self.redraw()
        
    def redo(self):
        self.map.redo()
        self.redraw()

    def backward(self):
        self.map.backward()
        self.redraw()
        
    def forward(self):
        self.map.forward()
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
        r, c = self.pixelToHex(event.x, event.y)

        print ("Click at: (%d, %d) --> (%d, %d)" % (event.x, event.y, r, c))

        if self.map.getHex(r, c) != None:
            if self.upgradeWindow != None: self.upgradeWindow.close()
            self.upgradeWindow = upgrade.UpgradeWindow(self, r, c)
            self.upgradeWindow.go()

    def draw(self):
        self.width=int((self.map.width) * 2 * math.cos(math.pi/6) * self.HEXSIZE) + self.PADDING
        self.height=int(((self.map.height) * 1.5 + 1) * self.HEXSIZE) + self.PADDING

        self.frame = tkinter.Frame(self.root, background="#605044") # , width=width, height=height)
        self.frame.pack(fill="both", expand=True)
        
        self.canvas = None
        self.redraw()
        # self.canvas.pack(fill="both", expand=True) # place(x=0,y=0)

    def redraw(self):
        if self.canvas: self.canvas.destroy()

        self.canvas = tkinter.Canvas(self.frame,
                                     width=self.width, height=self.height,
                                     background="#302522")
        self.canvas.pack(fill="both", expand=True) # place(x=0,y=0)

        for ri, ci, hx in self.map.getHexes():
            hw = hex.HexWindow(hx, ci, ri, self.HEXSIZE)
            hw.draw(self.canvas)

        self.canvas.create_text(4,0,text="Phase %d" % (self.map.getPhase()+1),
                                fill=hex.HexWindow.color(self.map.getPhase()+1),
                                font=("",24,"bold"), anchor=tkinter.NW)
        self.canvas.create_text(4,32,text="Turn %d" % (len(self.map.undoLog)),
                                fill="gray",
                                font=("",16,"bold"), anchor=tkinter.NW)
