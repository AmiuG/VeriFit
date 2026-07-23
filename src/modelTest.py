import math
from models import *

def almostEqual(a, b, epsilon = 10 ** -6):
    return abs(a - b) < epsilon


def testLinearModel():
    print('Testing LinearModel...', end = ' ')
    # y = 3x + 2
    xs = [1, 2, 3, 4, 5]
    ys = []
    for x in xs:
        ys.append(3 * x + 2)
    model = LinearModel()
    assert model.fit(xs, ys) == True
    assert almostEqual(model.params[0], 2)     # constant term
    assert almostEqual(model.params[1], 3)     # slope
    assert almostEqual(model.predict(10), 32)
    print('Passed.', model.getEquation())


def testQuadraticModel():
    print('Testing QuadraticModel...', end = ' ')
    # y = 2x^2 - 5x + 1
    xs = [-2, -1, 0, 1, 2, 3]
    ys = []
    for x in xs:
        ys.append(2 * x ** 2 - 5 * x + 1)
    model = QuadraticModel()
    assert model.fit(xs, ys) == True
    assert almostEqual(model.params[0], 1)
    assert almostEqual(model.params[1], -5)
    assert almostEqual(model.params[2], 2)
    print('Passed.', model.getEquation())


def testCubicModel():
    print('Testing CubicModel...', end = ' ')
    # y = x^3 - 4x
    xs = [-3, -2, -1, 0, 1, 2, 3]
    ys = [3,1,3,5,1,3,4]
    model = CubicModel()
    assert model.fit(xs, ys) == True
    print('Passed.', model.getEquation())

def testCustomPolynomialModel():
    print('Testing CustomPolynomialModel...', end = ' ')
    xs = [-3, -2, -1, 0, 1, 2, 3]
    ys = [3,1,3,5,1,3,4]
    model = CustomPolynomialModel([2])
    assert model.fit(xs, ys) == True
    print('Passed.', model.getEquation())


def testExponentialModel():
    print('Testing ExponentialModel...', end = ' ')
    # y = 5 * e^(0.3x)
    xs = [0, 1, 2, 3, 4, 5]
    ys = []
    for x in xs:
        ys.append((-1)*5 * math.exp(0.3 * x))
    model = ExponentialModel()
    assert model.fit(xs, ys) == True
    assert almostEqual(model.a, -5)
    assert almostEqual(model.b, 0.3)
    print('Passed.', model.getEquation())

def testPowerModel():
    print('Testing PowerModel...', end = ' ')
    # y = 2 * x^1.5
    xs = [1, 2, 3, 4, 8]
    ys = []
    for x in xs:
        ys.append(2 * x ** 0.01)
    model = PowerModel()
    assert model.fit(xs, ys) == True
    assert almostEqual(model.a, 2)
    assert almostEqual(model.b, 0.01)
    print('Passed.', model.getEquation())

testLinearModel()
testQuadraticModel()
testCubicModel()
testCustomPolynomialModel()
testExponentialModel()
testPowerModel()