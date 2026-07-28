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

        self.offset = 0
        # in case the user turns off viewing a model in graph
        self.isVisible = False
        self.colorIndex = None

    def rankingScore(self):
        # the engine sorts models by cross-validated RMSE, lowest first
        # models with no CV score should be at last, so we return
        # large number(infinity) instead of None.
        if self.cvRmse == None:
            return float('inf')
        return self.cvRmse

    def getEquation(self):
        return self.model.getEquation(self.offset)

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
        self.tieMessage = str()

    # pick what llist of x-values a model should be fitted on
    # polynomials are okay if x values are shifter, but it's not for power and logarithmic
    def x_coordsFor(self, model):
        if model.usesShiftedX:
            return self.dataset.getFitXs()
        return self.dataset.getRawXs()
    
    # gives the offset a model's printed equation has to show
    def offsetFor(self, model):
        if model.usesShiftedX:
            return self.dataset.xOffset
        return 0

    def predictAt(self, result, x):
        if result.model.usesShiftedX:
            x = self.dataset.toFitX(x)
        return stats.safePredict(result.model, x)
    
    def analyze(self):
        # in case the data changed, reset the results and unavailable
        self.results = []
        self.unavailable = []

        y_coords = self.dataset.getRawYs()

        # find models that cannot be fitted and fit rest
        fittedModels = []
        for model in self.candidates:
            model.reset()
            x_coords = self.x_coordsFor(model)
            works, message = model.canFit(x_coords, y_coords)
            if not works:
                self.unavailable.append((model.name, message))
                continue
            # even if the canFit return True, but fit might not work
            if not model.fit(x_coords, y_coords):
                self.unavailable.append((model.name, 'Could not be fitted'))
                continue
            fittedModels.append(model)

        # score each fitted models
        for model in fittedModels:
            result = self.scoreModel(model, x_coords, y_coords)
            self.results.append(result)

        # rank by cvRMSE, lowest to largest
        self.results.sort(key=lambda r: r.rankingScore())

        # akaike weights
        self.assignAkaikeWeights()
        # assign color
        self.assignColorsAndVisibility()
        self.tieMessage = self.detectTies()

        return self.results

    def scoreModel(self, model, x_coords, y_coords):
        result = FitResults(model)
        result.offset = self.offsetFor(model)
        result.residuals = stats.getResiduals(model, x_coords, y_coords)
        result.r2 = stats.rSquared(model, x_coords, y_coords)
        result.trainRmse = stats.rmse(result.residuals)
        # cvRMSE and AICc will be left blank on an adjusted model
        if model.isAdjusted:
            return result
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
            self.results[i].isVisible = True if (i < 3) else False

    # detect if the best model and second model are technically tied
    # then, it will recommend whichever is simpler
    def detectTies(self):
        if len(self.results) < 2:
            return str()

        best = self.results[0]
        second = self.results[1]
        isClose = False

        if best.akaikeWeight is not None and second.akaikeWeight is not None:
            # the program will not single out the winner if the second model
            # is supported by akaike by at least 25%
            # the fact that second beat the best in akaikeWeight means they're close
            if (second.akaikeWeight >= 0.25) or (second.akaikeWeight > best.akaikeWeight):
                isClose = True
        else:
            # in case akaikeWeights are not calculated
            if best.cvRmse is not None and second.cvRmse is not None:
                    gap = abs(second.cvRmse - best.cvRmse)
                    reference = max(best.cvRmse, 10 ** -9)
                    if gap / reference <= 0.10:
                        isClose = True

        if isClose:
            simpler = self.simplerOf(best, second)
            return (f'{best.model.name} and {second.model.name} perform '
                    f'almost identically. The simpler model '
                    f'({simpler.model.name}) is preferred.')

        return str()

    def simplerOf(self, resultA, resultB):
        if resultA.model.paramCount < resultB.model.paramCount:
            return resultA
        else:
            return resultB