#!/usr/bin/python3

import map

m = map.Map()
m.load("1817.map")

mw = map.MapWindow(m)
mw.run()
