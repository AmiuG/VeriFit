import math
import stats

# the engine will be given a dataset and fit every model possible.
# then, it will score each one, rank them by cv RMSE,
# calculate Akaike weights, assign color and report what models
# weren't used and why
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


class AnalysisEngine:
    def __init__(self, dataset, candidates):
        self.dataset = dataset
        self.candidates = candidates
        self.results = []
        self.unavailable = []

    def analyze(self):
        # in case the data changed, reset the results and unavailable
        self.results = []
        self.unavailable = []

        fitX_coords = self.dataset.getFitXs()
        y_coords = self.dataset.getRawYs()

        # find models that cannot be fitted and fit rest
        fittedModels = []
        for model in self.candidates:
            works, message = model.canFit(fitX_coords, y_coords)
            if not works:
                self.unavailable.append((model.name, message))
                continue
            # even if the canFit return True, but fit might not work
            if not model.fit(fitX_coords, y_coords):
                self.unavailable.append((model.name, 'Could not be fitted'))
                continue
            fittedModels.append(model)

        # score each fitted models
        for model in fittedModels:
            result = self.scoreModel(model, fitX_coords, y_coords)
            self.results.append(result)

        # rank by cvRMSE, lowest to largest
        self.results.sort(key=lambda r: r.rankingScore())

        # akaike weights
        self.assignAkaikeWeights()
        # assign color
        self.assignColorsAndVisibility()

        return self.results

    def scoreModel(model, x_coords, y_coords):
        result = FitResults(model)
        result.r2 = stats.rSquared(model, x_coords, y_coords)
        result.trainRmse = stats.trainingRmse(model, x_coords, y_coords)
        result.cvRmse = stats.crossValidatedRmse(model, x_coords, y_coords)
        result.aicc = stats.aicc(model, x_coords, y_coords)
        return result

    # get aicc values of models in the order of ranking and return the weight
    def assignAkaikeWeights(self):
        aiccValues = []
        for result in self.results:
            aiccValues.append(result.aicc)
        weights = stats.akaikeWeights(aiccValues)
        for i in range(len(self.results)):
            self.results[i].akaikeWeight = weights[i]

    def assignColorsAndVisibility(self):
        for i in range(len(self.results)):
            self.results[i].colorIndex = i
            # top three models are visible
            self.results[i].isVisible is True if (i < 3) else False

    