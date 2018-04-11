#!/usr/bin/python

import math
import numpy as np
from scipy import interpolate
from misc import *

class Hex:
    def __init__(self, type, connections=[], label="", revenue=None):
        self.connections = connections
        self.type = type
        self.label = label
        self.revenue = revenue

import widgets
import tkinter

class HexWindow:
    def __init__(self, hex, row, col, radius):
        self.hex = hex
        self.x = (2 * row + (2 if col % 2 == 0 else 1)) * radius
        self.y = (3 * col + 1) * radius / 2
        self.r = radius

    def corner(self, s):
        s %= 6
        a = s * math.pi / 3 + math.pi / 6
        return np.array((self.r + self.r * math.cos(a),
                         self.r + self.r * math.sin(a)))

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
        
    def draw(self, frame):
        # canvas = widgets.ResizingCanvas(frame)
        canvas = tkinter.Canvas(frame, width=self.r * 2, height=self.r * 2)
        # canvas.pack(fill=tkinter.NONE, expand=tkinter.NO)
        # canvas.pack()
        print (self.x, self.y)
        canvas.place(x=self.x, y=self.y) # , width=self.r * 2, height=self.r * 2)
        
        canvas.create_polygon(*flatten(self.outline()), fill='green', width=2, outline='white')
        
        canvas.create_line(*flatten(self.connect(0, 2)), fill='white', width=self.r / 10 + 2)
        canvas.create_line(*flatten(self.connect(4, 2)), fill='white', width=self.r / 10 + 2)
        # canvas.create_line(*flatten(self.connect(4, 0)), fill='white', width=self.r / 10 + 2)
        canvas.create_line(*flatten(self.connect(0, 2)), fill='black', width=self.r / 10)
        canvas.create_line(*flatten(self.connect(4, 2)), fill='black', width=self.r / 10)
        # canvas.create_line(*flatten(self.connect(4, 0)), fill='black', width=self.r / 10)

        canvas.addtag_all("all")
