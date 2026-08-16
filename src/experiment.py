# experiment.py
#
# VeriFit claims that ranking models by cross-validated error finds the
# right model more often than ranking them by R squared. This file tests
# that claim instead of assuming it.
#
# The idea: build data from an equation we already know, hide that
# equation, and see which scoring rule points back at it. Because the
# answer is known in advance, every run is either right or wrong, and
# the two rules can be compared honestly.
#
#     python3 src/experiment.py

import math
import random
import dataset
import models
import engine


# the equations the data is built from. Each one stays positive over the
# x range below, so no model is ruled out before the comparison starts.
def linearTruth(x):
    return 2 * x + 5

def quadraticTruth(x):
    return 0.4 * x * x - 1.5 * x + 12

def exponentialTruth(x):
    return 3 * math.exp(0.25 * x)

def logarithmicTruth(x):
    return 4 + 6 * math.log(x)

def powerTruth(x):
    return 2 * (x ** 1.5)


truths = [('Linear', linearTruth),
          ('Quadratic', quadraticTruth),
          ('Exponential', exponentialTruth),
          ('Logarithmic', logarithmicTruth),
          ('Power', powerTruth)]


# evenly spaced x values from 1 to 11, which keeps logs and powers legal
def makeXs(n):
    if n < 2:
        return [1]
    step = 10 / (n - 1)
    return [1 + i * step for i in range(n)]


# noise is a share of how far the clean values travel, so that the same
# noise setting means the same difficulty for every equation
def makeNoisyYs(truth, xs, noiseShare):
    clean = [truth(x) for x in xs]
    spread = max(clean) - min(clean)
    noisy = []
    for value in clean:
        noisy.append(value + random.gauss(0, noiseShare * spread))
    return noisy


def bestByRSquared(results):
    best = None
    for result in results:
        if result.r2 is None:
            continue
        if best is None or result.r2 > best.r2:
            best = result
    return best


# one round: build data from the given equation, then ask each rule which
# model it thinks made the data. Returns the two names it answered.
def runTrial(truth, n, noiseShare):
    xs = makeXs(n)
    ys = makeNoisyYs(truth, xs, noiseShare)
    analysis = engine.AnalysisEngine(dataset.Dataset(xs, ys),
                                     models.makeAllModels())
    analysis.analyze()
    if len(analysis.results) == 0:
        return (None, None)
    cvChoice = analysis.results[0].model.name
    r2Result = bestByRSquared(analysis.results)
    r2Choice = None if r2Result is None else r2Result.model.name
    return (cvChoice, r2Choice)
