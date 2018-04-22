#!/usr/bin/python

import math
import copy
import numpy as np
from scipy import interpolate
from misc import *

class Hex:
    def __init__(self, type, connections=[],
                 label="", revenue=None, upgradeCost=0,
                 upgradesTo=[], cities=[], towns=0,
                 rotation = 0):
        self.connections = connections
        self.type = type
        self.label = label
        self.revenue = revenue
        self.upgradeCost = upgradeCost
        self.upgradesTo = upgradesTo
        self.cities = cities
        self.towns = towns
        self.rotation = rotation

    def stops(self):
        return len(self.cities) + self.towns

    def isValidUpgrade(self, upgrade):
        return True

    def getUpgrades(self):
        upgrades = []

        for u in self.upgradesTo:
            rotations = []
            for r in range(6):
                hx = copy.deepcopy(u)
                hx.rotation = r
                if self.isValidUpgrade(hx):
                    rotations += [hx]
            if len(rotations) > 0:
                upgrades += [rotations]

        return upgrades

import map
import widgets
import tkinter

class HexWindow:
    def hexcoords(row, col, radius):
        x = (2 * row + (0 if col % 2 == 0 else 1) + 1) * radius * math.sin(math.pi/3)
        y = (1.5 * col + 1) * radius
        x += map.MapWindow.PADDING / 2
        y += map.MapWindow.PADDING / 2
        return x, y
    
    def __init__(self, hex, row, col, radius):
        self.hex = hex
        self.x, self.y = HexWindow.hexcoords(row, col, radius)
        self.r = radius

    def corner(self, s):
        s %= 6
        a = s * math.pi / 3 - 3 * math.pi / 6
        return np.array((self.x + self.r * math.cos(a),
                         self.y + self.r * math.sin(a)))

    def outline(self):
        return [ self.corner(i) for i in range(6) ]

    def side(self, s):
        s0 = self.corner(s)
        s1 = self.corner(s+1)
        return (s0 + s1) / 2

    def normal(self, s):
        s0 = self.corner(s)
        s1 = self.corner(s+1)
        return np.array((s1[1] - s0[1], s0[0] - s1[0]))

    def connect(self, s0, s1):
        p0 = self.side(s0)
        p1 = self.side(s1)

        n0 = self.normal(s0)
        n1 = self.normal(s1)

        pp0 = p0 + n0 / 10
        pp1 = p1 + n1 / 10

        points = np.array([ pp0, p0, p1, pp1 ])

        tck,u     = interpolate.splprep(points.T, s = 0, k = 3)
        xnew,ynew = interpolate.splev(np.linspace(0.05, 0.95, 100), tck, der = 0)

        return np.array([xnew, ynew]).T

    def center(self):
        return (self.x, self.y)

    def color(self, type):
        if type == "base":
            return "#cccccc"
        elif type == 1:
            return "yellow"
        elif type == 2:
            return "green"
        elif type == 3:
            return "brown"
        elif type == 4:
            return "gray"
        elif type == "off-board":
            return "#cc8888"
        else:
            print (type)
            assert False
        
    def draw(self, canvas):
        if self.hex.type == None: return

        if self.hex.type != "off-board" or self.hex.label != "":
            canvas.create_polygon(*flatten(self.outline()),
                                  fill=self.color(self.hex.type),
                                  width=2, outline='white')

        # compute locations of cities and towns
        stops = {}
        stopsToDraw = self.hex.stops()
        r = self.r / 3 if stopsToDraw >= 2 else 0
        a = self.hex.rotation * math.pi / 3

        for c in range(len(self.hex.cities)):
            stops['city-%d' % c] = self.center() + np.array((math.cos(a), math.sin(a))) * r
            a += 2 * math.pi / stopsToDraw

        for t in range(self.hex.towns):
            stops['town-%d' % t] = self.center() + np.array((math.cos(a), math.sin(a))) * r
            a += 2 * math.pi / stopsToDraw

        # draw connections
        def rotate(x):
            if isinstance(x,int):
                return (x + self.hex.rotation) % 6
            else:
                return x
        
        for conn in self.hex.connections:
            start = rotate(conn[0])
            end = rotate(conn[-1])

            if start == "None":
                # off-board locations
                p = self.side(end)
                n = self.normal(end)
                line = [p, p-n/4]
            elif isinstance(end, str):
                # connections to towns and cities
                # for now, assume it always goes into the hex center...
                line = [self.side(start), stops[end]]
            else:
                line = self.connect(start, end)
            line = np.array(line)

            flatline = flatten(line)
            canvas.create_line(*flatline, fill='white', width=self.r / 10 + 2)
            canvas.create_line(*flatline, fill='black', width=self.r / 10)

        # unconnected cities and towns
        def draw_circle(p, r, **kwargs):
            tl = p - (r/2, r/2)
            br = p + (r/2, r/2)
            canvas.create_oval(*flatten([tl, br]), **kwargs)

        cityrad = self.r/2
        townrad = self.r/4
        
        for stop, location in stops.items():
            if 'city' in stop:
                cidx = int(stop.split("-")[-1])
                citysize = len(self.hex.cities[cidx])
                if citysize > 1:
                    nrows = citysize / 2
                    ncols = min(citysize, 2)
                    dim = np.array([ncols, nrows]) * cityrad
                    canvas.create_rectangle(*(location-dim/2), *(location + dim/2),
                                            fill='white', outline='black', width=1)

                    # move location to top-left station
                    # 1 ->    ()    0 offset from center
                    # 2 ->   ()()   0.5 offset ...
                    # 3 ->  ()()()  1 offset ...
                    # 4 -> ()()()() 1.5 offset ...
                    location[0] -= ((ncols-1)/2) * cityrad
                    location[1] -= ((nrows-1)/2) * cityrad
                    
                for c in range(citysize):
                    station = location
                    station[0] += cityrad * int(c % 2)
                    station[1] += cityrad * int(c / 2)
                    draw_circle(station, cityrad, fill="white", outline="black", width=1)

            elif 'town' in stop:
                draw_circle(location, townrad, fill="black", outline="white", width=1)
            else:
                print (stop)
                assert False

        # text rendering
        location = np.array(self.center())
        if self.hex.stops() > 0 and self.hex.revenue != None: location += (0, -self.r/4)
        
        if self.hex.stops() > 0: location -= (0, self.r/3 + 2)
        if self.hex.label != "":
            canvas.create_text(*location, fill="black",
                               text=self.hex.label)
            location += (0, 16)
        if self.hex.revenue != None:
            if isinstance(self.hex.revenue, int):
                location += (-32, 0)
                canvas.create_oval(*(location - (10,10)),
                                        *(location + (10,10)),
                                        fill='black')
                canvas.create_text(*location, fill="white",
                                   text=self.hex.revenue)
            else:
                location -= (8 * len(self.hex.revenue), 0)
                for level, rev in enumerate(self.hex.revenue):
                    canvas.create_rectangle(*(location - (9,8)),
                                            *(location + (9,8)),
                                            fill=self.color(level+1))
                    canvas.create_text(*location,
                                       fill='black',
                                       text = rev)
                    location += (20, 0)
        if self.hex.upgradeCost != 0:
            location += (32, 0)
            canvas.create_text(*location,
                               fill='red',
                               text = '$%d' % self.hex.upgradeCost)

        canvas.addtag_all("all")
