#!/usr/bin/python

import math
import numpy as np
from scipy import interpolate
from misc import *

class Hex:
    def __init__(self, type, connections=[], label="", revenue=None, cities=0, towns=0):
        self.connections = connections
        self.type = type
        self.label = label
        self.revenue = revenue
        self.cities = cities
        self.towns = towns

    def stops(self):
        return self.cities + self.towns

import map
import widgets
import tkinter

class HexWindow:
    def __init__(self, hex, row, col, radius):
        self.hex = hex
        self.x = (2 * row + (0 if col % 2 == 0 else 1)) * radius * math.cos(math.pi/6)
        self.y = 1.5 * (col + 0.5) * radius
        self.x += map.MapWindow.PADDING / 2
        self.y += map.MapWindow.PADDING / 2
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
        else:
            print (type)
            assert False
        
    def draw(self, canvas):
        if self.hex.type == None: return

        if self.hex.type != "off-board":
            canvas.create_polygon(*flatten(self.outline()),
                                  fill=self.color(self.hex.type),
                                  width=2, outline='white')

        citiesToDraw = self.hex.cities
        townsToDraw = self.hex.towns

        def draw_circle(p, r, **kwargs):
            tl = p - (r/2, r/2)
            br = p + (r/2, r/2)
            canvas.create_oval(*flatten([tl, br]), **kwargs)

        for conn in self.hex.connections:
            start = conn[0]
            end = conn[-1]
            stop = conn[1] if len(conn) > 2 else None

            if start == "None":
                # off-board locations
                p = self.side(end)
                n = self.normal(end)
                line = [p, p-n/4]
            elif isinstance(end, str):
                # connections to towns and cities
                # for now, assume it always goes into the hex center...
                line = [self.side(start), self.center()]
            else:
                line = self.connect(start, end)

            flatline = flatten(line)
            canvas.create_line(*flatline, fill='white', width=self.r / 10 + 2)
            canvas.create_line(*flatline, fill='black', width=self.r / 10)

            if stop != None:
                t = np.linspace(0,1,len(flatline))
                location = (np.interp(0.5, t, flatline[:,0]),np.interp(0.5, t, flatline[:,0]))

                if stop == "city":
                    assert citiesToDraw > 0
                    citiesToDraw -= 1
                    draw_circle(location, self.r / 2, fill="white", outline="black", width=1)
                elif stop == "town":
                    assert townsToDraw > 0
                    townsToDraw -= 1
                    draw_circle(location, self.r / 4, fill="black", outline="white", width=1)

        # unconnected cities and towns
        stopsToDraw = citiesToDraw + townsToDraw
        r = 3 * self.r / 2 if stopsToDraw >= 2 else 0
        a = math.pi / 2

        for c in range(citiesToDraw):
            location = self.center() + np.array((math.cos(a), math.sin(a))) * r
            draw_circle(location, self.r / 2, fill="white", outline="black", width=1)
            a += math.pi / stopsToDraw

        for t in range(townsToDraw):
            location = self.center() + np.array((math.cos(a), math.sin(a))) * r
            draw_circle(location, self.r / 4, fill="black", outline="white", width=1)
            a += math.pi / stopsToDraw
            
        location = np.array(self.center()) + (0, -8)
        if self.hex.stops() > 0: location -= (0, self.r/3 + 2)
        if self.hex.label != "":
            canvas.create_text(*location, fill="black",
                               text=self.hex.label)
            location += (0, 16)
        if self.hex.revenue != None:
            if isinstance(self.hex.revenue, int):
                canvas.create_text(*location, fill="black",
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

        canvas.addtag_all("all")
