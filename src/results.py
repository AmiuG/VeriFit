class FitResults:
    def __init__(self, model):
        self.model = model
        # scores
        self.r2 = None
        self.trainRmse = None
        self.cvRmse = None
        self.aicc = None
        self.akaikeWeight = None

        # these values will be later filled by score models
        self.residuals = None
        self.standardErrors = None
        self.interpretations = []

        # in case the user turns off viewing a model in graph
        self.isVisible = False

    def rankingScore(self):
        # the engine sorts models by cross-validated RMSE, lowest first
        # models with no CV score should be at last, so we return
        # large number(infinity) instead of None.
        if self.cvRmse == None:
            return float('inf')
        return self.cvRmse

    # returns True or False whether the values are adjusted
    def isAdjusted(self):
        return self.model.isAdjusted

    def __repr__(self):
        return f'FitResult({self.model.name}, cvRmse={self.cvRmse})'