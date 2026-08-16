import math
import linalg
import stats

# turn 3.0 into '3' and 2.71828 into '2.7183' so equations look clean
def formatNumber(value):
    # rounding to 4 decimals would turn a tiny coefficient like 0.000003
    # into a plain 0, so those switch to powers of ten instead
    if value != 0 and abs(value) < 0.001:
        digits, exponent = f'{value:.2e}'.split('e')
        digits = digits.rstrip('0').rstrip('.')
        return f'({digits}*10^{int(exponent)})'
    rounded = round(value, 4)
    if rounded == int(rounded):
        return str(int(rounded))
    return str(rounded)
# check if the value is technically one
def almostOne(value):
    return abs(value - 1) < 10 ** -10

def formatXTerm(offset):
    if offset == 0:
        return 'x'
    elif offset > 0:
        return f'(x - {formatNumber(offset)})'
    else:
        return f'(x + {formatNumber(abs(offset))})'

# learned inheritence from this YouTube video https://youtu.be/RSl87lqOXDE?si=feKdyYe_9CdtmLQ7

class Model:
    usesShiftedX = True
    def __init__(self):
        self.name = 'Model'
        self.paramCount = 0 # number of parameters model should find
        self.params = None # will eventually store the fitted coefficients
        self.isFitted = False

        # will be true when a sensitivity slider edits the parameters
        self.isAdjusted = False

    # check if the model has enough amount of points for fitting
    def canFit(self, x_coords, y_coords):
        if len(x_coords) < self.paramCount:
            return (False, f'Needs at least {self.paramCount} points')
        diffXCoords = len(set(x_coords))
        if diffXCoords < self.paramCount:
            return (False, f'Needs at least {self.paramCount} different points')
        return (True, '')

    def makeBlankCopy(self):
        return type(self)()


    # placeholders(subclasses will fill out these functions)
    def fit(self, x_coords, y_coords):
        return False
    def predict(self, x):
        return None
    def getEquation(self):
        return ''

    def reset(self):
            self.params = None
            self.isFitted = False
            self.isAdjusted = False
    
    def setParams(self, params):
        if (not self.isFitted) or (len(params) != self.paramCount):
            return False
        self.params = list(params)
        self.isAdjusted = True
        self.applyParams()
        return True

    def applyParams(self):
        pass

    def designMatrix(self, x_coords):
        return None

    def fitSpaceResiduals(self, x_coords, y_coords):
        return None

    # turn standard errors into a (low, high) slider range per parameter.
    # symmetric here; the two log-fitted models override it.
    def boundsFromErrors(self, errors, spread = 2):
        bounds = []
        for i in range(len(self.params)):
            middle, reach = self.params[i], spread * errors[i]
            bounds.append((middle - reach, middle + reach))
        return bounds

    # tell what state the model is currently in
    def __repr__(self):
        if not self.isFitted:
            return f'{self.name}(not fitted yet)'
        return f'{self.name}: {self.getEquation()}'


class PolynomialModel(Model):
    def __init__(self, degree, name):
        super().__init__()
        self.degree = degree
        self.name = name
        startingPower = list(range(degree+1))
        self.setPowers(startingPower)

    # allow polynomials to use only selected terms
    def setPowers(self, powers):
        # ignore repeated powers and sort them
        cleanedPowers = list(set(powers))
        cleanedPowers.sort()
        self.powers = cleanedPowers # stores the powers
        self.paramCount = len(cleanedPowers)
        # update new degree
        self.degree = 0
        for power in cleanedPowers:
            if power > self.degree:
                self.degree = power
        # reset the past fit
        self.reset()

    # checks if the model has constant term because it could affect results
    def hasConstantTerm(self):
        return 0 in self.powers

    def makeBlankCopy(self):
        fresh = PolynomialModel(self.degree, self.name)
        fresh.setPowers(self.powers)
        return fresh

    def canFit(self, x_coords, y_coords):
        works, message = super().canFit(x_coords, y_coords)
        if not works:
            return (works, message)
        if len(self.powers) == 0:
            return (False, 'At least one term must be turned on')
        for power in self.powers:
            if (power < 0) and (0 in x_coords):
                return (False, 'Negative powers cannot accept x=0')
        return (True, '')

    def fit(self, x_coords, y_coords):
        works, message = self.canFit(x_coords, y_coords)
        if not works:
            return False
        # makes design matrix A
        A = [[x ** power for power in self.powers] for x in x_coords]
        solution = linalg.leastSquares(A, y_coords)
        # check if the system is valid and update values accordingly
        if solution is None:
            return False
        else:
            self.params = solution
            self.isFitted = True
            self.isAdjusted = False
            return True
    
    def designMatrix(self, x_coords):
        return [[x ** power for power in self.powers] for x in x_coords]

    def fitSpaceResiduals(self, x_coords, y_coords):
        # a polynomial is fitted in ordinary units, so these are just residuals
        return stats.getResiduals(self, x_coords, y_coords)
    # return predicted y value by the fitted model

    def predict(self, x):
        if not self.isFitted:
            return None
        total = 0
        for i in range(len(self.powers)):
            total += self.params[i]*(x**self.powers[i])
        return total

    def getEquation(self, offset = 0):
        if not self.isFitted:
            return ''
        xTerm = formatXTerm(offset)
        leftHandSide = 'y'
        rightHandSide = ''
        # add terms from the largest power to smallest power
        for i in range(len(self.powers)-1, -1, -1):
            power = self.powers[i]
            coefficient = self.params[i]
            if abs(coefficient) < 10**(-10):
                continue
            # format operator signs based on whether this is the first term
            if rightHandSide == '':
                if coefficient < 0:
                    rightHandSide += '-'
            else:
                if coefficient < 0:
                    rightHandSide += ' - '
                else:
                    rightHandSide += ' + '
            # add numerical coefficient unless it is 1 before an x term
            if not (almostOne(abs(coefficient)) and power >= 1):
                rightHandSide += formatNumber(abs(coefficient))
            # add x variable and exponent power
            if power == 1:
                rightHandSide += xTerm
            elif power != 0:
                rightHandSide += f'{xTerm}^{power}'
        # if every coefficient was zero
        if rightHandSide == '':
            rightHandSide = '0'

        return f'{leftHandSide} = {rightHandSide}'

# subclasses of PolynomialModel (linear, quadratic, cubic and custom)
class LinearModel(PolynomialModel):
    def __init__(self):
        super().__init__(1, 'Linear')

class QuadraticModel(PolynomialModel):
    def __init__(self):
        super().__init__(2, 'Quadratic')

class CubicModel(PolynomialModel):
    def __init__(self):
        super().__init__(3, 'Cubic')

class CustomPolynomialModel(PolynomialModel):
    def __init__(self, powers):
        super().__init__(0, 'Custom')
        self.setPowers(powers)
        self.name = self.makeName()

    #make the custom name
    def makeName(self):
        terms = []
        for i in range(len(self.powers)-1, -1, -1):
            if self.powers[i] == 0:
                terms.append('1')
            elif self.powers[i] == 1:
                terms.append('x')
            else:
                terms.append(f'x^{self.powers[i]}')
        equation = '+'.join(terms)
        return f'Custom({equation})'


class ExponentialModel(Model):
    def __init__(self):
        super().__init__()
        self.name = 'Exponential'
        self.paramCount = 2
        self.a, self.b = None, None #constants for fit model

    def canFit(self, x_coords, y_coords):
        works, message = super().canFit(x_coords, y_coords)
        if not works:
            return (False, message)
        allPositiveY = all(y > 0 for y in y_coords) # checks if y-values are strictly positive
        allNegativeY = all(y < 0 for y in y_coords) # checks if y-values are strictly negative
        if not (allPositiveY or allNegativeY):
            return (False, 'All y-values must be all positive or all negative')
        return (True, '')

    def fit(self, x_coords, y_coords):
        works, message = self.canFit(x_coords, y_coords)
        if not works:
            return False
        isNegative = y_coords[0] < 0 # checks if the model is fitting negative y-values
        # use leastSquare to solve ln(|y|) = ln(|a|) + b*x
        ln_ys = [math.log(abs(y)) for y in y_coords] # convert y-values into ln(|y|)
        A = [[1,x] for x in x_coords] # build design matrix
        solution = linalg.leastSquares(A, ln_ys) # compute ln(|a|) and b
        if solution is None:
            return False
        # extract ln(|a|) and b values from solution
        ln_a, b_val = solution[0], solution[1]
        # assign self.a and self.b with right sign
        try:
            abs_a = math.exp(ln_a)
        except OverflowError:
            return False
        self.a = -abs_a if isNegative else abs_a
        self.b = b_val
        # add self.a and self.b to parameters
        self.params = [self.a, self.b]
        self.isFitted = True
        self.isAdjusted = False
        return True

    def designMatrix(self, x_coords):
        # the fit solved ln|y| = ln|a| + b*x, so the matrix is [1, x]
        return [[1, x] for x in x_coords]

    def fitSpaceResiduals(self, x_coords, y_coords):
        if not self.isFitted or self.a == 0:
            return None
        lnA = math.log(abs(self.a))
        out = []
        for i in range(len(x_coords)):
            if y_coords[i] == 0:
                return None
            out.append(math.log(abs(y_coords[i])) - (lnA + self.b * x_coords[i]))
        return out

    # 'a' was estimated as ln|a|, so its interval is multiplicative rather
    # than symmetric: a * e^(-2SE) up to a * e^(+2SE)
    def boundsFromErrors(self, errors, spread = 2):
        reach = spread * errors[0]
        if self.a >= 0:
            aBounds = (self.a * math.exp(-reach), self.a * math.exp(reach))
        else:
            aBounds = (self.a * math.exp(reach), self.a * math.exp(-reach))
        bReach = spread * errors[1]
        return [aBounds, (self.b - bReach, self.b + bReach)]

    def predict(self, x):
        if not self.isFitted:
            return None
        return self.a * math.exp(self.b * x)

    def applyParams(self):
        self.a, self.b = self.params[0], self.params[1]

    def getEquation(self, offset = 0):
        if not self.isFitted:
            return ''
        xTerm = formatXTerm(offset)
        aStr, bStr = formatNumber(self.a), formatNumber(self.b)
        if self.b == 0:
            return f'y = {aStr}'
        elif almostOne(abs(self.b)):
            sign = '-' if self.b < 0 else ''
            return f'y = {aStr} * e^({sign}{xTerm})'
        else:
            return f'y = {aStr} * e^({bStr}{xTerm})'


class PowerModel(Model):
    usesShiftedX = False
    def __init__(self):
        super().__init__()
        self.name = 'Power'
        self.paramCount = 2
        self.a, self.b = None, None

    def canFit(self, x_coords, y_coords):
        works, message = super().canFit(x_coords, y_coords)
        if not works:
            return (False, message)
        allPositiveX = all(x > 0 for x in x_coords) # checks if x-values are strictly positive
        allPositiveY = all(y > 0 for y in y_coords) # checks if y-values are strictly positive
        if not allPositiveX:
            return (False, 'All x-values must be positive')
        if not allPositiveY:
            return (False, 'All y-values must be positive')
        return (True, '')

    def fit(self, x_coords, y_coords):
        works, message = self.canFit(x_coords, y_coords)
        if not works:
            return False
        ln_xs = [math.log(abs(x)) for x in x_coords]
        ln_ys = [math.log(abs(y)) for y in y_coords]
        A = [[1,ln_x] for ln_x in ln_xs] # build design matrix
        solution = linalg.leastSquares(A, ln_ys)
        if solution is None:
            return False
        # extract ln(|a|) and b values from solution
        ln_a, b_val = solution[0], solution[1]
        # assign self.a and self.b
        try:
            self.a = math.exp(ln_a)
        except OverflowError:
            return False
        self.b = b_val
        # add self.a and self.b to parameters
        self.params = [self.a, self.b]
        self.isFitted = True
        self.isAdjusted = False
        return True

    def designMatrix(self, x_coords):
        # the fit solved ln(y) = ln(a) + b*ln(x), so the matrix is [1, ln x]
        return [[1, math.log(x)] for x in x_coords if x > 0]

    def fitSpaceResiduals(self, x_coords, y_coords):
        if not self.isFitted or self.a <= 0:
            return None
        lnA = math.log(self.a)
        out = []
        for i in range(len(x_coords)):
            if x_coords[i] <= 0 or y_coords[i] <= 0:
                return None
            out.append(math.log(y_coords[i]) -
                       (lnA + self.b * math.log(x_coords[i])))
        return out

    # 'a' was estimated as ln(a), so its interval is multiplicative rather
    # than symmetric: a * e^(-2SE) up to a * e^(+2SE)
    def boundsFromErrors(self, errors, spread = 2):
        reach = spread * errors[0]
        aBounds = (self.a * math.exp(-reach), self.a * math.exp(reach))
        bReach = spread * errors[1]
        return [aBounds, (self.b - bReach, self.b + bReach)]

    def predict(self, x):
        if not self.isFitted or x<=0:
            return None
        return self.a * (x**self.b)

    def applyParams(self):
        self.a, self.b = self.params[0], self.params[1]

    def getEquation(self, offset = 0):
        if not self.isFitted:
            return ''
        aStr, bStr = formatNumber(self.a), formatNumber(self.b)
        if self.b == 0:
                    return f'y = {aStr}'
        elif almostOne(abs(self.b)):
            return f'y = {aStr} * x'
        else:
            return f'y = {aStr} * x^({bStr})'


class LogarithmicModel(Model):
    usesShiftedX = False
    def __init__(self):
        super().__init__()
        self.name = 'Logarithmic'
        self.paramCount = 2
        self.a, self.b = None, None

    def canFit(self, x_coords, y_coords):
        works, message = super().canFit(x_coords, y_coords)
        if not works:
            return (False, message)
        allPositiveX = all(x > 0 for x in x_coords) # checks if x-values are strictly positive
        if not allPositiveX:
            return (False, 'All x-values must be positive')
        return (True, '')

    def fit(self, x_coords, y_coords):
        works, message = self.canFit(x_coords, y_coords)
        if not works:
            return False
        A = [[1, math.log(x)] for x in x_coords] # build design matrix
        solution = linalg.leastSquares(A, y_coords)
        if solution is None:
            return False
        # a and b can simply be computed with leastSquares
        self.a, self.b = solution[0], solution[1]
        self.params = [self.a, self.b]
        self.isFitted = True
        self.isAdjusted = False
        return True

    def designMatrix(self, x_coords):
        # fitted directly against ln x, so the parameters are in normal units
        return [[1, math.log(x)] for x in x_coords if x > 0]

    def fitSpaceResiduals(self, x_coords, y_coords):
        return stats.getResiduals(self, x_coords, y_coords)

    def predict(self, x):
        if not self.isFitted or x <= 0:
            return None
        return self.a + self.b * math.log(x)

    def applyParams(self):
        self.a, self.b = self.params[0], self.params[1]

    def getEquation(self, offset = 0):
        if not self.isFitted:
            return ''
        aStr, bStr = formatNumber(self.a), formatNumber(abs(self.b))
        if self.b < 0:
            return f'y = {aStr} - {bStr} * ln(x)'
        return f'y = {aStr} + {bStr} * ln(x)'


class FlatlineModel(Model):
    def __init__(self):
        super().__init__()
        self.name = 'Flatline'
        self.paramCount = 1
        self.c = None

    # not necessary since parent class can handle it, but here for style purpose
    def canFit(self, x_coords, y_coords):
        works, message = super().canFit(x_coords, y_coords)
        if not works:
            return (False, message)
        return (True,'')

    def fit(self, xs, ys):
        works, message = self.canFit(xs, ys)
        if not works:
            return False
        # For a flatline y = c, the best c is the mean (average) of all y values
        self.c = sum(ys) / len(ys)
        self.params = [self.c]
        self.isFitted = True
        self.isAdjusted = False
        return True

    def designMatrix(self, x_coords):
        # y = c is a least squares fit against a single column of ones
        return [[1] for x in x_coords]

    def fitSpaceResiduals(self, x_coords, y_coords):
        return stats.getResiduals(self, x_coords, y_coords)

    def predict(self, x):
        if not self.isFitted:
            return None
        return self.c # always returns the constant value regardless of x
    
    def applyParams(self):
        self.c = self.params[0]

    def getEquation(self, offset = 0):
        if not self.isFitted:
            return ''
        return f'y = {formatNumber(self.c)}'



def makeAllModels():
    # Returns one fresh, unfitted object of every model type.
    return [LinearModel(), QuadraticModel(), CubicModel(),
            ExponentialModel(), PowerModel(), LogarithmicModel(), FlatlineModel()]
