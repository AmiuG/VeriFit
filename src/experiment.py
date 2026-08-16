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


# Two ways of being wrong. Added noise is the same size everywhere, as a
# share of how far the clean values travel. Multiplied noise grows with
# the value itself, which is how growth data usually misbehaves: a
# population is off by a few percent, not by a few individuals.
def makeNoisyYs(truth, xs, noiseShare, isMultiplied = False):
    clean = [truth(x) for x in xs]
    spread = max(clean) - min(clean)
    noisy = []
    for value in clean:
        if isMultiplied:
            noisy.append(value * math.exp(random.gauss(0, noiseShare)))
        else:
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
# model it thinks made the data. Also reports whether the app called the
# top two too close to separate, which is a different kind of answer from
# simply being wrong.
def runTrial(truth, n, noiseShare, isMultiplied = False):
    xs = makeXs(n)
    ys = makeNoisyYs(truth, xs, noiseShare, isMultiplied)
    analysis = engine.AnalysisEngine(dataset.Dataset(xs, ys),
                                     models.makeAllModels())
    analysis.analyze()
    if len(analysis.results) == 0:
        return (None, None, [])
    cvChoice = analysis.results[0].model.name
    r2Result = bestByRSquared(analysis.results)
    r2Choice = None if r2Result is None else r2Result.model.name
    # the names the app refused to choose between, if it said so
    tied = []
    if analysis.tieMessage != str() and len(analysis.results) >= 2:
        tied = [analysis.results[0].model.name,
                analysis.results[1].model.name]
    return (cvChoice, r2Choice, tied)


# many rounds of the same setting. Counts how often each rule named the
# equation the data actually came from, and how often the app declined to
# separate the true equation from one rival.
def runCondition(name, truth, n, noiseShare, trials, isMultiplied = False):
    cvHits, r2Hits, r2Cubic, fairHits = 0, 0, 0, 0
    for i in range(trials):
        cvChoice, r2Choice, tied = runTrial(truth, n, noiseShare,
                                            isMultiplied)
        if cvChoice == name:
            cvHits += 1
        if r2Choice == name:
            r2Hits += 1
        if r2Choice == 'Cubic':
            r2Cubic += 1
        # either it named the right equation, or it admitted the top two
        # were too close to call and the right one was among them
        if cvChoice == name or name in tied:
            fairHits += 1
    return (cvHits / trials, fairHits / trials, r2Hits / trials,
            r2Cubic / trials)


def percent(share):
    return f'{share * 100:.0f}%'


def runOneTable(title, settings, trials):
    print()
    print(f'{title}   ({trials} runs per row)')
    print(f'{"true equation":14}{"CV names it":>13}{"or admits a tie":>17}'
          f'{"R2 names it":>13}{"R2 says cubic":>15}')
    cvTotal, fairTotal, r2Total = 0, 0, 0
    for name, truth, n, noiseShare, isMultiplied in settings:
        cvShare, fairShare, r2Share, cubicShare = runCondition(
            name, truth, n, noiseShare, trials, isMultiplied)
        cvTotal += cvShare
        fairTotal += fairShare
        r2Total += r2Share
        print(f'{name:14}{percent(cvShare):>13}{percent(fairShare):>17}'
              f'{percent(r2Share):>13}{percent(cubicShare):>15}')
    count = len(settings)
    print(f'{"average":14}{percent(cvTotal / count):>13}'
          f'{percent(fairTotal / count):>17}{percent(r2Total / count):>13}')


def settingsFor(n, noiseShare, isMultiplied = False):
    rows = []
    for name, truth in truths:
        rows.append((name, truth, n, noiseShare, isMultiplied))
    return rows


def runStudy(trials = 400, seed = 112):
    # one seed for the whole study, so the numbers can be reproduced
    random.seed(seed)
    runOneTable('added noise, 12 points', settingsFor(12, 0.03), trials)
    runOneTable('added noise, 12 points, twice as noisy',
                settingsFor(12, 0.08), trials)
    runOneTable('added noise, only 8 points', settingsFor(8, 0.05), trials)
    runOneTable('added noise, 30 points', settingsFor(30, 0.08), trials)
    # the growth equations are usually wrong by a percentage rather than
    # by a fixed amount, and VeriFit fits them in log space to match
    runOneTable('multiplied noise, 12 points',
                settingsFor(12, 0.08, True), trials)
    runOneTable('multiplied noise, 30 points',
                settingsFor(30, 0.08, True), trials)


def main():
    print('How often does each scoring rule name the equation that')
    print('actually produced the data? Higher is better.')
    runStudy()
    print()


main()
