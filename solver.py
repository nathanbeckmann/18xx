#!/usr/bin/python3

# very naive and inefficient brand-and-bound ... probably still fast
# enough at the small scale of 18xx games?
#
# a full-fledged ILP solver like CPLEX would probably be better, if I
# could figure out how to express the problem as integer constraints.

import copy
import company
import collections
import sortedcontainers

class MapSolver:
    def __init__(self, map, useMemo=True):
        self.map = map
        self.recursionDepth = 0
        self.memoize = {}
        self.useMemo = useMemo
        self.explorations = 0
        self.combinations = 0

    def findStartingCities(self, company):
        self.startingCities = []
        
        for r, c, hx in self.map.getHexes():
            for ci, city in enumerate(hx.cities):
                if company.id in city:
                    self.startingCities.append( (r,c,"city-%d" % ci) )
        print ("Starting cities for company %s: %s" % (company.id, self.startingCities))

    # build up a graph representation of the map so we can add and
    # remove edges during exploration
    class Graph:
        def __init__(self):
            self.vertices = {}
            self.edges = {}

    class Vertex:
        def __init__(self, revenue, distance, stop):
            # self.name = name
            self.revenue = revenue
            self.distance = distance
            self.stop = stop
            self.available = [True]

        def __repr__(self):
            return "rev: %s, dist: %s, stop: %s, available: %s" % (self.revenue, self.distance, self.stop, self.available)

    @staticmethod
    def isHexside(loc):
        return isinstance(loc[2], int)
    
    # hexsides are really a single location; update them in the
    # vertex dictionary to use the same object
    @staticmethod
    def canonicalize(loc):
        # always use hexside 0,1,2 so there is a common name for
        # each side of a hexside
        if MapSolver.isHexside(loc):
            delta = {
                0: (0, 0, 0),
                1: (0, 0, 1),
                2: (0, 0, 2),
                3: (1, 0, 0),
                4: (0, -1, 1),
                5: (-1, 0, 2)
                }[loc[2]]
            res = [loc[0] + delta[0], loc[1] + delta[1], delta[2]]
            if delta[0] != 0 and loc[0] % 2 == 0: res[1] -= 1
            return tuple(res)
        else:
            return loc

    def buildGraph(self):
        self.graph = MapSolver.Graph()

        def getDistance(loc):
            # count cities and towns
            return 0 if MapSolver.isHexside(loc) else 1

        def getRevenue(loc):
            # count cities and towns
            if MapSolver.isHexside(loc):
                return 0
            else:
                rev = self.map.getHex(loc[0], loc[1]).revenue
                if isinstance(rev, int):
                    return rev
                elif rev == None:
                    return 0
                else:
                    return rev[self.map.getPhase()]

        def getStop(loc):
            return 0 if MapSolver.isHexside(loc) else 1

        def step(src):
            if isinstance(src[2], int):
                # compute the facing hexside from the destination's
                # perspective
                delta = {
                    0: (-1, 1),
                    1: (0, 1),
                    2: (1, 1),
                    3: (1, 0),
                    4: (0, -1),
                    5: (-1, 0)
                }[src[2]]
                dst = [src[0] + delta[0], src[1] + delta[1], src[2]]
                if delta[0] != 0 and src[0] % 2 == 0: dst[1] -= 1

                # the hexside we connect to is mirrored from the
                # perspective of the destination
                dst[2] += 3
                dst[2] %= 6

                return tuple(dst)
            else:
                return src
            
        def explore(src):
            r,c,loc = src
            hx = self.map.getHex(r,c)
            assert hx != None

            if src not in self.graph.vertices.keys():
                self.graph.vertices[src] = MapSolver.Vertex(getRevenue(src),
                                                       getDistance(src),
                                                       getStop(src))
                self.graph.edges[src] = []
            
                # find what this src connects to on the hex and
                # explore each direction
                for conn in hx.connections:
                    assert len(conn) == 2
                    if loc == conn[1]:
                        next = conn[0]
                    elif loc == conn[0]:
                        next = conn[1]
                    else:
                        continue

                    dst = step((src[0], src[1], next))

                    self.graph.edges[src] += [dst]

                    # # if this is a hexside connection, we need to add
                    # # an edge to the other hexside if one doesn't
                    # # exist...
                    # if isinstance(next,int):
                    #     if dst not in nodes.keys():
                    #         nodes[dst] = [ MapSolver.Node.mirror(dstnode) ]
                    #         print ("Mirror for %s is %s." % (dst, nodes[dst][-1]))
                    #     assert len(nodes[dst]) == 1
                    #     dst = nodes[dst][-1].loc

                    explore(dst)

        for src in self.startingCities:
            explore(src)

        # for src, dsts in sorted([(str(src),dsts) for src,dsts in self.graph.edges.items()]):
        #     print (src, dsts)

        newvertices = {}
        for loc in self.graph.vertices.keys():
            canloc = MapSolver.canonicalize(loc)
            if canloc in self.graph.vertices.keys():
                newvertices[loc] = self.graph.vertices[canloc]
            else:
                newvertices[loc] = self.graph.vertices[loc]
        self.graph.vertices = newvertices

    def solve(self, company):
        # constraints:
        #
        # 1) only N cities per train
        #
        # 2) no shared track
        #
        # 3) cities visited at most once per route
        #
        # 4) routes are connected and contiguous
        #
        # 5) not blocked by stations --- i.e., excluding company's
        # tokens, there must be empty space
        #
        # 6) route contains a company station
        #
        # 7) must connect at least two stops

        print ("Optimizing routes for:", company)
        
        self.findStartingCities(company)

        self.buildGraph()

        routes = self.findAllRoutes(max(company.trains))
        print ("Found %s routes in %s steps:" % (len(routes), self.explorations))
        for r in routes:
            print ("    Revenue: %s, Stops: %s, Hexsides: %s" % (r[0], [ (r,c) for r,c,s in r[2] if isinstance(s,str) ], r[3]))

        revenues, routes = self.findBestRoutes(company.trains, routes)

        print ()
        print ("Best revenue:", revenues)
        print ("Best routes for trains %s:" % company.trains)
        for r in routes:
            print ("    Revenue: %s, Stops: %s, Hexsides: %s" % (r[0], [ (r,c) for r,c,s in r[2] if isinstance(s,str) ], r[3]))
        print ("(Tried %s combinations)" % (self.combinations))

    def log(self, *args):
        return
        print ("".join(["|   "]*self.recursionDepth), *args)

    def findBestRoutes(self, trains, routes):
        # enumerate all combinations of routes, aborting once we know
        # the remaining routes can't possibly do better than the best
        # we've currently found

        bestRevenues = 0
        bestRoutes = []

        def loop(hexsidesUsed, currTrain, remainingTrains, revenuesSoFar, routesSoFar):
            nonlocal bestRevenues, bestRoutes, routes
            
            for r in routes:
                self.combinations += 1
                
                if r[1] > currTrain: continue

                if r[3] & hexsidesUsed != set(): continue

                currRevenues = revenuesSoFar + r[0]
                currRoutes = routesSoFar + [r]

                if currRevenues > bestRevenues:
                    bestRevenues = currRevenues
                    bestRoutes = currRoutes

                if len(remainingTrains) > 0:
                    loop(hexsidesUsed | r[3],
                         remainingTrains[0],
                         remainingTrains[1:],
                         currRevenues,
                         currRoutes)

        if len(trains) > 0:
            loop(set(), trains[0], trains[1:], 0, [])

        return bestRevenues, bestRoutes
        
    def findAllRoutes(self, maxDistance):
        self.recursionDepth += 1
        self.log("findAllRoutes(%s)" % (maxDistance))

        # baseline option is not to run this train at all...
        routes = [ (0, 0, [], set()) ]

        # dictionary indexed by revenue that stores the set of
        # hexsides used by all routes found at that revenue. used for
        # merging.
        hexsidesUsedByRevenue = {}

        # try starting this train at every possible starting city,
        # merge the results
        for city in self.startingCities:
            cityRoutes = self.findAllRoutesFromCity(maxDistance, city)

            # merge --- this ended up getting a little complicated...
            #
            # the basic idea is simple though. we want to keep a
            # sorted list (by revenue) of all unique routes we've
            # found so far. de-dupping the routes requires us to track
            # the set of hexsides used by each route.
            mergedRoutes = []
            i, j = 0, 0
            while i < len(routes) and j < len(cityRoutes):
                if routes[i][0] < cityRoutes[j][0]:
                    next = routes[i]
                    i += 1
                elif routes[i][0] > cityRoutes[j][0]:
                    next = cityRoutes[j]
                    j += 1
                else:
                    # equal revenue; check if we have a duplicate
                    # route, and skip it if so
                    assert cityRoutes[j][0] in hexsidesUsedByRevenue.keys()
                    if tuple(cityRoutes[j][3]) in hexsidesUsedByRevenue[ cityRoutes[j][0] ]:
                        # already have this; skip it
                        next = None
                    else:
                        # new route; add it
                        next = cityRoutes[j]
                    j += 1

                if next != None:
                    mergedRoutes.append(next)
                    if next[0] not in hexsidesUsedByRevenue.keys():
                        hexsidesUsedByRevenue[next[0]] = set()
                    hexsidesUsedByRevenue[ next[0] ].add(tuple(next[3]))

            mergedRoutes += routes[i:]
            mergedRoutes += cityRoutes[j:]
            for r in cityRoutes[j:]:
                if r[0] not in hexsidesUsedByRevenue.keys():
                    hexsidesUsedByRevenue[r[0]] = set()
                hexsidesUsedByRevenue[r[0]].add(tuple(r[3]))
                
            routes = mergedRoutes

        self.recursionDepth -= 1
        return routes

    def findAllRoutesFromCity(self, maxDistance, city):
        self.recursionDepth += 1
        self.log("Exploring up to distance %s from %s." % (maxDistance, city))

        route = [city]
        revenue = self.graph.vertices[city].revenue
        distance = self.graph.vertices[city].distance
        stops = 1
        hexsidesUsed = set()
        routes = sortedcontainers.SortedList()

        def explore():
            self.explorations += 1
            
            nonlocal route, revenue, distance, stops, hexsidesUsed, routes
            self.recursionDepth += 1

            src = route[-1]

            # TODO: THIS ONLY GROWS IN ONE DIRECTION, IT WILL NOT LET
            # US EXPLORE BEFORE AND AFTER A STARTING CITY

            for dst in self.graph.edges[src]:
                dstv = self.graph.vertices[dst]
                self.log("Step:", dst, dstv)

                # TODO: REMOVE AVAILABLE THING. JUST CHECK IF HEXSIDE
                # IS ALREADY IN ROUTE.
                if not dstv.available[0]:
                    self.log("Unavailable.")
                    continue

                if distance + dstv.distance > maxDistance:
                    self.log("Too far.")
                    continue

                # claim this path so it can't be used by any other routes
                route.append(dst)
                revenue += dstv.revenue
                distance += dstv.distance
                stops += dstv.stop
                if MapSolver.isHexside(dst):
                    dstv.available[0] = False
                    candst = MapSolver.canonicalize(dst)
                    hexsidesUsed.add(candst)

                valid = self.isValidRoute(route)
                self.log("Route: %s, rev: %s, dist: %s, stops: %s, valid: %s" % ([route], revenue, distance, stops, valid))
                if valid and stops >= 2 and dstv.revenue > 0:
                    routes.add( (revenue, distance, copy.copy(route), copy.copy(hexsidesUsed)) )
                    
                # now, try to extend the current route by recursing
                if valid:
                    explore()

                # unwind, iterate
                if MapSolver.isHexside(dst):
                    hexsidesUsed.remove(candst)
                    dstv.available[0] = True
                stops -= dstv.stop
                distance -= dstv.distance
                revenue -= dstv.revenue
                route.pop()

            self.recursionDepth -= 1
            return

        explore()
        
        self.recursionDepth -= 1
        return routes
    
    def isValidRoute(self, route):
        counts = collections.Counter(route)
        return max(counts.values()) == 1
