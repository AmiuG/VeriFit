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

