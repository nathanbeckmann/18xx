#!/usr/bin/python3

import cvxpy
import numpy as np

class MapSolver:
    def __init__(self, map):
        self.map = map

    def solve(self):
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
        
        visited = cvxpy.Bool(len(cities))

        constraints = 

        goal = cvxpy.Maximize(visited * revenues)

        problem = cvxpy.Problem(goal, constraints)
        problem.solve(solver=cvxpy.GLPK_MI)
