#!/usr/bin/python3

import math
import copy
import hex
import map
import tkinter
import numpy as np

class UpgradeWindow:
    def __init__(self, mapWindow, r, c):
        self.hexCoords = (r,c)
        self.mapWindow = mapWindow
        self.map = self.mapWindow.map
        self.hex = self.map.getHex(r, c)
        self.cityRoot = None
        self.HEXSIZE = 60

    def go(self):
        self.root = tkinter.Toplevel(self.mapWindow.root)
        self.root.wm_title("Modify hex: %s" % self.hex.label)
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.close())
        self.root.bind("<Key>", lambda event: self.close() if event.char == 'q' else None)
        # self.root.attributes("-topmost", True)
        
        self.frame = tkinter.Frame(self.root)
        self.frame.pack(fill="both", expand=True)

        # city upgrades
        if len(self.hex.cities) > 0:
            tkinter.Label(self.frame, text="Cities:", font=("", 16, "bold")).grid(row=0,column=0,columnspan=100)
            hw = hex.HexWindow(self.hex, 0, 0, self.HEXSIZE)
            
            for ci, city in enumerate(self.hex.cities):
                w = 2*math.sin(math.pi/3)*self.HEXSIZE + self.mapWindow.PADDING
                h = 2*self.HEXSIZE + self.mapWindow.PADDING * 2
                canvas = tkinter.Canvas(self.frame,
                                        width=w,
                                        height=h)

                hw.drawCity(canvas,np.array([w/2,h/2]),self.HEXSIZE,"c%d" % ci)
                
                canvas.grid(row=1, column=ci)
                canvas.bind("<Button-1>", lambda event, ci=ci: self.upgradeCityWindow(ci))
            
        
        def addOption(hx, r, c):
            w = 2*math.sin(math.pi/3)*self.HEXSIZE + self.mapWindow.PADDING
            h = 1.5*self.HEXSIZE + self.mapWindow.PADDING * 2
            canvas = tkinter.Canvas(self.frame,
                                    width=w,
                                    height=h,
                                    background="#888888")
            # nonlocal nupgrades
            # canvas.grid(row=2 + int(nupgrades / MAX_UPGRADES_PER_ROW),
            #             column=nupgrades % MAX_UPGRADES_PER_ROW)
            # nupgrades += 1
            canvas.grid(row=r, column=c)
            canvas.bind("<Button-1>", lambda event, hx=hx: self.updateHex(hx))
                
            hw = hex.HexWindow(hx, 0, 0, self.HEXSIZE)
            hw.draw(canvas)

            numTiles = self.map.getNumTilesAvailable(hx.key)
            if numTiles < 50:
                canvas.create_text(4,4, text=("x%d" % numTiles),
                                   fill='white', anchor=tkinter.NW)

        if self.hex.downgradesTo != None:
            tkinter.Label(self.frame, text="Downgrade:", font=("", 16, "bold")).grid(row=2,column=0,columnspan=100)
            addOption(self.hex.downgradesTo, 3, 0)

        tkinter.Label(self.frame, text="Upgrades:", font=("", 16, "bold")).grid(row=4,column=0,columnspan=100)
        for r, rot in enumerate(self.hex.getUpgrades(*self.hexCoords, self.map)):
            for c, hx in enumerate(rot):
                addOption(hx, 5+r, c)
            
        self.root.mainloop()

    def updateHex(self, choice):
        self.map.updateHex(*self.hexCoords, choice)
        self.close()

    def upgradeCityWindow(self, ci):
        print ("Updating city:", ci)
        self.cityRoot = tkinter.Toplevel(self.mapWindow.root)
        self.cityRoot.wm_title("Update city stations")
        # TODO: this should maybe be a cityroot.destroy instead of
        # self.close
        self.cityRoot.protocol("WM_DELETE_WINDOW", lambda: self.close())
        self.cityRoot.bind("<Key>", lambda event: self.close() if event.char == 'q' else None)

        self.cityFrame = tkinter.Frame(self.cityRoot)
        self.cityFrame.pack(fill="both", expand=True)

        MAX_COMPANIES_PER_ROW = 8
        nrows = 1 + int((len(self.map.companies) + MAX_COMPANIES_PER_ROW - 1) / MAX_COMPANIES_PER_ROW)
        for si in range(len(self.hex.cities[ci])):
            tkinter.Label(self.cityFrame, text="Station %d:" % si, font=("", 16, "bold")).grid(row=si * nrows,column=0,columnspan=100)

            # Delete station option
            SIZE = 80
            canvas = tkinter.Canvas(self.cityFrame,
                                    width=SIZE,
                                    height=SIZE)

            hex.HexWindow.drawStation(canvas,np.array([SIZE/2,SIZE/2]),SIZE/2,None)

            canvas.grid(row=si * nrows, column=0)
            canvas.bind("<Button-1>", lambda event, ci=ci, si=si: self.upgradeCity(ci,si,None))

            # Company options
            for company in self.map.companies:
                canvas = tkinter.Canvas(self.cityFrame,
                                        width=SIZE,
                                        height=SIZE)

                hex.HexWindow.drawStation(canvas,np.array([SIZE/2,SIZE/2]),SIZE/2,company)
                
                canvas.grid(row=si * nrows + int((company.id+1) / MAX_COMPANIES_PER_ROW),
                            column=(company.id+1) % MAX_COMPANIES_PER_ROW)
                canvas.bind("<Button-1>", lambda event, ci=ci, si=si, company=company.id: self.upgradeCity(ci,si,company))
            
        self.cityRoot.mainloop()

    def upgradeCity(self, ci, si, company):
        self.map.updateCity(*self.hexCoords, ci, si, company)
        self.close()

    def close(self):
        if self.cityRoot != None: self.cityRoot.destroy()
        self.root.destroy()
        self.mapWindow.redraw()
        self.mapWindow.upgradeWindow = None
