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
