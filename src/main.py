# SIMPLE DEMO AT THIS POINT

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

