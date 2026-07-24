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
