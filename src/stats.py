import math
import linalg

#######################################################################
# written by Claude Opus 4.8 / Jul 25, 2026 
#######################################################################
def safePredict(model, x):
    # A model can fail to predict for legitimate reasons: a power model
    # cannot handle x <= 0, and an exponential can overflow if b*x is
    # huge. Rather than letting the program crash, we return None and
    # let the caller decide what to do.
    try:
        guess = model.predict(x)
    except (ValueError, OverflowError, ZeroDivisionError):
        return None
    if guess == None:
        return None
    # Catches inf and nan, which can appear without raising an error.
    if not isFinite(guess):
        return None
    return guess

def isFinite(value):
    if value != value:                       # nan is the only value
        return False                         # not equal to itself
    if value == float('inf') or value == float('-inf'):
        return False
    if abs(value) > 10 ** 150:
        return False
    return True
#######################################################################


def getResiduals(model, x_coords, y_coords):
    # residual = actual value - predicted value
    if not model.isFitted:
        return None
    residuals = []
    for i in range(len(x_coords)):
        guess = safePredict(model, x_coords[i])
        if guess is None:
            return None
        residuals.append(y_coords[i]-guess)
    return residuals

def sumOfSquares(values):
    total = 0
    for value in values:
        if abs(value) > 10 ** 150:
            return float('inf')
        total += value**2
    return total

# calculate the root mean square error from a list of residuals
def rmse(residuals):
    if residuals == None or len(residuals) == 0:
        return None
    total = sumOfSquares(residuals)
    if total == float('inf'):
        return None
    return math.sqrt(total / len(residuals))

# calculate the model's RMSE on the training data
def trainingRmse(model, x_coords, y_coords):
    return rmse(getResiduals(model, x_coords, y_coords))

# calculate coefficient of determination
# R^2 = 1 - (sum of squared residuals)/(squared error)
# sets the dumbest model that returns mere average of y-values as baseline
# compares how good the model is compared to the dumbest model
def rSquared(model, x_coords, y_coords):
    residuals = getResiduals(model, x_coords, y_coords)
    if residuals == None or len(y_coords) == 0:
        return None
    meanY = sum(y_coords) / len(y_coords)
    # if totalSquares is 0, every y is identical, so R^2 is not defined
    totalSquares = sumOfSquares([y - meanY for y in y_coords])
    residualSquares = sumOfSquares(residuals)
    if totalSquares == 0 or totalSquares == float('inf'):
        return None
    if residualSquares == float('inf'):
        return None
    return 1 - residualSquares / totalSquares

def chooseFoldCount(n):
    # for small data sets, each data points will be hidden and tested
    # for large data sets, the model will use only 10 groups for efficiency
    if n <= 25:
        return n
    return 10


# k fold cross validated RMSE
def crossValidatedRmse(model, x_coords, y_coords, foldCount = None):
    n = len(x_coords)
    if foldCount is None:
        foldCount = chooseFoldCount(n)
    if foldCount < 2 or n < 2:
        return None

    heldOutErrors = [] # contain residuals from test points

    for fold in range(foldCount):
        trainXs, trainYs = [], [] # data used to fit the model
        testXs, testYs = [], [] # data hidden from the model and used to evalute it
        for i in range(n):
            if i % foldCount == fold:
                testXs.append(x_coords[i])
                testYs.append(y_coords[i])
            else:
                trainXs.append(x_coords[i])
                trainYs.append(y_coords[i])

        # if len(testXs) == 0:
        #     continue

        practice = model.makeBlankCopy()
        works, message = practice.canFit(trainXs, trainYs)
        # checks if the fold meets the restrictions,
        # such as minimum points and domain restrictions
        if not works:
            continue

        if not practice.fit(trainXs, trainYs):
            continue
         
        for j in range(len(testXs)):
            # safePredict will convert failure of prediction into None instead of crashing 
            # the entire program
            guess = safePredict(practice, testXs[j])
            if guess == None:
                continue
            heldOutErrors.append(testYs[j] - guess)
    #check if enough amount of rounds of the test were successful
    minErrors = max(2, math.ceil(n/2))
    if len(heldOutErrors) < minErrors:
            return None

    return rmse(heldOutErrors)

def aicc(model, x_coords, y_coords):
    residuals = getResiduals(model, x_coords, y_coords)
    if residuals is None:
        return None
    n = len(x_coords)
    K = model.paramCount + 1
    # the correction term divides by (n - K - 1), so we need enough points
    # for example, cubic has K = 5 and therefore needs at least 7 points
    if n - K - 1 <= 0:
        return None
    squaredError = sumOfSquares(residuals)
    # avoids the perfect fitting case in which parameter count is same as data points
    if squaredError <= 0:
        return None
    aic = n * math.log(squaredError / n) + 2 * K
    # corrects AIC's tendency to favor overly complicated models with small sample size
    correction = (2 * K * (K + 1)) / (n - K - 1)
    return aic + correction

# turns a list of AICc scores into shares of support that add to 1
def akaikeWeights(aiccValues):
    # find the best AICc score:
    best = None
    for value in aiccValues:
        if value is not None:
            if best is None or value < best:
                best = value
    # if every value is None, no model can be compared
    if best is None:
        return [None] * len(aiccValues)
    # calculate and add score of each aiccValues
    scores, total = [], 0
    for value in aiccValues:
        if value == None:
            scores.append(None)
        else:
            difference = value - best
            score = math.exp(-difference / 2) # relative likelihood
            scores.append(score)
            total += score
    # weight each score to sum up to 1
    weights = []
    for score in scores:
        if score == None:
            weights.append(None)
        else:
            weights.append(score / total)
    return weights

def median(values):
    if values is None or len(values) == 0:
        return None
    ordered = sorted(values)
    middleIndex = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middleIndex]
    else:
        return (ordered[middleIndex-1]+ordered[middleIndex])/2

# orders residual values from lowest x value to largest x value
def residualsInXOrder(x_coords, residuals):
    pairs = []
    for i in range(len(residuals)):
        pairs.append((x_coords[i], residuals[i]))
    pairs.sort(key = lambda pair:pair[0])
    ordered = []
    for x, residual in pairs:
        ordered.append(residual)
    return ordered

# run is a series of residuals sharing a sign
# heavily clustered residuals will have less runs
def countSignRuns(values):
    runs, lastSign = 0, 0
    for value in values:
        if value < 0:
            sign = -1
        elif value > 0:
            sign = +1
        else:
            continue
        if sign != lastSign:
            runs += 1
            lastSign = sign
    return runs

# THe Wald-Wolfowitz Runs Test
# based on null hypothesis that the positive and negative signs
# will ideally occur in random order if the model is accurate fit
def runsTestScoreZ(values):
    positives, negatives = 0, 0
    for value in values:
        if value < 0:
            negatives += 1
        elif value > 0:
            positives += 1
        else:
            continue
    n = positives + negatives
    # the result will be unreliable if there are too less data
    if positives < 2 or negatives < 2 or n < 8:
        return None
    runs = countSignRuns(values)
    expected = (2*positives*negatives)/n + 1
    varTop = 2*positives*negatives * (2 * positives * negatives - n)
    varBottom = n * n * (n - 1)
    if varBottom <= 0:
        return None
    variance = varTop/varBottom
    if variance <= 0:
        return None
    stdDevR = variance**0.5

    zScore = (runs-expected)/stdDevR
    return zScore

def curvatureWarning(x_coords, residuals):
    ordered = residualsInXOrder(x_coords, residuals)
    signed = []
    for value in ordered:
        if value != 0:
            signed.append(value)
    if len(signed) < 5:
        return ''
    runs = countSignRuns(ordered)
    z = runsTestScoreZ(ordered)
    if z is not None:
        tooFew = z < -1.96
    else:
        # too small for the test, so fall back on the blunt ver
        tooFew = runs <= 2
    if not tooFew:
        return str()
    return(f'The points sit above the curve in one stretch and below it in '
           f'another ({runs} runs). The data bends in a way this model '
           f'cannot follow.')

# compares the typical miss in the first half on x against the second half
# median will serve as the half
def spreadWarning(x_coords, residuals):
    ordered = residualsInXOrder(x_coords, residuals)
    n = len(ordered)
    if n < 8:
        return str()
    half = n//2
    firstHalf = median([abs(value) for value in ordered[:half]])
    secondHalf = median([abs(value) for value in ordered[n-half:]])
    if firstHalf is None or secondHalf is None:
        return str()
    smaller, larger = min(firstHalf, secondHalf), max(firstHalf, secondHalf)
    if smaller <= 0:
        return str()
    ratio = larger / smaller
    if ratio < 3:
        return str()
    if secondHalf > firstHalf:
        where = 'larger x'
    else:
        where = 'smaller x'
    return (f'The misses are about {ratio:.0f} times bigger at {where}. '
            f'Predictions there are much less trustworthy than the single '
            f'error number suggests.')

# search for the most extreme residual. The threshold for being "extreme"
# is being 5 times the median absolute redisual
def outlierIndex(residuals, threshold = 5):
    if residuals is None or len(residuals) < 5:
        return None
    sizes = []
    for residual in residuals:
        sizes.append(abs(residual))
    typical = median(sizes)
    if typical is None or typical <= 0:
        return None
    worstSize = max(sizes)
    worstRatio = worstSize / typical
    if worstRatio < threshold:
        return None
    return sizes.index(worstSize)

def outlierWarning(residuals):
    index = outlierIndex(residuals)
    if index is None:
        return str()
    sizes = []
    for residual in residuals:
        sizes.append(abs(residual))
    ratio = sizes[index]/median(sizes)
    return (f'One point misses by about {ratio:.0f} times the usual amount. '
            f'Try excluding it to see whether the ranking depends on it.')

def describeResiduals(x_coords, y_coords, residuals):
    if residuals is None or len(residuals) == 0:
        return list()
    # mere tiny floating values might lead to curvature warning,
    # so this will simply rule out such cases
    scale = max(y_coords) - min(y_coords)
    typical = rmse(residuals)
    if scale > 0 and typical is not None and typical < scale * 10 ** -9:
        return list()
    warnings = []
    for warning in [curvatureWarning(x_coords, residuals),
                    spreadWarning(x_coords, residuals),
                    outlierWarning(residuals)]:
        if warning != str():
            warnings.append(warning)
    return warnings

# everything about a model's uncertainty that does not depend on x: the
# noise estimate and the inverse of A^T A, bundled up for predictionBand
def bandSetup(model, x_coords, y_coords):
    if not model.isFitted:
        return None
    A = model.designMatrix(x_coords)
    fitResiduals = model.fitSpaceResiduals(x_coords, y_coords)
    if A is None or fitResiduals is None or len(A) == 0:
        return None
    n, p = len(A), len(A[0])
    if n - p <= 0:
        return None
    squaredError = sumOfSquares(fitResiduals)
    if squaredError == float('inf'):
        return None
    sigmaSquared = squaredError / (n - p)
    AtA = linalg.multiplyMatrices(linalg.transpose(A), A)
    inverse = linalg.invert(AtA)
    if inverse is None:
        return None
    return (sigmaSquared, inverse)

# the plausible range for a brand new observation at x: the prediction
# plus or minus two standard deviations, sigma^2 * (1 + a^T (A^T A)^-1 a).
# The band widens away from the middle of the data, which is exactly the
# extrapolation warning drawn as a picture.
def predictionBand(model, setup, x, spread = 2):
    if setup is None:
        return None
    guess = safePredict(model, x)
    if guess is None:
        return None
    sigmaSquared, inverse = setup
    rows = model.designMatrix([x])
    if rows is None or len(rows) == 0:
        return None
    row = rows[0]
    p = len(row)
    leverage = 0
    for i in range(p):
        for j in range(p):
            leverage += row[i] * inverse[i][j] * row[j]
    # a negative value can only come from rounding on a near-singular fit
    if leverage < 0:
        return None
    halfWidth = spread * math.sqrt(sigmaSquared * (1 + leverage))
    if model.usesLogSpace:
        # the fit lives in log space, so the band is multiplicative and
        # can never cross zero
        if halfWidth > 300:
            return None
        low = guess * math.exp(-halfWidth)
        high = guess * math.exp(halfWidth)
        return (min(low, high), max(low, high))
    return (guess - halfWidth, guess + halfWidth)


def standardErrors(model, x_coords, y_coords):
    if not model.isFitted:
        return None
    A = model.designMatrix(x_coords)
    fitResiduals = model.fitSpaceResiduals(x_coords, y_coords)
    if A is None or fitResiduals is None or len(A) == 0:
        return None
    n, p = len(A), len(A[0])
    # with no spare points there is nothing left to estimate the noise from
    if n - p <= 0:
        return None
    squaredError = sumOfSquares(fitResiduals)
    if squaredError == float('inf'):
        return None
    sigmaSquared = squaredError / (n - p)

    AtA = linalg.multiplyMatrices(linalg.transpose(A), A)
    inverse = linalg.invert(AtA)
    if inverse is None:
        return None

    errors = []
    for j in range(p):
        variance = sigmaSquared * inverse[j][j]
        # a negative diagonal can only come from rounding on a near-singular
        # matrix, and there is no honest error to report in that case
        if variance < 0:
            return None
        errors.append(math.sqrt(variance))
    return errors

def parameterBounds(model, x_coords, y_coords, spread = 2):
    errors = standardErrors(model, x_coords, y_coords)
    if errors is None or model.params is None:
        return None
    if len(errors) != len(model.params):
        return None
    return model.boundsFromErrors(errors, spread)