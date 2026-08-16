# bridge.py
#
# The layer between the browser and the analysis engine. The browser
# cannot reach into Python objects comfortably, so everything crosses
# this boundary as JSON: the page sends a list of points, and gets back
# finished answers.
#
# Nothing about drawing lives here, and nothing about the browser lives
# in the engine. The page never has to know that some models are fitted
# on shifted x values or in log space, because the curve it draws is
# computed on this side by the same code the desktop app uses.
#
# This file is only used by the website. The desktop app never imports it.

import json
import math

import dataset
import models
import engine


# JSON has no way to write infinity or nan, and a score that blew up is
# not a score, so those become null and the page prints them as n/a.
def safeNumber(value):
    if value is None:
        return None
    if not math.isfinite(value):
        return None
    return value


def safeList(values):
    if values is None:
        return []
    cleaned = []
    for value in values:
        cleaned.append(safeNumber(value))
    return cleaned


# One engine lives for the whole visit. Keeping it means the show and
# hide choices and the fixed curve colours survive every refit, exactly
# as they do in the desktop app.
class Session:
    def __init__(self):
        self.engine = engine.AnalysisEngine(dataset.Dataset(),
                                            models.makeAllModels())

    def setPoints(self, points):
        x_coords, y_coords = [], []
        for point in points:
            x_coords.append(point['x'])
            y_coords.append(point['y'])
        data = dataset.Dataset(x_coords, y_coords)
        for i in range(len(points)):
            if points[i].get('excluded', False):
                data.points[i].isExcluded = True
        # exclusions change which points are active, so the offset that
        # keeps big x values well behaved has to be worked out again
        data.updateOffset()
        self.engine.dataset = data
        self.engine.analyze()

    def resultFor(self, name):
        for result in self.engine.results:
            if result.model.name == name:
                return result
        return None


session = Session()


def describeResult(result):
    return {
        'name': result.model.name,
        'equation': result.getEquation(),
        'paramCount': result.model.paramCount,
        'cvRmse': safeNumber(result.cvRmse),
        'trainRmse': safeNumber(result.trainRmse),
        'r2': safeNumber(result.r2),
        'aicc': safeNumber(result.aicc),
        'weight': safeNumber(result.akaikeWeight),
        'colorIndex': result.colorIndex,
        'isVisible': result.isVisible,
        'isAdjusted': result.isAdjusted(),
        'outlierIndex': result.outlierIndex,
        'residuals': safeList(result.residuals),
        'warnings': list(result.interpretations),
    }


def describe():
    data = session.engine.dataset
    unavailable = []
    for name, reason in session.engine.unavailable:
        unavailable.append({'name': name, 'reason': reason})
    results = []
    for result in session.engine.results:
        results.append(describeResult(result))
    return {
        'verdict': session.engine.verdict(),
        'tieMessage': session.engine.tieMessage,
        'warnings': data.getWarnings(),
        'unavailable': unavailable,
        'activeCount': data.getActiveCount(),
        'usesOffset': data.usesOffset(),
        'xOffset': safeNumber(data.xOffset),
        'results': results,
    }


# ---------------------------------------------------------------
# everything below is called from JavaScript, and takes and returns
# JSON text so that nothing has to be unwrapped on the other side
# ---------------------------------------------------------------

def analyze(pointsJson):
    session.setPoints(json.loads(pointsJson))
    return json.dumps(describe())


# a whole new dataset starts over, so the top three curves are shown
# again rather than whatever was being shown for the last one. The
# desktop app does the same thing when a sample is loaded.
def reset():
    global session
    session = Session()
    return json.dumps(True)


# The curve is worked out here rather than in the browser, so that the
# x offset and the log space fits stay a detail of the engine. Where a
# model has no value, such as a power model at x below zero, the line
# breaks into a new piece instead of jumping across the gap.
def curve(name, xMin, xMax, steps = 240):
    result = session.resultFor(name)
    if result is None or steps < 1:
        return json.dumps([])
    pieces, current = [], []
    for i in range(steps + 1):
        x = xMin + (xMax - xMin) * i / steps
        y = safeNumber(session.engine.predictAt(result, x))
        if y is None:
            if len(current) > 1:
                pieces.append(current)
            current = []
        else:
            current.append([x, y])
    if len(current) > 1:
        pieces.append(current)
    return json.dumps(pieces)


# the same shape, but each entry carries the low and high edge of the
# range a new observation would probably land in
def band(name, xMin, xMax, steps = 90):
    result = session.resultFor(name)
    if result is None or steps < 1:
        return json.dumps([])
    pieces, current = [], []
    for i in range(steps + 1):
        x = xMin + (xMax - xMin) * i / steps
        edges = session.engine.bandAt(result, x)
        low = None if edges is None else safeNumber(edges[0])
        high = None if edges is None else safeNumber(edges[1])
        if low is None or high is None:
            if len(current) > 1:
                pieces.append(current)
            current = []
        else:
            current.append([x, low, high])
    if len(current) > 1:
        pieces.append(current)
    return json.dumps(pieces)


def predict(name, x):
    result = session.resultFor(name)
    if result is None:
        return json.dumps({'y': None, 'low': None, 'high': None})
    edges = session.engine.bandAt(result, x)
    return json.dumps({
        'y': safeNumber(session.engine.predictAt(result, x)),
        'low': None if edges is None else safeNumber(edges[0]),
        'high': None if edges is None else safeNumber(edges[1]),
        'isExtrapolation': session.engine.dataset.isExtrapolation(x),
    })


# leave each point out in turn and see whether the winner changes. This
# is the slow one, so the page asks for it only when it is opened.
def influence():
    sweep = session.engine.influenceSweep()
    if sweep is None:
        return json.dumps({'winner': None, 'entries': []})
    winner, report = sweep
    entries = []
    for entry in report:
        entries.append({
            'row': entry.row,
            'winner': entry.winner,
            'cvShift': safeNumber(entry.cvShift),
            'changesWinner': entry.changesWinner,
        })
    return json.dumps({'winner': winner, 'entries': entries})


def setVisible(name, isVisible):
    result = session.resultFor(name)
    if result is None:
        return json.dumps(False)
    session.engine.setVisible(result, isVisible)
    return json.dumps(True)


# the built in datasets, so the page does not keep its own copy of them
def samples():
    listed = []
    for label, hint, x_coords, y_coords in dataset.samples:
        points = []
        for i in range(len(x_coords)):
            points.append({'x': x_coords[i], 'y': y_coords[i]})
        listed.append({'label': label, 'hint': hint, 'points': points})
    return json.dumps(listed)
