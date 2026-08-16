from cmu_graphics import *
import math

# graphview will soley draw (never edits data, rerun the engine, store values, etc)
borderColor = rgb(205, 205, 205)
axisColor = rgb(55, 55, 55)
pointColor = 'black'
minorGridColor = rgb(241, 241, 241)
majorGridColor = rgb(224, 224, 224)
tickLabelColor = rgb(95, 95, 95)
excludedColor = 'gray'
# the Okabe-Ito palette, chosen so the curves stay tellable-apart for
# colorblind users. The order matches makeAllModels.
curveColors = [rgb(0, 114, 178),    # linear: blue
               rgb(213, 94, 0),     # quadratic: vermillion
               rgb(0, 158, 115),    # cubic: green
               rgb(204, 121, 167),  # exponential: pink
               rgb(230, 159, 0),    # power: orange
               rgb(86, 180, 233),   # logarithmic: sky blue
               rgb(0, 0, 0)]        # flatline: black
extraCurveColor = 'gray'
residualDotColor = rgb(60, 60, 60)
residualStemColor = rgb(200, 200, 200)
outlierColor = rgb(200, 40, 40)
zeroLineColor = rgb(120, 120, 120)

def niceStep(roughStep):
    if roughStep <= 0:
        return 1
    power = math.floor(math.log10(roughStep))
    base = 10 ** power
    for multiple in [1, 2, 5]:
        if roughStep <= multiple * base:
            return multiple * base
    return 10 * base

def tickValuesByStep(low, high, step):
    if step <= 0 or high <= low:
        return []
    firstIndex = math.ceil(low / step)
    lastIndex = math.floor(high / step)
    values = []
    for tickIndex in range(firstIndex, lastIndex+1):
        value = tickIndex * step
        values.append(value)
    return values

def tickValues(low, high, targetCount):
    if high <= low or targetCount < 1:
        return []
    return tickValuesByStep(low, high, niceStep((high-low) / targetCount))

# desmos splits a major step of 2 into quarters, and 1 or 5 into fifths
def minorStep(step):
    power = math.floor(math.log10(step))
    mantissa = round(step / (10 ** power))
    if mantissa == 2:
        return step / 4
    return step / 5

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
    pixelsPerXTick = 50
    pixelsPerYTick = 50
    pointRadius = 4
    curveWidth = 2
    curveStep = 3

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
        return self.left + ratio * self.width

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
        return self.yMin + ratio * (self.yMax - self.yMin)

    def screenToData(self, pixelX, pixelY):
        return (self.toDataX(pixelX), self.toDataY(pixelY))

    # check if the point is in the xy plain
    def isInPanel(self, pixelX, pixelY):
        return (self.left <= pixelX <= self.right) and (self.top <= pixelY <= self.bottom)

    # draw
    def drawBackground(self):
        drawRect(self.left,self.top,self.width,self.height, 
                 fill='white')

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
                pixelX += GraphView.curveStep
                continue
            pixelY = self.toScreenY(y)
            if previousX is not None:
                piece = self.clipSegment(previousX, previousY, pixelX, pixelY)
                if piece is not None:
                    drawLine(piece[0], piece[1], piece[2], piece[3],
                             fill=color, lineWidth=GraphView.curveWidth)
            previousX, previousY = pixelX, pixelY
            pixelX += GraphView.curveStep
    ########################################################################

    ########################################################################
    # written by Claude Opus 5 / Jul 30, 2026
    ########################################################################
    def drawGhostCurve(self, analysisEngine, result, color):
        ghost = analysisEngine.originalModelFor(result)
        if ghost is None:
            return
        previousX, previousY = None, None
        pixelX, dashStep = self.left, 0
        while pixelX <= self.right:
            y = analysisEngine.predictWith(ghost, result.model.usesShiftedX,
                                           self.toDataX(pixelX))
            if y is None:
                previousX, previousY = None, None
                pixelX += GraphView.curveStep
                continue
            pixelY = self.toScreenY(y)
            # every other run of three pixels is skipped, which reads as a dash
            if previousX is not None and dashStep % 6 < 3:
                piece = self.clipSegment(previousX, previousY, pixelX, pixelY)
                if piece is not None:
                    drawLine(piece[0], piece[1], piece[2], piece[3],
                             fill=color, lineWidth=1)
            previousX, previousY = pixelX, pixelY
            pixelX += 1
            dashStep += GraphView.curveStep

    def drawPredictionMarker(self, analysisEngine, x, markerColor):
        pixelX = self.toScreenX(x)
        if not (self.left <= pixelX <= self.right):
            return
        drawLine(pixelX, self.top, pixelX, self.bottom, fill=markerColor,
                 lineWidth=1)
        for result in analysisEngine.results:
            if not result.isVisible:
                continue
            y = analysisEngine.predictAt(result, x)
            if y is None:
                continue
            pixelY = self.toScreenY(y)
            if self.top <= pixelY <= self.bottom:
                drawCircle(pixelX, pixelY, 5, fill=None,
                           border=self.colorFor(result), borderWidth=2)
    ########################################################################

    def colorFor(self, result):
        index = result.colorIndex
        if index is None or index >= len(curveColors):
            return extraCurveColor
        return curveColors[index]

    def drawCurves(self, analysisEngine):
        visible = []
        for result in analysisEngine.results:
            if result.isVisible:
                visible.append(result)
        for i in range(len(visible)-1, -1, -1):
            self.drawCurve(analysisEngine, visible[i], self.colorFor(visible[i]))

    def gridSteps(self):
        xStep = niceStep((self.xMax - self.xMin) /
                         max(1, self.width // GraphView.pixelsPerXTick))
        yStep = niceStep((self.yMax - self.yMin) /
                         max(1, self.height // GraphView.pixelsPerYTick))
        return (xStep, yStep)

    def drawGridAndTicks(self):
        xStep, yStep = self.gridSteps()

        # the faint in-between lines go down first, then the main grid on
        # top of them, the way desmos layers its paper
        for x in tickValuesByStep(self.xMin, self.xMax, minorStep(xStep)):
            pixelX = self.toScreenX(x)
            drawLine(pixelX, self.top, pixelX, self.bottom,
                     fill=minorGridColor, lineWidth=1)
        for y in tickValuesByStep(self.yMin, self.yMax, minorStep(yStep)):
            pixelY = self.toScreenY(y)
            drawLine(self.left, pixelY, self.right, pixelY,
                     fill=minorGridColor, lineWidth=1)
        for x in tickValuesByStep(self.xMin, self.xMax, xStep):
            pixelX = self.toScreenX(x)
            drawLine(pixelX, self.top, pixelX, self.bottom,
                     fill=majorGridColor, lineWidth=1)
        for y in tickValuesByStep(self.yMin, self.yMax, yStep):
            pixelY = self.toScreenY(y)
            drawLine(self.left, pixelY, self.right, pixelY,
                     fill=majorGridColor, lineWidth=1)

    # tick labels hug the axes like desmos, and slide to the nearest edge
    # of the panel when an axis is out of view
    def drawTickLabels(self):
        xStep, yStep = self.gridSteps()

        if self.yMin <= 0 <= self.yMax:
            labelY = min(self.toScreenY(0) + 11, self.bottom - 10)
        elif self.yMin > 0:
            labelY = self.bottom - 10
        else:
            labelY = self.top + 10
        for x in tickValuesByStep(self.xMin, self.xMax, xStep):
            if x == 0:
                continue
            pixelX = self.toScreenX(x)
            text = formatTick(x, xStep)
            halfWidth = 3 * len(text) + 2
            drawRect(pixelX - halfWidth, labelY - 6, 2 * halfWidth, 12,
                     fill='white', opacity=75)
            drawLabel(text, pixelX, labelY, size=10, fill=tickLabelColor)

        if self.xMin <= 0 <= self.xMax:
            labelX = max(self.toScreenX(0) - 5, self.left + 38)
            labelX = min(labelX, self.right - 6)
        elif self.xMin > 0:
            labelX = self.left + 38
        else:
            labelX = self.right - 6
        for y in tickValuesByStep(self.yMin, self.yMax, yStep):
            if y == 0:
                continue
            pixelY = self.toScreenY(y)
            text = formatTick(y, yStep)
            width = 6 * len(text) + 4
            drawRect(labelX - width, pixelY - 6, width, 12, fill='white',
                     opacity=75)
            drawLabel(text, labelX, pixelY, size=10, align='right',
                      fill=tickLabelColor)

    def drawAxisLines(self):
        if self.xMin <= 0 <= self.xMax:
            pixelX = self.toScreenX(0)
            drawLine(pixelX, self.top, pixelX, self.bottom, fill=axisColor)
        if self.yMin <= 0 <= self.yMax:
            pixelY = self.toScreenY(0)
            drawLine(self.left, pixelY, self.right, pixelY, fill=axisColor)

    def drawBorder(self):
        drawRect(self.left, self.top, self.width, self.height,
                 fill=None, border=borderColor)

    def drawEmptyMessage(self):
        drawLabel('Add at least 2 points to see a fit.',
                  self.left + self.width / 2, self.top + self.height / 2,
                  size=14, fill=excludedColor)


    def draw(self, data, analysisEngine = None):
        self.drawBackground()
        self.drawGridAndTicks()
        self.drawAxisLines()
        if analysisEngine is not None and len(analysisEngine.results) > 0:
            self.drawCurves(analysisEngine)
        self.drawPoints(data)
        # labels come after the curves so they stay readable on top
        self.drawTickLabels()
        self.drawBorder()
        if data.getActiveCount() < 2:
            self.drawEmptyMessage()


class ResidualPlot:
    dotRadius = 3

    def __init__(self, left, top, width, height):
        self.left, self.top = left, top
        self.width, self.height = width, height
        self.right, self.bottom = left+width, top+height
        self.middle = top + height/2

    def halfRange(self, residuals):
        biggest = 0
        for residual in residuals:
            if abs(residual) > biggest:
                biggest = abs(residual)
        if biggest <= 0:
            return 1
        return biggest * 1.25

    def toScreenX(self, x, xMin, xMax):
        if xMax <= xMin:
            return self.left
        return self.left + (x - xMin) / (xMax - xMin) * self.width

    def toScreenY(self, residual, halfRange):
        pixelY = self.middle - (residual/halfRange)*(self.height/2)
        if pixelY < self.top:
            pixelY = self.top
        if pixelY > self.bottom:
            pixelY = self.bottom
        return pixelY

    def drawEmpty(self, message):
        drawRect(self.left,self.top,self.width,self.height, fill='white',
                 border=borderColor)
        drawLabel(message,self.left + self.width/2,self.middle, size=10,
                  fill=excludedColor)

    def draw(self, result, x_coords, xMin, xMax, outlierIndex=None):
        if result is None or result.residuals is None:
            self.drawEmpty('no residuals to show')
            return

        residuals = result.residuals
        drawRect(self.left,self.top,self.width,self.height, fill='white')
        halfRange = self.halfRange(residuals)

        drawLine(self.left,self.middle,self.right,self.middle, fill=zeroLineColor)
        for i in range(min(len(residuals), len(x_coords))):
            pixelX = self.toScreenX(x_coords[i], xMin, xMax)
            if not (self.left <= pixelX <= self.right):
                continue
            pixelY = self.toScreenY(residuals[i], halfRange)
            isOutlier = (outlierIndex is not None and i == outlierIndex)
            drawLine(pixelX,self.middle,pixelX,pixelY, fill=residualStemColor)
            drawCircle(pixelX, pixelY, ResidualPlot.dotRadius, 
                    fill=outlierColor if isOutlier else residualDotColor)

        drawLabel(f'residuals: {result.model.name}',self.left+4,self.top+9, size=9,
                    align='left', fill=excludedColor)
        drawLabel(f'+{formatTick(halfRange, halfRange/4)}',self.left-6,self.top+8, size=9,
                    align='right', fill=excludedColor)
        drawLabel('0',self.left-6,self.middle, size=9, align='right', fill=excludedColor)
        drawRect(self.left,self.top,self.width,self.height, fill=None, border=borderColor)