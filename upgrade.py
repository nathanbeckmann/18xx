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
        self.hex = self.map.hexes[r][c]

    def go(self):
        self.root = tkinter.Toplevel(self.mapWindow.frame)
        self.root.wm_title("Upgrade %s" % self.hex.label)
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.close())
        self.root.bind("<Key>", lambda event: self.close() if event.char == 'q' else None)
        # self.root.attributes("-topmost", True)
        
        frame = tkinter.Frame(self.root)
        frame.pack(fill="both", expand=True)
        # self.bind("<Button-1>", lambda event: self.click(event))

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
            canvas.grid(row=1 + r, column=c)
            canvas.bind("<Button-1>", lambda event, hx=hx: self.upgradeTo(hx))
                
            hw = hex.HexWindow(hx, 0, 0, self.mapWindow.HEXSIZE)
            hw.draw(canvas)

        tkinter.Label(frame, text="Upgrades:").grid(row=1,column=1)

        for r, rot in enumerate(self.hex.getUpgrades()):
            for c, hx in enumerate(rot):
                addOption(hx, r, c)
        # for i, label in enumerate(self.hex.upgradesTo):
        #     h = self.map.tiles[label]
        #     for r in range(6):
        #         hx = copy.deepcopy(h)
        #         hx.rotation = r
        #         if self.hex.isValidUpgrade(hx):
        #             addOption(hx, i, r)
            
        self.root.mainloop()

    def upgradeTo(self, choice):
        self.map.upgradeTo(*self.hexCoords, choice)
        self.close()

    def close(self):
        self.root.destroy()
        self.mapWindow.redraw()
        self.mapWindow.upgradeWindow = None
