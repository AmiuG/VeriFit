# tests.py
#
# checks the math half of VeriFit against answers worked out by hand.
# cmu_graphics is not needed, so this runs anywhere plain Python runs:
#
#     python3 src/tests.py

import linalg


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


def main():
    testLinalg()
    print('All tests passed!')


main()
