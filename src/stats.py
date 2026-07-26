import math

#######################################################################
# written by Claude Opus 4.8 / Jul 28, 2026 
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
        total += value**2
    return total

# calculate the root mean square error from a list of residuals
def rmse(residuals):
    if residuals == None or len(residuals) == 0:
        return None
    return math.sqrt(sumOfSquares(residuals) / len(residuals))

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
    totalSquares = 0
    for y in y_coords:
        totalSquares = totalSquares + (y - meanY) ** 2
    # if totalSquares is 0, every y is identical, so R^2 is not defined
    if totalSquares == 0:
        return None
    return 1 - sumOfSquares(residuals) / totalSquares


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

        # if not practice.fit(trainXs, trainYs):
        #     continue
         
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
    