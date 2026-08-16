# tests.py
#
# checks the math half of VeriFit against answers worked out by hand.
# cmu_graphics is not needed, so this runs anywhere plain Python runs:
#
#     python3 src/tests.py

import math
import linalg
import models


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


def main():
    testLinalg()
    testPolynomialModels()
    testCurvedModels()
    testAdjusting()
    print('All tests passed!')


main()
