#!/usr/bin/python3

import map
import sys
import pickle

if len(sys.argv) > 1:
    with open(sys.argv[1], 'rb') as f:
        m = pickle.load(f)
else:
    m = map.Map()
    m.load("1822.map")

mw = map.MapWindow(m)
mw.run()
