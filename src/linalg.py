def transpose(matrix):
    rows, cols = len(matrix), len(matrix[0])
    result = []

    for col in range(cols):
        newRow = []
        for row in range(rows):
            newRow.append(matrix[row][col])
        result.append(newRow)
    return result

def multiplyMatrices(A, B):
    #A is (mxn) and B is (nxp), so answer is (mxp)
    m, n, p = len(A), len(B), len(B[0])
    result = []

    for row in range(m):
        newRow = []
        for col in range(p):
            total = 0
            for i in range(n):
                total += A[row][i]*B[i][col]
            newRow.append(total)
        result.append(newRow)
    return result

def multiplyMatrixVector(A, v):
    #A is (mxn) and v is (nx1)
    result = []
    m,n = len(A), len(v)
    for row in range(m):
        total = 0
        for col in range(n):
            total += A[row][col]*v[col]
        result.append(total)
    return result

def solveSystem(A, B):
    #solves the system of equations A(nxn) * solution = B(nx1)
    #A must be square matrix
    # A and B must be 2D list
    #returns 2D list matrix or None if no solution

    #Step 1. build augmented matrix
    augMatrix = []
    n = len(A)
    for row in range(n):
        newRow = []
        for col in range(n):
            newRow.append(A[row][col])
        newRow.append(B[row][0])
        augMatrix.append(newRow)

    #Step 2. Gaussian elimination
    #ensure each pivot is the largest value its col
    for col in range(n):
        bestRow = col
        for row in range(col+1, n):
            if abs(augMatrix[row][col]) > abs(augMatrix[bestRow][col]):
                bestRow = row
        #switch best row into current pivot position
        augMatrix[col], augMatrix[bestRow] = augMatrix[bestRow], augMatrix[col]
        #if pivot is zero, there's no solution
        if abs(augMatrix[col][col]) < 10**(-12):
            return None
        #eliminate entries below pivot
        for row in range(col+1, n):
            factor = augMatrix[row][col]/augMatrix[col][col]
            for c in range(col, n + 1):
                augMatrix[row][c] = augMatrix[row][c] - factor * augMatrix[col][c]

    #Step 3. back substitution
    solution = [0] * n
    #start with bottom row becaue it has only one unknown
    for row in range(n-1,-1,-1):
        total = augMatrix[row][n]
        for col in range(row+1, n):
            total = total - augMatrix[row][col]*solution[col]
        solution[row] = total / augMatrix[row][row]
    return solution

#solves the normal equation for least squares regression
def leastSquares(A, y):
    #convert y matrix into 2D list if it's not
    if len(y) > 0 and not isinstance(y[0], list):
        y = [[val] for val in y]
    #(A^T*A) * solution = A^T * y
    At = transpose(A)
    #left hand side
    AtA = multiplyMatrices(At, A)
    #right hand side
    Aty = multiplyMatrices(At, y)
    return solveSystem(AtA, Aty)

def identitymatrix(n):
    result = []
    for i in range(n):
        row = [1 if i == j else 0 for j in range(n)]
        result.append(row)
    return result

def invert(A):
    n = len(A)
    I = identitymatrix(n)
    # find each columns of the inverse
    cols = []
    for i in range(n):
        e = [[I[row][i]] for row in range(n)]
        solution = solveSystem(A, e)
        if solution is None:
            return None
        cols.append(solution)
    # change the list of each colums into valid matrix
    inverse = []
    for row in range(n):
        inverse.append([cols[i][row] for i in range(n)])
    return inverse