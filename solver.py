#!/usr/bin/python3

# very naive and inefficient brand-and-bound ... probably still fast
# enough at the small scale of 18xx games?
#
# a full-fledged ILP solver like CPLEX would probably be better, if I
# could figure out how to express the problem as integer constraints.

import copy
import company
import collections

class MapSolver:
    def __init__(self, map):
        self.map = map
        self.recursionDepth = 0

    def getStartingCities(self, company):
        startingCities = []
        
        for r, c, hx in self.map.getHexes():
            for ci, city in enumerate(hx.cities):
                if company.id in city:
                    startingCities.append( (r,c,"city-%d" % ci) )
        print ("Starting cities for company %s: %s" % (company.id, startingCities))
        return startingCities

    # build up a graph representation of the map so we can add and
    # remove edges during exploration
    class Node:
        def __init__(self, loc, solver):
            self.loc = loc
            self.available = None
            self.revenue = solver.getRevenue(loc)
            self.distance = solver.getDistance(loc)

        def __repr__(self):
            return "(%s, %s, %s, %s)" % (self.loc, self.available, self.revenue, self.distance)
    
    def buildGraph(self, startingCities):
        nodes = {}

        def step(src, next):
            if isinstance(next,int):
                # adjust row/col
                delta = {
                    0: (-1, 1),
                    1: (0, 1),
                    2: (1, 1),
                    3: (1, 0),
                    4: (0, -1),
                    5: (-1, 0)
                }[next]
                dst = [src[0] + delta[0], src[1] + delta[1]]
                if delta[0] != 0 and src[0] % 2 == 0: dst[1] -= 1

                # the hexside we connect to is mirrored from the
                # perspective of the destination
                next += 3
                next %= 6
            else:
                # another location in the same tile
                dst = src
            return (dst[0], dst[1], next)

        def explore(src):
            # print (src)
            r,c,loc = src

            if src not in nodes.keys():
                nodes[src] = []
            
                hx = self.map.getHex(r,c)
                assert hx != None
                
                for conn in hx.connections:
                    assert len(conn) == 2
                    if loc == conn[1]:
                        next = conn[0]
                    elif loc == conn[0]:
                        next = conn[1]
                    else:
                        continue
                    
                    dst = step(src, next)
                    nodes[src] += [ self.Node(dst, self) ]
                    explore(dst)

        for src in startingCities:
            explore(src)

        # allocate shared 'available' boolean values for edges in each
        # direction
        for src, dsts in nodes.items():
            for dst in dsts:
                if dst.available == None:
                    dst.available = [True]
                    # find the corresponding edge pointing in the
                    # other direction
                    for src2 in nodes[dst.loc]:
                        if src2.loc == src:
                            src2.available = dst.available

        print ("Graph:", nodes)

        # # de-ref 'pointers' to speed things up?
        # for src, dsts in nodes.items():
        #     for di, dst in enumerate(dsts):
        #         assert dst in nodes.keys()
        #         dsts[di] = nodes[dst]

        return nodes

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
        
        startingCities = self.getStartingCities(company)

        graph = self.buildGraph(startingCities)

        routes, revenues = self.findBestRoutes(company.trains, graph, startingCities)

        print ("Found:", routes, revenues)

    def log(self, *args):
        return
        print ("".join(["    "]*self.recursionDepth), *args)
        
    # absurdly slow branch-and-bound ... take one step in the first
    # train, solve for all the other trains ... repeat.
    #
    # we should be able to do some heavy memoization here ... remember
    # what track was used by a given optimal solution and only
    # re-compute if it has been taken.
    def findBestRoutes(self, trains, graph, startingCities):
        if trains == []: return [], 0
        self.recursionDepth += 1

        # baseline option is not to run this train at all...
        self.log("Skipping %s-train." % trains[0])
        bestRoutes, bestRevenues = self.findBestRoutes(trains[1:], graph, startingCities)
        bestRoutes = [[]] + bestRoutes

        # try starting this train at every possible starting city
        for city in startingCities:
            cityRoutes, cityRevenues = self.findBestRoutesFromCity(trains[0], city,
                                                                   trains[1:], graph,
                                                                   startingCities)
            
            if cityRevenues > bestRevenues:
                bestRevenues = cityRevenues
                bestRoutes = cityRoutes

        self.recursionDepth -= 1
        return bestRoutes, bestRevenues

    def findBestRoutesFromCity(self, train, city, trains, graph, startingCities):
        # self.recursionDepth -= 1
        self.log("Exploring %s-train from %s." % (train, city))
        
        # can only do a single step at a time --- need to give the
        # other trains a chance too!
        route = [city]
        revenue = self.map.getHex(city[0],city[1]).revenue
        distance = self.getDistance(city)
        stops = 1

        bestRoutes = [[]]
        bestRevenues = 0

        def explore():
            nonlocal route, revenue, distance, stops, bestRoutes, bestRevenues
            if distance == train: return
            self.recursionDepth += 1

            src = route[-1]

            for dst in graph[src]:
                if not dst.available[0]: continue

                # claim this path so it can't be used by any other routes
                route.append(dst.loc)
                revenue += dst.revenue
                distance += dst.distance
                stops += 1 if isinstance(dst.loc[2], str) else 0
                dst.available[0] = False

                # solve for best routes for other trains
                self.log("Route:", [route], revenue, distance, stops)
                
                if self.isValidRoute(route):
                    # only explore other routes if this one has two
                    # stops, otherwise its like we didn't run this
                    # train at all (which has already been explored
                    # above)
                    if stops >= 2:
                        otherRoutes, otherRevenues = \
                            self.findBestRoutes(trains, graph, startingCities)

                        revenues = revenue + otherRevenues
                        if revenues > bestRevenues:
                            bestRevenues = revenues
                            bestRoutes = [copy.copy(route)] + otherRoutes
                            self.log("**** Best route!", bestRoutes, bestRevenues)

                    # now, try to extend the current route by recursing
                    explore()

                # unwind, iterate
                dst.available[0] = True
                stops -= 1 if isinstance(dst.loc[2], str) else 0
                distance -= dst.distance
                revenue -= dst.revenue
                route.pop()

            self.recursionDepth -= 1
            return

        explore()

        # self.recursionDepth += 1
        return bestRoutes, bestRevenues

    # def findBestRouteFromCity(train, routes, city):

    #     def explore(stopsRemaining, route, revenue):
    #         if stopsRemaining == 0: return route, revenue

    #         if not isRouteValid(route):
    #             return route, -1

    #         r,c,src = route[-1]
    #         hx = self.map.getHex(r,c)

    #         bestRoute = route
    #         bestRevenue = revenue

    #         for step in hx.connectsTo[src]:
    #             # where does this dst take us?
    #             if isinstance(step,int):
    #                 delta = {
    #                     0: (-1, 1),
    #                     1: (0, 1),
    #                     2: (1, 1),
    #                     3: (1, 0),
    #                     4: (0, -1),
    #                     5: (-1, 0)
    #                 }[step]
    #                 dst = (r + delta[0], c + delta[1])
    #             else:
    #                 # another location in the same tile
    #                 dst = (r, c)

    #             dstStopsRemaining = self.getStopsRemaining(src, step, dst, stopsRemaining)
    #             stepRevenue = self.getRevenue(src, step, dst)
                    
    #             dstRoute, dstRevenue = explore(dstStopsRemaining,
    #                                            route + [ (*dst, step) ],
    #                                            revenue + stepRevenue)

    #             if dstRevenue > bestRevenue:
    #                 bestRevenue = dstRevenue
    #                 bestRoute = dstRoute

    #         return bestRoute, bestRevenue

    #     return explore(train - 1, [city])

    def isValidRoute(self, route):
        counts = collections.Counter(route)
        return max(counts.values()) == 1

    def getDistance(self, loc):
        # count cities and towns
        return 1 if isinstance(loc[2], str) else 0

    def getRevenue(self, loc):
        # count cities and towns
        if isinstance(loc[2], str):
            rev = self.map.getHex(loc[0], loc[1]).revenue
            if isinstance(rev, int):
                return rev
            else:
                return rev[self.map.getPhase()]
        else:
            return 0
