# tests.py
#
# checks the math half of VeriFit against answers worked out by hand.
# cmu_graphics is not needed, so this runs anywhere plain Python runs:
#
#     python3 src/tests.py

import math
import linalg
import stats
import models
import dataset
import engine


def almostEqual(a, b, epsilon = 10 ** -6):
    return abs(a - b) < epsilon

def listsAlmostEqual(listA, listB, epsilon = 10 ** -6):
    if listA is None or listB is None or len(listA) != len(listB):
        return False
    for i in range(len(listA)):
        if not almostEqual(listA[i], listB[i], epsilon):
            return False
    return True


def testLinalg():
    print('Testing linalg...', end='')
    assert(linalg.transpose([[1, 2, 3], [4, 5, 6]]) ==
           [[1, 4], [2, 5], [3, 6]])
    assert(linalg.multiplyMatrices([[1, 2], [3, 4]], [[5, 6], [7, 8]]) ==
           [[19, 22], [43, 50]])

    # 2a + b = 5 and a + 3b = 10 gives a = 1, b = 3
    solution = linalg.solveSystem([[2, 1], [1, 3]], [[5], [10]])
    assert(listsAlmostEqual(solution, [1, 3]))
    # the second row is twice the first, so there is no unique solution
    assert(linalg.solveSystem([[1, 2], [2, 4]], [[3], [6]]) is None)

    # the points (0,1), (1,3), (2,5) sit exactly on y = 1 + 2x
    A = [[1, 0], [1, 1], [1, 2]]
    assert(listsAlmostEqual(linalg.leastSquares(A, [1, 3, 5]), [1, 2]))

    # this one is not exact. Solving the normal equations by hand gives
    # intercept 0.1 and slope 0.6.
    A = [[1, 0], [1, 1], [1, 2], [1, 3]]
    assert(listsAlmostEqual(linalg.leastSquares(A, [0, 1, 1, 2]), [0.1, 0.6]))

    # for any least squares answer, the leftover error must be perpendicular
    # to every column of A, so A^T * (A * solution - y) has to be all zeros
    A = [[1, 2], [3, 4], [5, 6], [7, 9]]
    ys = [1, 5, 2, 8]
    solution = linalg.leastSquares(A, ys)
    predictions = linalg.multiplyMatrixVector(A, solution)
    errors = [predictions[i] - ys[i] for i in range(len(ys))]
    check = linalg.multiplyMatrixVector(linalg.transpose(A), errors)
    assert(listsAlmostEqual(check, [0, 0]))

    # det is 10, so the inverse can be written down directly
    inverse = linalg.invert([[4, 7], [2, 6]])
    assert(listsAlmostEqual(inverse[0], [0.6, -0.7]))
    assert(listsAlmostEqual(inverse[1], [-0.2, 0.4]))
    assert(linalg.invert([[1, 2], [2, 4]]) is None)
    print('Passed!')


def testPolynomialModels():
    print('Testing polynomial models...', end='')
    linear = models.LinearModel()
    assert(linear.fit([0, 1, 2, 3], [1, 3, 5, 7]))  # y = 2x + 1
    assert(listsAlmostEqual(linear.params, [1, 2]))
    assert(almostEqual(linear.predict(10), 21))
    assert(linear.getEquation() == 'y = 2x + 1')

    quadratic = models.QuadraticModel()
    # y = x^2 - 2x + 3 at x = -1, 0, 1, 2, 3
    assert(quadratic.fit([-1, 0, 1, 2, 3], [6, 3, 2, 3, 6]))
    assert(listsAlmostEqual(quadratic.params, [3, -2, 1]))

    cubic = models.CubicModel()
    assert(cubic.fit([-2, -1, 0, 1, 2], [-8, -1, 0, 1, 8]))  # y = x^3
    assert(listsAlmostEqual(cubic.params, [0, 0, 0, 1]))

    flat = models.FlatlineModel()
    assert(flat.fit([1, 2], [4, 6]))
    assert(almostEqual(flat.c, 5))
    assert(flat.getEquation() == 'y = 5')

    # not enough points, and points stacked on the same x
    works, message = models.LinearModel().canFit([5], [1])
    assert(works == False)
    works, message = models.LinearModel().canFit([2, 2], [1, 3])
    assert(works == False)
    print('Passed!')


def testCurvedModels():
    print('Testing curved models...', end='')
    expo = models.ExponentialModel()
    xs = [0, 1, 2, 3]
    ys = [3 * math.exp(0.5 * x) for x in xs]
    assert(expo.fit(xs, ys))
    assert(almostEqual(expo.a, 3) and almostEqual(expo.b, 0.5))

    # the same shape flipped below the x-axis
    negative = models.ExponentialModel()
    ys = [-2 * math.exp(0.3 * x) for x in xs]
    assert(negative.fit(xs, ys))
    assert(almostEqual(negative.a, -2) and almostEqual(negative.b, 0.3))

    # y-values crossing zero is something no exponential can do
    works, message = models.ExponentialModel().canFit([1, 2], [-1, 2])
    assert(works == False)

    power = models.PowerModel()
    xs = [1, 2, 3, 4]
    ys = [2 * x ** 1.5 for x in xs]
    assert(power.fit(xs, ys))
    assert(almostEqual(power.a, 2) and almostEqual(power.b, 1.5))
    assert(power.predict(-1) is None)
    works, message = models.PowerModel().canFit([-1, 2], [1, 2])
    assert(works == False)

    log = models.LogarithmicModel()
    ys = [1 + 2 * math.log(x) for x in xs]
    assert(log.fit(xs, ys))
    assert(almostEqual(log.a, 1) and almostEqual(log.b, 2))
    assert(log.predict(0) is None)
    print('Passed!')


def testAdjusting():
    print('Testing setParams and reset...', end='')
    linear = models.LinearModel()
    linear.fit([0, 1, 2], [1, 3, 5])
    assert(linear.isAdjusted == False)
    assert(linear.setParams([0, 1]))
    assert(linear.isAdjusted)
    assert(almostEqual(linear.predict(3), 3))
    linear.reset()
    assert(linear.isFitted == False and linear.params is None)
    # an unfitted model refuses hand-set parameters
    assert(models.LinearModel().setParams([1, 2]) == False)
    print('Passed!')


def testStatsBasics():
    print('Testing residuals, rmse, and r squared...', end='')
    linear = models.LinearModel()
    linear.fit([0, 1, 2], [1, 3, 5])
    residuals = stats.getResiduals(linear, [0, 1, 2], [1, 3, 5])
    assert(listsAlmostEqual(residuals, [0, 0, 0]))

    assert(almostEqual(stats.rmse([3, -4]), math.sqrt(12.5)))
    assert(stats.rmse([]) is None and stats.rmse(None) is None)

    assert(almostEqual(stats.rSquared(linear, [0, 1, 2], [1, 3, 5]), 1))
    # a flatline predicts the mean, which is exactly what R^2 scores
    # against, so its R^2 is zero by definition
    flat = models.FlatlineModel()
    flat.fit([1, 2, 3], [1, 2, 3])
    assert(almostEqual(stats.rSquared(flat, [1, 2, 3], [1, 2, 3]), 0))

    assert(stats.median([5, 1, 3]) == 3)
    assert(almostEqual(stats.median([4, 1, 3, 2]), 2.5))
    print('Passed!')


def testCrossValidation():
    print('Testing cross validation...', end='')
    assert(stats.chooseFoldCount(10) == 10)
    assert(stats.chooseFoldCount(30) == 10)

    # on a perfect line every held-out point is predicted exactly
    linear = models.LinearModel()
    xs = [1, 2, 3, 4, 5, 6]
    ys = [2 * x + 1 for x in xs]
    linear.fit(xs, ys)
    assert(almostEqual(stats.crossValidatedRmse(linear, xs, ys), 0))

    # there is no randomness anywhere, so the score must repeat exactly
    noisyYs = [2.4, 5.1, 6.2, 9.4, 10.1, 13.4]
    linear = models.LinearModel()
    linear.fit(xs, noisyYs)
    first = stats.crossValidatedRmse(linear, xs, noisyYs)
    second = stats.crossValidatedRmse(linear, xs, noisyYs)
    assert(first is not None and first == second)
    assert(stats.crossValidatedRmse(linear, [1], [2]) is None)
    print('Passed!')


def testInformationScores():
    print('Testing AICc and akaike weights...', end='')
    xs = [1, 2, 3, 4, 5, 6, 7, 8]
    ys = [2.4, 5.1, 6.2, 9.4, 10.1, 13.4, 14.0, 17.6]
    linear = models.LinearModel()
    linear.fit(xs, ys)
    assert(stats.aicc(linear, xs, ys) is not None)
    # linear needs n - K - 1 > 0 with K = 3, so four points is not enough
    assert(stats.aicc(linear, xs[:4], ys[:4]) is None)

    weights = stats.akaikeWeights([100, 102, None])
    assert(weights[2] is None)
    assert(almostEqual(weights[0] + weights[1], 1))
    assert(weights[0] > weights[1])
    assert(stats.akaikeWeights([None, None]) == [None, None])
    print('Passed!')


def testResidualPatterns():
    print('Testing runs test and outlier spotting...', end='')
    assert(stats.countSignRuns([1, 2, -1, -2, 3]) == 3)
    assert(stats.countSignRuns([1, 0, 1]) == 1)  # zeros carry no sign

    # perfectly alternating signs means more runs than chance expects
    z = stats.runsTestScoreZ([1, -1, 1, -1, 1, -1, 1, -1])
    assert(z is not None and z > 0)
    # one positive block then one negative block is the classic sign that
    # the data bends away from the model
    z = stats.runsTestScoreZ([1, 1, 1, 1, -1, -1, -1, -1])
    assert(z is not None and z < 0)
    # too small for the test to mean anything
    assert(stats.runsTestScoreZ([1, -1, 1]) is None)

    assert(stats.outlierIndex([1, -1, 1, -1, 20]) == 4)
    assert(stats.outlierIndex([1, -1, 1, -1, 2]) is None)
    print('Passed!')


def testStandardErrors():
    print('Testing standard errors...', end='')
    # a perfect fit has zero leftover noise, so both errors are zero
    linear = models.LinearModel()
    linear.fit([0, 1, 2], [0, 1, 2])
    errors = stats.standardErrors(linear, [0, 1, 2], [0, 1, 2])
    assert(listsAlmostEqual(errors, [0, 0]))

    # noisy data must give a positive error for every parameter
    xs = [1, 2, 3, 4, 5, 6]
    ys = [2.4, 5.1, 6.2, 9.4, 10.1, 13.4]
    linear = models.LinearModel()
    linear.fit(xs, ys)
    errors = stats.standardErrors(linear, xs, ys)
    assert(errors is not None and len(errors) == 2)
    assert(errors[0] > 0 and errors[1] > 0)

    # two points and two parameters leave nothing to estimate noise from
    linear = models.LinearModel()
    linear.fit([0, 1], [0, 1])
    assert(stats.standardErrors(linear, [0, 1], [0, 1]) is None)
    print('Passed!')


def testParseNumber():
    print('Testing parseNumber...', end='')
    assert(dataset.parseNumber('3.5') == (True, 3.5))
    assert(dataset.parseNumber('  -2 ') == (True, -2.0))
    assert(dataset.parseNumber('abc')[0] == False)
    assert(dataset.parseNumber('')[0] == False)
    assert(dataset.parseNumber('inf')[0] == False)
    assert(dataset.parseNumber('nan')[0] == False)
    print('Passed!')


def testDatasetEditing():
    print('Testing dataset editing and undo...', end='')
    data = dataset.Dataset()
    data.addPoint(1, 2)
    data.addPoint(3, 4)
    assert(data.getPointCount() == 2)
    data.editPoint(0, 5, 6)
    assert(data.points[0].x == 5 and data.points[0].y == 6)
    assert(data.undo())
    assert(data.points[0].x == 1)
    data.toggleExcluded(1)
    assert(data.getRawXs() == [1])
    data.includeAll()
    assert(data.getRawXs() == [1, 3])
    data.clear()
    assert(data.getPointCount() == 0)
    assert(data.undo())
    assert(data.getPointCount() == 2)
    print('Passed!')


def testOffset():
    print('Testing the x offset...', end='')
    small = dataset.Dataset([1, 2, 3], [1, 2, 3])
    assert(small.usesOffset() == False)

    years = dataset.Dataset([2010, 2015, 2020], [1, 2, 3])
    assert(years.usesOffset())
    assert(years.xOffset == 2015)
    assert(years.getFitXs() == [-5, 0, 5])
    print('Passed!')


def testDatasetChecks():
    print('Testing extrapolation and warnings...', end='')
    data = dataset.Dataset([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
    assert(data.isExtrapolation(3) == False)
    assert(data.isExtrapolation(6))
    assert(dataset.Dataset().isExtrapolation(1))

    assert(len(dataset.Dataset().getWarnings()) == 1)
    few = dataset.Dataset([1, 2, 3], [1, 2, 3])
    assert(len(few.getWarnings()) > 0)
    print('Passed!')


# the same noisy straight line as the app's Tie sample
sampleXs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
sampleYs = [2.4, 5.1, 6.2, 9.4, 10.1, 13.4, 14.0, 17.6, 18.1, 21.4, 22.2, 25.6]

def makeEngine(xs, ys):
    data = dataset.Dataset(list(xs), list(ys))
    return engine.AnalysisEngine(data, models.makeAllModels())

def findResult(analysis, name):
    for result in analysis.results:
        if result.model.name == name:
            return result
    return None


def testEngineRanking():
    print('Testing the engine ranking...', end='')
    analysis = makeEngine(sampleXs, sampleYs)
    analysis.analyze()
    assert(len(analysis.results) > 0)
    # the sample data is a noisy straight line, and the ranking should say so
    assert(analysis.results[0].model.name == 'Linear')

    # results must come back sorted best first
    for i in range(len(analysis.results) - 1):
        assert(analysis.results[i].rankingScore() <=
               analysis.results[i + 1].rankingScore())

    # akaike weights split 100% of the support between the scored models
    total = 0
    for result in analysis.results:
        if result.akaikeWeight is not None:
            total += result.akaikeWeight
    assert(almostEqual(total, 1))
    print('Passed!')


def testUnavailableModels():
    print('Testing unavailable models...', end='')
    # y-values that cross zero rule out the exponential and power models
    analysis = makeEngine([1, 2, 3, 4, 5], [2, -1, 3, -2, 4])
    analysis.analyze()
    names = [name for name, reason in analysis.unavailable]
    assert('Exponential' in names and 'Power' in names)
    fitted = [result.model.name for result in analysis.results]
    assert('Linear' in fitted and 'Flatline' in fitted)
    print('Passed!')


def testOffsetPredictions():
    print('Testing that the offset never changes predictions...', end='')
    ys = [x ** 2 for x in range(1, 9)]
    plain = makeEngine([1, 2, 3, 4, 5, 6, 7, 8], ys)
    shifted = makeEngine([2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008], ys)
    plain.analyze()
    shifted.analyze()
    assert(shifted.dataset.usesOffset())

    # the same curve through the same shape of data, so predictions at
    # matching x-values must agree: both should give 4.5^2 = 20.25
    plainQuad = findResult(plain, 'Quadratic')
    shiftedQuad = findResult(shifted, 'Quadratic')
    assert(almostEqual(plain.predictAt(plainQuad, 4.5), 20.25, 10 ** -4))
    assert(almostEqual(shifted.predictAt(shiftedQuad, 2004.5), 20.25,
                       10 ** -4))
    print('Passed!')


def testInfluenceSweep():
    print('Testing the influence sweep...', end='')
    # three points is too few to drop one and still compare models
    analysis = makeEngine([1, 2, 3], [1, 2, 3])
    analysis.analyze()
    assert(analysis.influenceSweep() is None)

    analysis = makeEngine(sampleXs, sampleYs)
    analysis.analyze()
    winnerBefore = analysis.results[0].model.name
    sweep = analysis.influenceSweep()
    assert(sweep is not None)
    winner, report = sweep
    assert(winner == winnerBefore)
    assert(len(report) == len(sampleXs))
    # the sweep excludes points as it works, and must put every one back
    assert(analysis.dataset.getActiveCount() == len(sampleXs))
    assert(analysis.results[0].model.name == winnerBefore)
    print('Passed!')


def testAdjustedRescoring():
    print('Testing rescoring after a hand adjustment...', end='')
    analysis = makeEngine(sampleXs, sampleYs)
    analysis.analyze()
    result = analysis.results[0]
    assert(result.cvRmse is not None)
    params = list(result.model.params)
    params[0] += 1
    result.model.setParams(params)
    analysis.rescoreAdjusted(result)
    # a hand-adjusted curve was never fitted, so the honest answer is that
    # its cross-validation and AICc scores no longer exist
    assert(result.cvRmse is None and result.aicc is None)
    assert(result.isAdjusted())
    print('Passed!')


def testFormatNumber():
    print('Testing equation number formatting...', end='')
    assert(models.formatNumber(3.0) == '3')
    assert(models.formatNumber(2.71828) == '2.7183')
    assert(models.formatNumber(-1.5) == '-1.5')
    assert(models.formatNumber(0) == '0')
    # tiny coefficients used to display as a plain 0
    assert(models.formatNumber(0.000003) == '(3*10^-6)')
    assert(models.formatNumber(-0.0000425) == '(-4.25*10^-5)')

    # a whole equation with a tiny slope: y = 0.000003x
    linear = models.LinearModel()
    assert(linear.fit([0, 1], [0, 0.000003]))
    assert(linear.getEquation() == 'y = (3*10^-6)x')
    print('Passed!')


def testPowerStandardErrors():
    print('Testing power model standard errors...', end='')
    xs = [1, 2, 3, 4, 5, 6]
    # exactly 2 * x^1.5, so the leftover noise is zero
    exact = models.PowerModel()
    assert(exact.fit(xs, [2 * x ** 1.5 for x in xs]))
    errors = stats.standardErrors(exact, xs, [2 * x ** 1.5 for x in xs])
    assert(listsAlmostEqual(errors, [0, 0]))

    # the same curve with a bit of noise
    ys = [2.1, 5.5, 10.7, 15.8, 22.6, 29.2]
    power = models.PowerModel()
    assert(power.fit(xs, ys))
    errors = stats.standardErrors(power, xs, ys)
    assert(errors is not None and len(errors) == 2)
    assert(errors[0] > 0 and errors[1] > 0)

    # 'a' came from ln(a), so its interval is multiplicative and can
    # never cross below zero
    bounds = stats.parameterBounds(power, xs, ys)
    assert(bounds is not None and len(bounds) == 2)
    low, high = bounds[0]
    assert(0 < low < power.a < high)
    low, high = bounds[1]
    assert(low < power.b < high)
    print('Passed!')


def testVerdict():
    print('Testing the verdict...', end='')
    # nothing to conclude from an empty dataset
    analysis = makeEngine([], [])
    analysis.analyze()
    assert(analysis.verdict() == '')

    # one point fits a flatline but cannot be scored
    analysis = makeEngine([3], [5])
    analysis.analyze()
    assert('too little data' in analysis.verdict())

    # two points on the same x leave the flatline as the only model
    analysis = makeEngine([2, 2], [1, 3])
    analysis.analyze()
    assert('only model' in analysis.verdict())

    # the sample data is a genuine tie: a power fit with exponent near 1
    # is almost the same curve as a line, and both use two parameters
    analysis = makeEngine(sampleXs, sampleYs)
    analysis.analyze()
    text = analysis.verdict()
    assert('almost identically' in text)
    assert('cannot tell them apart' in text)

    # a parabola has a clear winner with clean residuals
    analysis = makeEngine([1, 2, 3, 4, 5, 6, 7, 8],
                          [1.1, 3.9, 9.2, 15.8, 25.3, 35.8, 49.4, 63.7])
    analysis.analyze()
    text = analysis.verdict()
    assert(text.startswith('Quadratic predicts unseen points best'))
    assert('no obvious pattern' in text)
    print('Passed!')


def testSampleDatasets():
    print('Testing the sample datasets...', end='')
    byLabel = {}
    for label, hint, xs, ys in dataset.samples:
        analysis = makeEngine(xs, ys)
        analysis.analyze()
        byLabel[label] = analysis

    # each sample was picked to show one thing off, so pin that down
    assert(byLabel['Line'].results[0].model.name == 'Linear')
    names = [name for name, reason in byLabel['Line'].unavailable]
    assert('Exponential' in names and 'Power' in names)

    assert(byLabel['Curve'].results[0].model.name == 'Quadratic')
    assert(byLabel['Growth'].results[0].model.name == 'Exponential')

    # the outlier sample: the wild point gets flagged, and the sweep
    # shows the winner depends on that single row
    outlier = byLabel['Outlier']
    assert(outlier.results[0].outlierIndex == 3)
    winner, report = outlier.influenceSweep()
    flips = [entry.row for entry in report if entry.changesWinner]
    assert(3 in flips)

    assert('cannot tell them apart' in byLabel['Tie'].verdict())
    print('Passed!')


def testPredictionBands():
    print('Testing prediction bands...', end='')
    # a perfect line has zero noise, so the band collapses onto the line
    xs = [1, 2, 3, 4, 5, 6]
    linear = models.LinearModel()
    linear.fit(xs, [2 * x + 1 for x in xs])
    setup = stats.bandSetup(linear, xs, [2 * x + 1 for x in xs])
    low, high = stats.predictionBand(linear, setup, 4)
    assert(almostEqual(low, 9) and almostEqual(high, 9))

    # noisy data: the band brackets the prediction, and it must be wider
    # far outside the data than at the middle of it
    ys = [2.4, 5.1, 6.2, 9.4, 10.1, 13.4]
    linear = models.LinearModel()
    linear.fit(xs, ys)
    setup = stats.bandSetup(linear, xs, ys)
    low, high = stats.predictionBand(linear, setup, 3.5)
    guess = linear.predict(3.5)
    assert(low < guess < high)
    farLow, farHigh = stats.predictionBand(linear, setup, 20)
    assert(farHigh - farLow > high - low)

    # a log-space fit gets a multiplicative band that cannot cross zero
    expo = models.ExponentialModel()
    growthYs = [6.1, 7.4, 11.5, 14.9, 22.1, 29.6]
    expo.fit(xs, growthYs)
    setup = stats.bandSetup(expo, xs, growthYs)
    low, high = stats.predictionBand(expo, setup, 3)
    assert(0 < low < expo.predict(3) < high)

    # the engine carries the band, and a hand adjustment takes it away
    analysis = makeEngine(sampleXs, sampleYs)
    analysis.analyze()
    result = analysis.results[0]
    assert(analysis.bandAt(result, 5) is not None)
    result.model.setParams(list(result.model.params))
    analysis.rescoreAdjusted(result)
    assert(analysis.bandAt(result, 5) is None)
    print('Passed!')


def testColorsAndVisibility():
    print('Testing stable colors and visibility memory...', end='')
    analysis = makeEngine(sampleXs, sampleYs)
    analysis.analyze()
    linearColor = findResult(analysis, 'Linear').colorIndex
    cubicColor = findResult(analysis, 'Cubic').colorIndex
    assert(linearColor != cubicColor)

    # hiding the winner's curve must survive the next refit
    winner = analysis.results[0]
    winnerName = winner.model.name
    assert(winner.isVisible)
    analysis.setVisible(winner, False)

    # a new point changes the data and reruns everything
    analysis.dataset.addPoint(13, 27.4)
    analysis.analyze()
    assert(findResult(analysis, 'Linear').colorIndex == linearColor)
    assert(findResult(analysis, 'Cubic').colorIndex == cubicColor)
    assert(findResult(analysis, winnerName).isVisible == False)
    print('Passed!')


def main():
    testLinalg()
    testPolynomialModels()
    testCurvedModels()
    testAdjusting()
    testStatsBasics()
    testCrossValidation()
    testInformationScores()
    testResidualPatterns()
    testStandardErrors()
    testParseNumber()
    testDatasetEditing()
    testOffset()
    testDatasetChecks()
    testEngineRanking()
    testUnavailableModels()
    testOffsetPredictions()
    testInfluenceSweep()
    testAdjustedRescoring()
    testFormatNumber()
    testPowerStandardErrors()
    testVerdict()
    testSampleDatasets()
    testPredictionBands()
    testColorsAndVisibility()
    print('All tests passed!')


main()
