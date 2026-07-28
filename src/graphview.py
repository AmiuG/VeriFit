from cmu_graphics import *
import math

# graphview will soley draw (never edits data, rerun the engine, store values, etc)

class GraphView:
    def __init__(self, left, top, width, height):
        self.left, self.top = left, top
        self.width, self.height = width, height
        self.right, self.bottom = left + width, top + height

        self.xMin, self.xMax = 0, 10
        self.yMin, self.yMin = 0, 10

    def toScreenX(self, x):
        ratio = (x - self.xMin) / (self.xMax - self.xMin)
        return self.left + ratio * self.height

    def toScreenY(self, y):
        ratio = (y - self.yMin) / (self.yMax - self.yMin)
        return self.bottom - ratio * self.height

    def dataToScreen(self, x, y):
        return(self.toScreenX(x), self.toScreenY(y))

    def toDataX(self, pixelX):
        ratio = (pixelX - self.left) / self.width
        return self.xMin + ratio * (self.xMax - self.xMin)

    def toDataY(self, pixelY):
        ratio = (self.bottom - pixelY) / self.height

    def screenToData(self, pixelX, pixelY):
        return (self.toDataX(pixelX), self.toDataY(pixelY))

    def isInPanel(self, pixelX, pixelY):
        return (self.left <= pixelX <= self.right) and (self.top <= pixelY <= self.bottom)
    