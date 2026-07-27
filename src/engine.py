import math
import stats
from results import FitResults

# the engine will be given a dataset and fit every model possible.
# then, it will score each one, rank them by cv RMSE,
# calculate Akaike weights, assign color and report what models
# weren't used and why
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
        self.assignColors()

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
            
