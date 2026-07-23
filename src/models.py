import math
import linalg

# turn 3.0 into '3' and 2.71828 into '2.7183' so equations look clean
def formatNumber(value):
    rounded = round(value, 4)
    if rounded == int(rounded):
        return str(int(rounded))
    return str(rounded)
# check if the value is technically one
def almostOne(value):
    return abs(value - 1) < 10 ** -10

# learned inheritence from this YouTube video https://youtu.be/RSl87lqOXDE?si=feKdyYe_9CdtmLQ7

class Model:
    def __init__(self):
        self.name = 'Model'
        self.paramCount = 0 # number of parameters model should find
        self.params = None # will eventually store the fitted coefficients
        self.isFitted = False

    # check if the model has enough amount of points for fitting
    def canFit(self, x_coords, y_coords):
        if len(x_coords) < self.paramCount:
            return (False, f'Needs at least {self.paramCount} points')
        diffXCoords = len(set(x_coords))
        if diffXCoords < self.paramCount:
            return (False, f'Needs at least {self.paramCount} different points')
        return (True, '')

    # placeholders(subclasses will fill out these functions)
    def fit(self, x_coords, y_coords):
        return False
    def predict(self, x):
        return None
    def getEquation(self):
        return ''

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
        self.params = None
        self.isFitted = False

    # checks if the model has constant term because it could affect results
    def hasConstantTerm(self):
        return 0 in self.powers

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
            return True

    # return predicted y value by the fitted model
    def predict(self, x):
        if not self.isFitted:
            return None
        total = 0
        for i in range(len(self.powers)):
            total += self.params[i]*(x**self.powers[i])
        return total

    def getEquation(self):
        if not self.isFitted:
            return ''
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
                rightHandSide += 'x'
            elif power != 0:
                rightHandSide += f'x^{power}'
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
        allPositive = all(y > 0 for y in y_coords) # checks if y-values are strictly positive
        allNegative = all(y < 0 for y in y_coords) # checks if y-values are strictly negative
        if not (allPositive or allNegative):
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
        ln_a = solution[0][0] if isinstance(solution[0], list) else solution[0]
        b_val = solution[1][0] if isinstance(solution[1], list) else solution[1]
        # assign self.a and self.b with right sign
        abs_a = math.exp(ln_a)
        self.a = -abs_a if isNegative else abs_a
        self.b = b_val
        # add self.a and self.b to parameters
        self.params = [self.a, self.b]
        self.isFitted = True
        return True

    def predict(self, x):
        if not self.isFitted:
            return None
        return self.a * math.exp(self.b * x)

    def getEquation(self):
        if not self.isFitted:
            return ''
        aStr, bStr = formatNumber(self.a), formatNumber(self.b)
        if self.b == 0:
            return f'y = {aStr}'
        elif almostOne(abs(self.b)):
            sign = '-' if self.b < 0 else ''
            return f'y = {aStr} * e^({sign}x)'
        else:
            return f'y = {aStr} * e^({bStr}x)'



def makeAllModels():
    # Returns one fresh, unfitted object of every model type.
    # Later steps will loop over this list to test every model at once.
    return [LinearModel(), QuadraticModel(), CubicModel()]
        



    

    
