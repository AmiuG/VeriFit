# SIMPLE DEMO AT THIS POINT
# this simply ranks models based on cross-validated RMSE

from cmu_graphics import *
import models
import stats

windowWidth = 940
windowHeight = 640

graphLeft = 200
graphRight = 600
graphTop = 80
graphBottom = 600

xMin, xMax = 0, 10
yMin, yMax = 0, 10

curveColors = ['blue', 'green', 'orange', 'purple', 'red', 'brown']

def onAppStart(app):
    app.width = windowWidth
    app.height = windowHeight
    app.points = []
    app.results = []

# fit and rank all models that can handle the current points
def fit(app):
    app.results = []
    if len(app.points) < 2:
        return
    x_coords = [p[0] for p in app.points]
    y_coords = [p[1] for p in app.points]
    # run each models for given x coordinates and y coordinates
    for model in models.makeAllModels():
        works, message = model.canFit(x_coords, y_coords)
        if not works:
            continue
        if not model.fit(x_coords, y_coords):
            continue
        app.results.append([model, stats.crossValidatedRmse(model, x_coords, y_coords)])
    # learned how to sort list with None without crashing https://docs.python.org/3/howto/sorting.html
    app.results.sort(key=lambda r: r[1] if r[1] is not None else 10 ** 9)

def toScreen(x, y):
    px = graphLeft + (x - xMin) / (xMax - xMin) * (graphRight - graphLeft)
    py = graphBottom - (y - yMin) / (yMax - yMin) * (graphBottom - graphTop)
    return px, py

def toData(px, py):
    x = xMin + (px - graphLeft) / (graphRight - graphLeft) * (xMax - xMin)
    y = yMin + (graphBottom - py) / (graphBottom - graphTop) * (yMax - yMin)
    return x, y

def inGraph(x, y):
    return (graphLeft <= x <= graphRight) and (graphTop <= y <= graphBottom)

def onMousePress(app, mouseX, mouseY):
    if inGraph(mouseX, mouseY):
        x, y = toData(mouseX, mouseY)
        app.points.append((x,y))
        fit(app)

def onKeyPress(app, key):
    if key == 'c':
        app.points = []
        fit(app)

def drawCurve(model, color):
    prevX, prevY = None, None
    steps = 100
    for i in range(steps + 1):
        x = xMin + (xMax - xMin) * i / steps
        y = stats.safePredict(model, x)
        if y is None:
            prevX = None
            continue
        px, py = toScreen(x, y)
        if not inGraph(px, py):
            prevX = None
            continue
        if prevX is not None:
            drawLine(prevX, prevY, px, py, fill=color, lineWidth=2)
        prevX, prevY = px, py

def redrawAll(app):
    drawLabel('Click in the graph to add points (c = clear)',
              20, 20, size=16, bold=True, align='left')
    drawRect(graphLeft, graphTop, graphRight - graphLeft, graphBottom - graphTop,
             fill='white', border='gray')

    # graph top 3 graphs
    for i in range(min(3, len(app.results))):
        drawCurve(app.results[i][0], curveColors[i])
    # draw points
    for p in app.points:
        px, py = toScreen(p[0], p[1])
        drawCircle(px, py, 4, fill='black')
    # ranked list on the right
    drawLabel('Ranked models', 640, 55, size=14, bold=True, align='left')
    if len(app.results) < 2:
        drawLabel('Add at least 2 points.', 640, 80, size=12, align='left')
    else:
        for i in range(len(app.results)):
            model = app.results[i][0]
            cv = app.results[i][1]
            if cv is None:
                cvText = 'n/a'
            else:
                cvText = str(cv)
            color = curveColors[i] if i < 3 else 'black'
            drawLabel(str(i + 1) + '. ' + model.name + '   cv=' + cvText,
                        640, 80 + i * 45, size=12, align='left', fill=color)
            drawLabel(model.getEquation(), 640, 80 + i * 45 + 15,
                        size=10, align='left', fill='gray')

def main():
    runApp()

main()