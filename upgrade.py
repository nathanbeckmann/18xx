#!/usr/bin/python3

import math
import copy
import hex
import map
import tkinter

class UpgradeWindow:
    def __init__(self, mapWindow, r, c):
        self.hexCoords = (r,c)
        self.mapWindow = mapWindow
        self.map = self.mapWindow.map
        self.hex = self.map.getHex(r, c)

    def go(self):
        self.root = tkinter.Toplevel(self.mapWindow.frame)
        self.root.wm_title("Modify hex: %s" % self.hex.label)
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.close())
        self.root.bind("<Key>", lambda event: self.close() if event.char == 'q' else None)
        # self.root.attributes("-topmost", True)
        
        frame = tkinter.Frame(self.root)
        frame.pack(fill="both", expand=True)

        # MAX_UPGRADES_PER_ROW = 8
        # nupgrades = 0
        
        def addOption(hx, r, c):
            w = 2*math.sin(math.pi/3)*self.mapWindow.HEXSIZE + self.mapWindow.PADDING
            h = 1.5*self.mapWindow.HEXSIZE + self.mapWindow.PADDING * 2
            canvas = tkinter.Canvas(frame,
                                    width=w,
                                    height=h,
                                    background="#888888")
            # nonlocal nupgrades
            # canvas.grid(row=2 + int(nupgrades / MAX_UPGRADES_PER_ROW),
            #             column=nupgrades % MAX_UPGRADES_PER_ROW)
            # nupgrades += 1
            canvas.grid(row=r, column=c)
            canvas.bind("<Button-1>", lambda event, hx=hx: self.updateHex(hx))
                
            hw = hex.HexWindow(hx, 0, 0, self.mapWindow.HEXSIZE)
            hw.draw(canvas)

            numTiles = self.map.getNumTilesAvailable(hx.key)
            if numTiles < 50:
                canvas.create_text(16,16, text=("x%d" % numTiles),
                                   fill='white', justify=tkinter.LEFT)

        if self.hex.downgradesTo != None:
            tkinter.Label(frame, text="Downgrade:", font=("", 16, "bold")).grid(row=0,column=0,columnspan=100)
            addOption(self.hex.downgradesTo, 1, 0)

        tkinter.Label(frame, text="Upgrades:", font=("", 16, "bold")).grid(row=2,column=0,columnspan=100)
        for r, rot in enumerate(self.hex.getUpgrades()):
            for c, hx in enumerate(rot):
                addOption(hx, 3+r, c)
            
        self.root.mainloop()

    def updateHex(self, choice):
        self.map.updateHex(*self.hexCoords, choice)
        self.close()

    def close(self):
        self.root.destroy()
        self.mapWindow.redraw()
        self.mapWindow.upgradeWindow = None
