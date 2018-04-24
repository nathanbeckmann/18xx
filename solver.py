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
    def __init__(self, map):
        self.map = map
        self.recursionDepth = 0
        self.memoize = {}
        self.explorations = 0

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

        routes, revenues = self.findBestRoutes(tuple(company.trains), set())

        print ("Found:", routes, revenues)
        print ("In %s explorations" % self.explorations)

    def log(self, *args):
        # return
        print ("".join(["    "]*self.recursionDepth), *args)

    # absurdly slow branch-and-bound ... take one step in the first
    # train, solve for all the other trains ... repeat.
    #
    # memoization strategy:
    # 
    # to avoid repeating the same thing over and over and over... we
    # record the hexsides used by the best routes returned.
    #
    # then we pass in the hexside constraints from other routes when
    # findBestRoutes is called.
    #
    # if the hexsides constraints are a superset of prior constraints
    # AND they do not overlap with any used in the best routes, then
    # we can safely return the previous result.
    #
    # if they are not a superset, then we need to recompute the best
    # route to be sure we aren't missing any opportunities.
    #
    # if they overlap with the prior result, then we obviously need to
    # recompute because that result isn't feasible.
    #
    # finally, if the new result is identical to a previous result,
    # then we scan over the memoized results and remove any
    # "duplicates" whose constraints are a superset of the new
    # constraints.
    #
    # todo: will the memoization list itself become unreasonable
    # large?
    class Memo:
        def __init__(self, routes, revenues, hexsideConstraints, hexsidesUsed):
            self.routes = routes
            self.revenues = revenues
            self.hexsideConstraints = hexsideConstraints
            self.hexsidesUsed = hexsidesUsed

        def __gt__(self, that):
            return self.revenues < that.revenues

        def __repr__(self):
            return "(rev: %s, rte: %s, used: %s, cnst: %s)" % (self.revenues, self.routes, self.hexsidesUsed, self.hexsideConstraints)

    def checkMemo(self, memokey, hexsideConstraints):
        # see if we can memoize this call...
        if memokey in self.memoize:
            memos = self.memoize[memokey]
            for memo in memos:
                if hexsideConstraints >= memo.hexsideConstraints and \
                   hexsideConstraints & memo.hexsidesUsed == set():
                    self.log("Memoized! Current constraints: %s, Memo constraints: %s, Memo hexsides: %s"\
                             % (hexsideConstraints, memo.hexsideConstraints, memo.hexsidesUsed))
                    return memo.routes, memo.revenues
                
        return None

    def updateMemo(self, memokey, bestRoutes, bestRevenues, hexsideConstraints):
        if not self.useMemo: return
        
        # memoize result and deduplicate
        if memokey not in self.memoize:
            self.memoize[ memokey ] = sortedcontainers.SortedList()

        hexsidesUsed = set()
        for route in bestRoutes:
            for loc in route:
                if MapSolver.isHexside(loc):
                    hexsidesUsed.add(MapSolver.canonicalize(loc))

        memo = MapSolver.Memo(bestRoutes, bestRevenues,
                              copy.copy(hexsideConstraints), hexsidesUsed)
        memos = self.memoize[memokey]

        i = memos.bisect_left(memo)
        self.log("Deduping from", i, "to", len(memos))
        while i < len(memos):
            memo2 = memos[i]
            self.log("Considering", i, memo2)
            pruned = False
            
            # because it is a sorted list, once we see a memo with
            # worse revenue, we can stop looking
            if memo2.revenues < bestRevenues:
                break
            # if this other memo is more restrictive and returns
            # exactly the same result, delete it
            elif memo2.revenues == bestRevenues:

                if memo2.hexsidesUsed == memo.hexsidesUsed and \
                   memo2.hexsideConstraints >= memo.hexsideConstraints:
                    self.log("Pruned over-restrictive memo", memos, i)
                    del memos[i]
                    pruned = True

                # # not sure we need this and it seems risky to get
                # # rid of a less-constrained solution...
                # elif memo2.hexsidesUsed >= memo.hexsides and \
                #      memo2.hexsideConstraints <= memo.hexsideConstraints:
                #     self.log("Pruned wasteful memo", memos, i)
                #     del memos[i]
                #     pruned = True
                
            # (we're doing weird c++ iterator because the del
            # implicitly increments i)
            if not pruned: i += 1

        memos.add(memo)
        self.log("Added memo: %s (%s total)" % (memo, len(memos)))
    
    def findBestRoutes(self, trains, hexsideConstraints):
        if len(trains) == 0: return [], 0
        self.recursionDepth += 1

        memoResult = self.checkMemo(trains, hexsideConstraints)
        if memoResult: return memoResult
        
        # baseline option is not to run this train at all...
        self.log("Skipping %s-train." % trains[0])
        bestRoutes, bestRevenues = \
            self.findBestRoutes(trains[1:], hexsideConstraints)
        bestRoutes = [[]] + bestRoutes

        # try starting this train at every possible starting city
        for city in self.startingCities:
            cityRoutes, cityRevenues = \
                self.findBestRoutesFromCity(trains[0], city, trains[1:], hexsideConstraints)
            
            if cityRevenues > bestRevenues:
                bestRevenues = cityRevenues
                bestRoutes = cityRoutes

        self.updateMemo(trains, bestRoutes, bestRevenues, hexsideConstraints)
        
        self.recursionDepth -= 1
        return bestRoutes, bestRevenues

    def findBestRoutesFromCity(self, train, city, trains, hexsideConstraints):
        # self.recursionDepth -= 1
        self.log("Exploring %s-train from %s." % (train, city))

        memoResult = self.checkMemo((train,city,trains), hexsideConstraints)
        if memoResult: return memoResult

        # can only do a single step at a time --- need to give the
        # other trains a chance too!
        route = [city]
        revenue = self.graph.vertices[city].revenue
        distance = self.graph.vertices[city].distance
        stops = 1

        bestRoutes = [[]]
        bestRevenues = 0

        def explore():
            self.explorations += 1
            
            nonlocal route, revenue, distance, stops, bestRoutes, bestRevenues
            if distance == train: return
            self.recursionDepth += 1

            src = route[-1]

            # TODO: THIS ONLY GROWS IN ONE DIRECTION, IT WILL NOT LET
            # US EXPLORE BEFORE AND AFTER A STARTING CITY

            for dst in self.graph.edges[src]:
                dstv = self.graph.vertices[dst]
                self.log("Step:", dst, dstv)
                if not dstv.available[0]:
                    self.log("Unavailable.")
                    continue

                # claim this path so it can't be used by any other routes
                route.append(dst)
                revenue += dstv.revenue
                distance += dstv.distance
                stops += dstv.stop
                if MapSolver.isHexside(dst): dstv.available[0] = False

                addConstraint = False
                if MapSolver.isHexside(dst):
                    candst = MapSolver.canonicalize(dst)
                    if candst not in hexsideConstraints:
                        hexsideConstraints.add(candst)
                        addConstraint = True

                # solve for best routes for other trains
                self.log("Route:", [route], revenue, distance, stops)
                
                if self.isValidRoute(route):
                    # only explore other routes if this one has two
                    # stops, otherwise its like we didn't run this
                    # train at all (which has already been explored
                    # above)
                    if stops >= 2:
                        otherRoutes, otherRevenues = \
                            self.findBestRoutes(trains, hexsideConstraints)

                        revenues = revenue + otherRevenues
                        if revenues > bestRevenues:
                            bestRevenues = revenues
                            bestRoutes = [copy.copy(route)] + otherRoutes
                            self.log("**** Best route!", bestRoutes, bestRevenues)

                    # now, try to extend the current route by recursing
                    explore()

                # unwind, iterate
                if addConstraint: hexsideConstraints.remove(candst)
                dstv.available[0] = True
                stops -= dstv.stop
                distance -= dstv.distance
                revenue -= dstv.revenue
                route.pop()

            self.recursionDepth -= 1
            return

        explore()

        self.updateMemo((train,city,trains), bestRoutes, bestRevenues, hexsideConstraints)
        
        # self.recursionDepth += 1
        return bestRoutes, bestRevenues

    def isValidRoute(self, route):
        counts = collections.Counter(route)
        return max(counts.values()) == 1
