import math

class DataPoint:
    def __init__(self, x, y):
        self.x, self.y = x, y
        # an excluded point will still appear in the table and graph, but models with
        # ignore it. This boolean value records whether this point should be ignored.
        self.isExcluded = False 

    def __repr__(self):
        if self.isExcluded:
            return f'({self.x}, {self.y}) [excluded]'
        else:
            return f'({self.x}, {self.y})'

# learned about exception in https://docs.python.org/3/tutorial/errors.html
# user will type in to table, so everything will be string
# this function will return (True, number) if the string is number
def parseNumber(text):
    text = text.strip()
    if text == str():
        return (False, 'Cell is empty')
    try:
        value = float(text)
    except ValueError:
        return (False, f'"{text}" is not a number')
    # blocks 'nan' and 'inf' case of float
    if math.isnan(value):
        return (False, 'Not a number')
    if math.isinf(value):
        return (False, 'Number is too large')

    return (True, value)

# Dataset class will manage:
#   active and excluded points
#   data editing
#   undo history
#   x-coordinate shifiting
#   ranges
#   warnings
#   validation
class Dataset:
    # if the given value is larger than this value,
    # we will shift the values before fitting to avoid error
    largestX = 1000

    def __init__(self, x_coords = None, y_coords = None):
        self.points = []
        self.undoStack = []
        self.xOffset = 0
        if (x_coords is not None) and (y_coords is not None):
            for i in range(len(x_coords)):
                self.points.append(DataPoint(x_coords[i], y_coords[i]))
        self.updateOffset()

    # Basic information about the dataset
    def getPointCount(self):
        return len(self.points)
    def getActivePoints(self):
        active = []
        for point in self.points:
            if not point.isExcluded:
                active.append(point)
        return active
    def getActiveCount(self):
        return len(self.getActivePoints())
    # returns the original x-values of active points
    def getRawXs(self):
        x_coords = []
        for point in self.getActivePoints():
            x_coords.append(point.x)
        return x_coords
    # returns the original y-values of active points
    def getRawYs(self):
        y_coords = []
        for point in self.getActivePoints():
            y_coords.append(point.y)
        return y_coords
    # returns the x-values that are shifted by self.xOffset to feed models
    def getFitXs(self):
        x_coords = []
        for point in self.getActivePoints():
            x_coords.append(point.x - self.xOffset)
        return x_coords
    # returns if the x-values are shifted by self.xOffset
    def usesOffset(self):
        return self.xOffset != 0

    def updateOffset(self):
        rawX_coords = self.getRawXs()
        # checks whether there are no active x-values
        if len(rawX_coords):
            self.xOffset = 0
            return
        # checks whether largest x value is larger than 1000
        biggest = 0
        for x in rawX_coords:
            if abs(x) > biggest:
                biggest = abs(x)
        if biggest <= Dataset.largestX:
            self.xOffset = 0
        else:
            # shifts the data points to sit aroung the origin
            avg = sum(rawX_coords) // len(rawX_coords)
            self.xOffset = avg


    
    
            


