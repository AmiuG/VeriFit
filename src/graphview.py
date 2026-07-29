from cmu_graphics import *
import math

# graphview will soley draw (never edits data, rerun the engine, store values, etc)
borderColor = 'black'
axisColor = 'black'
pointColor = 'black'
excludedColor = 'gray'
curveColors = ['blue', 'red', 'green', 'purple', 'green', 'brown', 'black']
extraCurveColor = 'gray'

def niceStep(roughStep):
    if roughStep <= 0:
        return 1
    power = math.floor(math.log10(roughStep))
    base = 10 ** power
    for multiple in [1, 2, 5]:
        if roughStep <= multiple * base:
            return multiple * base
    return 10 * base

def tickValues(low, high, targetCount):
    if high <= low or targetCount < 1:
        return []
    step = niceStep((high-low) / targetCount)
    firstIndex = math.ceil(low / step)
    lastIndex = math.floor(high / step)
    values = []
    for tickIndex in range(firstIndex, lastIndex+1):
        value = tickIndex * step
        values.append(value)
    return value

########################################################################
# written by Claude Opus 5 / Jul 29, 2026
########################################################################
def formatTick(value, step):
    decimals = 0
    if step < 1:
        decimals = int(math.ceil(-math.log10(step)))
    text = f'{value:.{decimals}f}'
    # '-0' happens when a tiny negative rounds to zero
    if text.startswith('-') and float(text) == 0:
        text = text[1:]
    return text
########################################################################

def padRange(low, high):
    if low == high:
        # one point, or a column of identical values, has no width to pad.
        # invent a window so the point lands in the middle instead of on an edge.
        size = abs(low) * 0.1 if low != 0 else 1
        return (low - size, high + size)
    margin = (high - low) * 0.08
    return (low - margin, high + margin)

class GraphView:
    pointRadius = 4

    def __init__(self, left, top, width, height):
        self.left, self.top = left, top
        self.width, self.height = width, height
        self.right, self.bottom = left + width, top + height

        self.xMin, self.xMax = 0, 10
        self.yMin, self.yMax = 0, 10

    def setWindow(self, xMin, xMax, yMin, yMax):
        # a zero-width window would divide by zero in every conversion below
        if xMax <= xMin:
            xMin, xMax = padRange(xMin, xMin)
        if yMax <= yMin:
            yMin, yMax = padRange(yMin, yMin)
        self.xMin, self.xMax = xMin, xMax
        self.yMin, self.yMax = yMin, yMax
 
    # frames the window around the dataset. Always uses the raw x-values,
    # because the user's coordinates are the only ones that go on screen.
    def fitToDataset(self, data):
        xRange, yRange = data.getRawXRange(), data.getYRange()
        if xRange is None or yRange is None:
            self.setWindow(0, 10, 0, 10)
            return
        xLow, xHigh = padRange(xRange[0], xRange[1])
        yLow, yHigh = padRange(yRange[0], yRange[1])
        self.setWindow(xLow, xHigh, yLow, yHigh)

    # convert coordinate
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

    # check if the point is in the xy plain
    def isInPanel(self, pixelX, pixelY):
        return (self.left <= pixelX <= self.right) and (self.top <= pixelY <= self.bottom)

    # draw
    def drawBackground(self):
        drawRect(self.left,self.top,self.width,self.height, 
                 fill='white', border=borderColor)

    def drawPoints(self, data):
        for point in data.points:
            pixelX, pixelY = self.dataToScreen(point.x, point.y)
            if not self.isInPanel(pixelX, pixelY):
                continue
            if point.isExcluded:
                drawCircle(pixelX,pixelY,GraphView.pointRadius, fill=None, 
                           border=excludedColor, borderWidth=2)
            else:
                drawCircle(pixelX,pixelY,GraphView.pointRadius, fill=pointColor)

    ########################################################################
    # written by Claude Opus 5 / Jul 29, 2026
    ########################################################################
    def clipSegment(self, x1, y1, x2, y2):
        if y1 == y2:
            if self.top <= y1 <= self.bottom:
                return (x1, y1, x2, y2)
            return None
        # t runs from 0 at the first end to 1 at the second. Find the t values
        # where the segment crosses the top and bottom edges.
        tTop = (self.top - y1) / (y2 - y1)
        tBottom = (self.bottom - y1) / (y2 - y1)
        tLow, tHigh = min(tTop, tBottom), max(tTop, tBottom)
        # keep only the part that is both inside the panel and on the segment
        tStart, tEnd = max(0.0, tLow), min(1.0, tHigh)
        if tStart > tEnd:
            return None
        return (x1 + tStart * (x2 - x1), y1 + tStart * (y2 - y1),
                x1 + tEnd * (x2 - x1), y1 + tEnd * (y2 - y1))
    
    def drawCurve(self, analysisEngine, result, color):
        previousX, previousY = None, None
        pixelX = self.left
        while pixelX <= self.right:
            x = self.toDataX(pixelX)
            # predictAt converts x into whichever coordinates this model was
            # fitted in, so this file never has to know about the x-offset
            y = analysisEngine.predictAt(result, x)
            if y is None:
                # the model has no value here (a power model at x <= 0, or an
                # overflow), so the line breaks rather than jumping across
                previousX, previousY = None, None
                pixelX += 1
                continue
            pixelY = self.toScreenY(y)
            if previousX is not None:
                piece = self.clipSegment(previousX, previousY, pixelX, pixelY)
                if piece is not None:
                    drawLine(piece[0], piece[1], piece[2], piece[3],
                             fill=color, lineWidth=GraphView.curveWidth)
            previousX, previousY = pixelX, pixelY
            pixelX += 1
    ########################################################################

    def colorFor(self, result):
        index = result.colorIndex
        if index is None or index >= len(curveColors):
            return extraCurveColor
        return curveColors[index]

    def drawCurves(self, analysisEngine):
        visible = []
        for result in analysisEngine.result:
            if result.isVisible:
                visible.append(result)
        for i in range(len(visible)-1, -1, -1):
            self.drawCurve(analysisEngine, visible[i], self.colorFor(visible[i]))

    def drawEmptyMessage(self):
        drawLabel('Add at least 2 points to see a fit.',
                  self.left + self.width / 2, self.top + self.height / 2,
                  size=14, fill=excludedColor)