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
        works, message = m.canFit(x_coords, y_coords)
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

