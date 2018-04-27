#!/usr/bin/python

import math
import copy
import numpy as np
import solver
from scipy import interpolate
from misc import *

class Hex:
    def __init__(self, map,
                 key, type, connections=[],
                 label="", revenue=None, upgradeCost=0,
                 upgradesTo=[], cities=[], towns=0,
                 rotation = 0):

        self.row = 0
        self.col = 0
        self.key = key
        self.map = map
        self.connections = connections
        self.type = type
        self.label = label
        self.revenue = revenue
        self.upgradeCost = upgradeCost
        self.upgradesTo = upgradesTo
        self.downgradesTo = None # previous hex in this position
        self.cities = cities
        self.towns = towns
        self.rotation = rotation

        self.canonicalizeConnections()

    def __repr__(self):
        return "Hex:%s-%s" % (self.type, self.label)

    def canonicalizeConnections(self):
        # canonical form for connections is that the connection
        # list is sorted and each individual connection is sorted
        # as well
        #
        # this matters to eliminate duplicates when doing upgrades
        def keyfn(x):
            return str(x)
                
        for ci in range(len(self.connections)):
            self.connections[ci] = sorted(self.connections[ci], key=keyfn)
        self.connections = sorted(self.connections)

        # # directed map of what connects to what. useful when solving
        # # for optimal routes.
        # self.connectsTo = {}
        # for conn in self.connections:
        #     assert len(conn) == 2
            
        #     if conn[0] in self.connectsTo.keys():
        #         self.connectsTo[conn[0]] += [conn[1]]
        #     else:
        #         self.connectsTo[conn[0]] = [conn[1]]
                
        #     if conn[1] in self.connectsTo.keys():
        #         self.connectsTo[conn[1]] += [conn[0]]
        #     else:
        #         self.connectsTo[conn[1]] = [conn[0]]

    def __deepcopy__(self, memo):
        # do a selective, shallow copy of the hex pieces, since hexes
        # are immutable --- do NOT deepcopy the map, or it blows up
        # memory!
        newHex = copy.copy(self)
        newHex.connections = copy.deepcopy(self.connections, memo)
        # newHex.connectsTo = copy.deepcopy(self.connectsTo, memo)
        newHex.revenue = copy.deepcopy(self.revenue, memo)
        # newHex.upgradesTo = copy.deepcopy(self.upgradesTo)
        # newHex.downgradesTo = copy.deepcopy(self.downgradesTo)
        newHex.cities = copy.deepcopy(self.cities, memo)
        return newHex

    def stops(self):
        return len(self.cities) + self.towns

    def isUpgrade(self, upgrade):
        return upgrade.type in [ hx.type for hx in self.upgradesTo ]

    def rotate(self, r):
        self.rotation += r
        self.rotation %= 6
        
        def rot(x):
            if isinstance(x,int):
                return (x + self.rotation) % 6
            else:
                return x

        for i in range(len(self.connections)):
            self.connections[i] = [ rot(x) for x in self.connections[i] ]

        self.canonicalizeConnections()

    @staticmethod
    def step(r, c, hexside):
        if isinstance(hexside,int):
            # compute the facing hexside from the destination's
            # perspective
            delta = {
                0: (-1, 1),
                1: (0, 1),
                2: (1, 1),
                3: (1, 0),
                4: (0, -1),
                5: (-1, 0)
            }[hexside]
            dst = [r + delta[0], c + delta[1], hexside]
            if delta[0] != 0 and r % 2 == 0: dst[1] -= 1

            # the hexside we connect to is mirrored from the
            # perspective of the destination
            dst[2] += 3
            dst[2] %= 6

            return tuple(dst)
        else:
            return (r,c,hexside)

    def getUpgrades(self, r, c, map):
        upgrades = []

        def preservesConnections(hx):

            # if there are multiple stops or if the number of stops
            # has reduced, we need to find a valid mapping of stops
            # from the old tile to the new tile. the implementation is
            # simpler assuming only two stops on a tile.
            assert self.stops() <= 2
            assert self.stops() >= hx.stops()

            selfstops  = [ "town-%d" % d for d in range(self.towns) ]
            selfstops += [ "city-%d" % d for d in range(len(self.cities)) ]
            hxstops  = [ "town-%d" % d for d in range(hx.towns) ]
            hxstops += [ "city-%d" % d for d in range(len(hx.cities)) ]

            renames = []
            def generate(indices):
                nonlocal renames
                if len(indices) == len(selfstops):
                    rename = {}
                    for i, j in enumerate(indices):
                        rename[selfstops[i]] = hxstops[j]
                    renames += [ rename ]
                else:
                    for i in range(len(hxstops)):
                        generate(indices + [i])
            generate([])

            def preservesConnectionsRenamed(hx, rename):
                # under a given renaming of cities, the tile fails to
                # preserve connections if _any_ connection fails.
                for curr in self.connections:
                    assert len(curr) == 2
                    matched = False
                    for new in hx.connections:
                        assert len(new) == 2

                        curr0 = rename[curr[0]] if curr[0] in rename.keys() else curr[0]
                        curr1 = rename[curr[1]] if curr[1] in rename.keys() else curr[1]

                        if (curr0 == new[0] and curr1 == new[1]) or \
                           (curr1 == new[0] and curr0 == new[1]):
                            matched = True
                            break

                    if not matched:
                        return False
            
                return True

            # but overall, the tile succeeds in preserving connections
            # if _any_ renaming succeeds
            for rename in renames:
                if preservesConnectionsRenamed(hx, rename):
                    return True
            return False

        def equivalentConnections(hx1, hx2):
            return hx1.connections == hx2.connections

        def runsOffBoard(hx):
            for conn in hx.connections:
                dst = Hex.step(r, c, conn[0])
                if map.getHex(*dst[:2]) == None: return True
                dst = Hex.step(r, c, conn[1])
                if map.getHex(*dst[:2]) == None: return True
            return False

        for u in self.upgradesTo:
            rotations = []
            for rot in range(6):
                hx = copy.deepcopy(u)
                hx.rotate(rot)

                valid = True
                valid = valid and preservesConnections(hx)
                valid = valid and self.map.getNumTilesAvailable(u.key) > 0
                valid = valid and not any([ equivalentConnections(hx, x) for x in rotations ])
                valid = valid and not runsOffBoard(hx)
                
                if valid:
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
        xnew,ynew = interpolate.splev(np.linspace(0.05, 0.95, 20), tck, der = 0)

        return np.array([xnew, ynew]).T

    def center(self):
        return (self.x, self.y)

    def getHexColor(type):
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

    def getCityColor(city):
        primaryColors = [ '#444444', 'red', 'green', 'blue', 'cyan', 'yellow' ]
        secondaryColors = primaryColors + [ 'white' ]

        pairedColors = [ (primaryColors[p], secondaryColors[s]) \
                          for p in range(len(primaryColors)) \
                          for s in range(len(secondaryColors)) \
                          if p != s ]

        if city == None:
            return ['white']
        elif city < len(primaryColors):
            return [primaryColors[city]]
        elif city < len(primaryColors) * len(secondaryColors):
            return pairedColors[city - len(primaryColors)]
        else:
            assert False
        
    def drawCircle(canvas, p, r, c, o, w=1, **kwargs):
        tl = p - (r/2, r/2)
        br = p + (r/2, r/2)
        canvas.create_oval(*flatten([tl, br]), fill=c, outline=o, width=w, **kwargs)

    def drawStation(canvas, p, r, city, **kwargs):
        colors = HexWindow.getCityColor(city)
        HexWindow.drawCircle(canvas, p, r, c=colors[0], o='black', w=1)
        for c in colors[1:]:
            HexWindow.drawCircle(canvas, p, r/len(colors), c='', o=c, w=r/len(colors)/3)

    def drawCity(self, canvas, p, r, stop, **kwargs):
        cidx = int(stop.split("-")[-1])
        citysize = len(self.hex.cities[cidx])
        if citysize > 1:
            nrows = math.ceil(citysize / 2)
            ncols = min(citysize, 2)
            dim = np.array([ncols, nrows]) * r
            canvas.create_rectangle(*(p-dim/2), *(p + dim/2),
                                    fill='white', outline='black', width=1)

            # move location to top-left station
            # 1 ->    ()    0 offset from center
            # 2 ->   ()()   0.5 offset ...
            # 3 ->  ()()()  1 offset ...
            # 4 -> ()()()() 1.5 offset ...
            p[0] -= ((ncols-1)/2) * r
            p[1] -= ((nrows-1)/2) * r

        for c in range(citysize):
            station = np.copy(p)
            station[0] += r * int(c % 2)
            station[1] += r * int(c / 2)

            company = self.hex.cities[cidx][c]
            HexWindow.drawStation(canvas, station, r, company)

    def draw(self, canvas):
        if self.hex == None: return

        if self.hex.type != "off-board" or self.hex.label != "":
            canvas.create_polygon(*flatten(self.outline()),
                                  fill=HexWindow.getHexColor(self.hex.type),
                                  width=2, outline='white')

        # compute locations of cities and towns
        stops = {}
        stopsToDraw = self.hex.stops()
        r = self.r / 3 if stopsToDraw >= 2 else 0
        a = self.hex.rotation * math.pi / 3 - math.pi / 3

        for c in range(len(self.hex.cities)):
            stops['city-%d' % c] = self.center() + np.array((math.cos(a), math.sin(a))) * r
            a += 2 * math.pi / stopsToDraw

        for t in range(self.hex.towns):
            stops['town-%d' % t] = self.center() + np.array((math.cos(a), math.sin(a))) * r
            a += 2 * math.pi / stopsToDraw

        # draw connections
        
        for conn in self.hex.connections:
            start = conn[0]
            end = conn[-1]

            if end == "None":
                # off-board locations
                p = self.side(start)
                n = self.normal(start)
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
        cityrad = self.r/2
        townrad = self.r/4
        
        for stop, location in stops.items():
            if 'city' in stop:
                self.drawCity(canvas, location, cityrad, stop)
            elif 'town' in stop:
                HexWindow.drawCircle(canvas, location, townrad, c="black", o="white")
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
                                            fill=HexWindow.getHexColor(level+1))
                    canvas.create_text(*location,
                                       fill='black',
                                       text = rev)
                    location += (20, 0)
        if self.hex.upgradeCost != 0:
            location += (40, 0)
            canvas.create_text(*location,
                               fill='red',
                               text='$%d' % self.hex.upgradeCost,
                               anchor=tkinter.NE)

        canvas.addtag_all("all")
