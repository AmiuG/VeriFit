from cmu_graphics import *
import math

# graphview will soley draw (never edits data, rerun the engine, store values, etc)

class GraphView:
    def __init__(self, left, top, width, height):
        self.left, self.top = left, top
        self.width, self.height = width, height
        self.right, self.bottom - left + width, top + height

        self.xMin, self.xMax = 0, 10
        self.yMin, self.yMin = 0, 10

    