#!/usr/bin/python3

import math
import json
import hex
import copy
import upgrade
import solver, company
import pickle
import numpy as np
import time
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
        self.solution = None

    def load(self, filename):
        with open(filename, 'r') as f:
            obj = json.load(f)

        map = obj["Map"]
        if "Transposed" in obj.keys() and obj["Transposed"] == "True":
            newMap = []
            width = max([ len(r) for r in map ])
            for ci in range(width):
                newRow = []
                for ri in range(len(map)-1,-1,-1):
                    if ci < len(map[ri]):
                        newRow.append(map[ri][ci])
                    else:
                        newRow.append("")
                newMap.append(newRow)
            map = newMap
                        
        self.tiles = { k: v for k,v in obj["Tiles"].items() if "####" not in k }
        self.companies = [[0]] * obj["Companies"]
        self.trains = {}
        for phase, trains in obj["Trains"].items():
            for train in trains:
                self.trains[train] = int(phase)

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
                    h = None # hex.Hex(self, key="", type=None)
                elif key not in self.tiles.keys():
                    # 1st special case for basic cities to make
                    # writing map files easier...
                    h = hex.Hex(self, key=key, label=key, **self.tiles["base-city"])
                elif "label:" == key[:6]:
                    # 2nd special case for basic cities to make
                    # writing map files easier...
                    h = hex.Hex(self, key=key[6:], label=key[6:], **self.tiles[key])
                else:
                    # normally described tiles
                    h = hex.Hex(self, key=key, **self.tiles[key])
                return h

            processedTiles = {}
            for key in keys:
                if key in processedTiles.keys(): continue
                hx = makeHex(key)
                processedTiles[hx.key if hx else key] = hx
            self.tiles = processedTiles

            for t in self.tiles.values():
                if t == None: continue
                processedUpgradesTo = []
                for u in t.upgradesTo:
                    processedUpgradesTo += [ self.tiles[str(u)] ]
                t.upgradesTo = processedUpgradesTo

        processTiles(set(self.tiles.keys()).union(set(flatten(map))))

        for row, rowTiles in enumerate(map):
            hexrow = []
            for col, tileType in enumerate(rowTiles):
                hx = copy.deepcopy(self.tiles[tileType])
                if hx != None:
                    hx.row = row
                    hx.col = col
                hexrow.append(hx)
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
                 for ci in range(len(self.state.hexes[ri]))
                 if self.getHex(ri,ci) != None ]

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
        if newHex != None:
            newHex.row = row
            newHex.col = col

        # copy tokens
        if newHex.type != "base" and (oldHex.type == "base" or newHex.type > oldHex.type):
            cityMap = [ i % len(newHex.cities) for i in range(len(oldHex.cities)) ]
            cityIndex = [ 0 ] * len(newHex.cities)

            for ci, city in enumerate(oldHex.cities):
                for j in city:
                    nci = cityMap[ci]
                    newHex.cities[nci][cityIndex[nci]] = j
                    cityIndex[nci] += 1
            
        self.log()

    def updateCity(self, row, col, city, station, company):
        # map state is immutable. always copy before modifying
        self.state = copy.deepcopy(self.state)
        
        hx = self.getHex(row, col)
        if hx == None: return

        assert city < len(hx.cities)
        assert station < len(hx.cities[city])

        hx.cities[city][station] = company

        self.log()

    def updatePhase(self):
        self.state.phase = max([self.trains[t] \
                                for c in self.companies \
                                for t in c \
                                if t in self.trains.keys()]) \
                           - 1

import tkinter
        
class MapWindow:
    PADDING = 20
    HEXSIZE = 30
    
    def __init__(self, map, hexsize=50):
        self.map = map
        self.upgradeWindow = None

    def run(self):        
        self.init()
        # self.root.after(10000, lambda: exit(0))
        self.root.mainloop()

    def key(self, event):
        # pass
        # print ('Key press: ' + repr(event.char))
        if event.char == 'q' or event.char == 'Q': exit(0)

        # if event.char == 's': self.solve()

        if event.char == 'x':
            print ("Saved map state.")
            with open('test.save', 'wb') as f:
                pickle.dump(self.map, f)

    def solve(self, ci):
        s = solver.MapSolver(self.map)
        solId = time.time()
        self.map.solution = list(s.solve(company.Company(ci, self.map.companies[ci]))) + [solId]
        self.redraw()
        self.root.after(10000, lambda solId=solId: self.clearSolution(solId))

    def clearSolution(self, solId):
        if self.map.solution != None and self.map.solution[-1] == solId:
            self.map.solution = None
            self.redraw()

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

    def updateTrains(self, companyIndex, trains):
        try:
            self.map.companies[companyIndex] = [ int(t) for t in trains.split(',') ]
            print ("Company %s has trains: %s" % (companyIndex, self.map.companies[companyIndex]))
        except:
            pass
        
        if self.map.companies[companyIndex] == []:
            self.map.companies[companyIndex] = [0]

        oldPhase = self.map.getPhase()
        self.map.updatePhase()
        if self.map.getPhase() != oldPhase:
            self.redraw()
            print ("Entered phase: %d" % (self.map.getPhase()+1))

    def init(self):
        self.width=int((self.map.width) * 2 * math.cos(math.pi/6) * self.HEXSIZE) + self.PADDING
        self.height=int(((self.map.height) * 1.5 + 1) * self.HEXSIZE) + self.PADDING
        
        self.root = tkinter.Tk()
        self.root.wm_title("18xx")
        self.root.bind("<Key>", lambda event: self.key(event))
        # self.root.bind("<Escape>", lambda event: exit(0))
        self.root.bind("<Left>", lambda event: self.undo())
        self.root.bind("<Right>", lambda event: self.redo())
        self.root.bind("<Down>", lambda event: self.backward())
        self.root.bind("<Up>", lambda event: self.forward())
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Top text
        infoFrame = tkinter.Frame(self.root)
        infoFrame.pack(fill=tkinter.X)

        self.phaseLabelText = tkinter.StringVar()
        self.phaseLabel = tkinter.Label(infoFrame, textvariable=self.phaseLabelText)
        self.phaseLabel.pack(side=tkinter.LEFT, fill=tkinter.X, anchor=tkinter.W, expand=True)

        self.turnLabelText = tkinter.StringVar()
        self.turnLabel = tkinter.Label(infoFrame, textvariable=self.turnLabelText)
        self.turnLabel.pack(side=tkinter.LEFT, fill=tkinter.X, anchor=tkinter.CENTER, expand=True)

        self.solutionLabelText = tkinter.StringVar()
        self.solutionLabel = tkinter.Label(infoFrame, textvariable=self.solutionLabelText)
        self.solutionLabel.pack(side=tkinter.LEFT, fill=tkinter.X, anchor=tkinter.E, expand=True)

        # map
        mapFrame = tkinter.Frame(self.root) # width=self.width, height=self.height)
        mapFrame.pack(fill=tkinter.BOTH, expand=True)

        # draw companies
        companyFrame = tkinter.Frame(self.root)
        companyFrame.pack(side=tkinter.LEFT, fill=tkinter.Y)
        
        # label = tkinter.Label(companyFrame, text="Companies:", font=("", 16, "bold"))
        # label.pack() # (row=0,column=1,columnspan=2)

        SIZE = 40
        COMPANIESPERROW = 12

        for ci, company in enumerate(self.map.companies):
            # if company == None: continue
            cf = tkinter.Frame(companyFrame)

            canvas = tkinter.Canvas(cf,width=SIZE,height=SIZE)
            hex.HexWindow.drawStation(canvas,np.array([SIZE/2,SIZE/2]),SIZE/2,ci)
            canvas.pack(side=tkinter.LEFT) # grid(row=1, column=2*ci)
            canvas.bind("<Button-1>", lambda event, ci=ci: self.solve(ci))

            content = tkinter.StringVar()
            content.set(','.join([str(t) for t in company]))
            content.trace("w", lambda name, index, mode, ci=ci, content=content: self.updateTrains(ci, content.get()))
            text = tkinter.Entry(cf,textvariable=content, width=8) # width=16,height=1)
            text.pack(side=tkinter.LEFT)
            
            cf.grid(row=int(ci / COMPANIESPERROW), column=ci % COMPANIESPERROW)

        # draw map
        self.canvas = tkinter.Canvas(mapFrame,
                                     width=self.width, height=self.height,
                                     background="#605044")
        self.canvas.pack(side=tkinter.LEFT, expand=True, fill=tkinter.BOTH) #, row=0, column=0, rowspan=100)
        
        self.canvas.bind('<B1-Motion>',     self.moveTo)
        self.canvas.bind('<ButtonPress-1>', self.moveFrom)
        self.canvas.bind("<ButtonRelease-1>", lambda event: self.click(event))
        self.canvas.bind('<MouseWheel>', self.wheel)  # with Windows and MacOS, but not Linux
        self.canvas.bind('<Button-5>',   self.wheel)  # only with Linux, wheel scroll down
        self.canvas.bind('<Button-4>',   self.wheel)  # only with Linux, wheel scroll up
        # self.canvas.bind('<Configure>', lambda event: self.canvas.config(width=event.width-2, height=event.height-2))
        
        self.redraw()

    def redraw(self):
        # redraw map
        self.canvas.delete('all')
        
        for ri, ci, hx in self.map.getHexes():
            hw = hex.HexWindow(hx, ci, ri, self.HEXSIZE)
            hw.draw(self.canvas)

        # update info
        self.phaseLabelText.set("Phase %d" % (self.map.getPhase() + 1))
        self.phaseLabel.config(font=("",16,"bold"), fg=hex.HexWindow.getHexColor(self.map.getPhase()+1))
        self.turnLabelText.set("Turn %d" % (len(self.map.undoLog) + self.map.undoPosition + 1))
        self.turnLabel.config(font=("",16,"bold"), fg="gray")

        if self.map.solution:
            self.solutionLabelText.set("Revenue: %d" % (self.map.solution[0]))
        else:
            self.solutionLabelText.set("")
        self.solutionLabel.config(fg="red", font=("",16,"bold"))

    def moveFrom(self, event):
        self.dragStart = np.array((event.x, event.y))
        self.canvas.scan_mark(event.x, event.y)

    def moveTo(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def wheel(self, event):
        # Respond to Linux (event.num) or Windows (event.delta) wheel event
        ZOOMSTEP = 1.1
        scale = 1
        if event.num == 5 or event.delta == -120:  # scroll down
            scale /= ZOOMSTEP
        if event.num == 4 or event.delta == 120:  # scroll up
            scale *= ZOOMSTEP
        self.HEXSIZE *= scale

        # the premise here is that canvasx/y is just doing a translation...
        self.canvas.scan_mark(event.x, event.y)
        delta = np.array((self.canvas.canvasx(0), self.canvas.canvasy(0)))

        vorigscreen = np.array((event.x, event.y))
        vorigcanvas = vorigscreen + delta
        vzoomcanvas = vorigcanvas / scale
        vzoomscreen = vzoomcanvas - delta
        self.canvas.scan_dragto(int(vzoomscreen[0]), int(vzoomscreen[1]), gain=1)
        
        self.redraw()
        # self.canvas.scale('all', x, y, scale, scale)  # rescale all canvas objects
    
    def click(self, event):
        delta = np.array((event.x, event.y)) - self.dragStart
        if np.sum(delta**2) > self.HEXSIZE: return
        
        r, c = self.pixelToHex(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))

        print ("Click at: (%d, %d) --> (%d, %d)" % (event.x, event.y, r, c))

        if self.map.getHex(r, c) != None:
            if self.upgradeWindow != None:
                self.upgradeWindow.close()
                self.upgradeWindow = None
            self.upgradeWindow = upgrade.UpgradeWindow(self, r, c)
            self.upgradeWindow.go()

