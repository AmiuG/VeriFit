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

        self.outlierIndex = None

        # the parameters the fit actually produced are kept so the graph can
        # still show the original curve after a slider has moved things
        self.originalParams = None
        self.parameterBounds = None

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
    
class InfluenceEntry:
    def __init__(self, activeIndex, row):
        self.activeIndex = activeIndex
        self.row = row
        self.winner = None
        self.winnerCv = None
        self.cvShift = None
        self.changesWinner = False

    def __repr__(self):
        return f'InfluenceEntry(row={self.row}, winner={self.winner})'

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

    # After a slider has hand-edited the parameters, CV RMSE and AICc
    # because nothing is fitted it's simply adjusted
    def rescoreAdjusted(self, result):
        y_coords = self.dataset.getRawYs()
        x_coords = self.x_coordsFor(result.model)
        result.residuals = stats.getResiduals(result.model, x_coords, y_coords)
        result.trainRmse = stats.rmse(result.residuals)
        result.r2 = stats.rSquared(result.model, x_coords, y_coords)
        result.interpretations = stats.describeResiduals(x_coords, y_coords,
                                                         result.residuals)
        result.outlierIndex = stats.outlierIndex(result.residuals)
        result.cvRmse = None
        result.aicc = None
        result.akaikeWeight = None

    # rebuilds the model exactly as it came out of the fit, so the view can
    # draw the untouched curve behind a hand-adjusted one
    def originalModelFor(self, result):
        if result.originalParams is None:
            return None
        ghost = result.model.makeBlankCopy()
        ghost.isFitted = True
        ghost.params = list(result.originalParams)
        ghost.applyParams()
        return ghost

    # predict with any model, doing the same coordinate conversion predictAt does
    def predictWith(self, model, usesShiftedX, x):
        if usesShiftedX:
            x = self.dataset.toFitX(x)
        return stats.safePredict(model, x)

    # leave one point out, refit everything, and see what changed. A ranking
    # that survives every point being removed is worth believing; one that
    # flips when a single point goes is worth doubting.
    def influenceSweep(self):
        if len(self.results) == 0:
            return None
        baselineWinner = self.results[0].model.name
        baselineCv = self.results[0].cvRmse
        active = self.dataset.getActivePoints()
        # with three points or fewer, dropping one leaves too little to fit
        if len(active) < 4:
            return None

        # the table row each active point came from, captured before anything
        # is excluded: asking mid-sweep would give the wrong answer
        rows = []
        for row in range(len(self.dataset.points)):
            if not self.dataset.points[row].isExcluded:
                rows.append(row)

        report = []
        for i in range(len(active)):
            point = active[i]
            point.isExcluded = True
            self.dataset.updateOffset()
            try:
                fresh = []
                for candidate in self.candidates:
                    fresh.append(candidate.makeBlankCopy())
                trial = AnalysisEngine(self.dataset, fresh)
                trial.analyze()
                entry = InfluenceEntry(i, rows[i])
                if len(trial.results) > 0:
                    entry.winner = trial.results[0].model.name
                    entry.winnerCv = trial.results[0].cvRmse
                    entry.changesWinner = (entry.winner != baselineWinner)
                    # how much the original winner's own score moved
                    for other in trial.results:
                        if other.model.name == baselineWinner:
                            if baselineCv is not None and other.cvRmse is not None:
                                entry.cvShift = other.cvRmse - baselineCv
                report.append(entry)
            finally:
                # the point goes back no matter what happened above
                point.isExcluded = False
                self.dataset.updateOffset()

        # the sweep refitted the shared candidate models, so put the real
        # analysis back before anything tries to draw a curve
        self.analyze()
        return (baselineWinner, report)

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
            # a model can "fit" and still be useless: on year data the power
            # model's ln(a) underflows to a = 0.0 with b = 468, so fit()
            # returns True and every prediction then overflows to None
            if stats.getResiduals(model, x_coords, y_coords) is None:
                self.unavailable.append((model.name, 'Fit was not numerically usable'))
                model.reset()
                continue
            fittedModels.append(model)

        # score each fitted models
        for model in fittedModels:
            result = self.scoreModel(model, self.x_coordsFor(model), y_coords)
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
        result.interpretations = stats.describeResiduals(x_coords, y_coords, result.residuals)
        result.outlierIndex = stats.outlierIndex(result.residuals)
        if model.params is not None:
            result.originalParams = list(model.params)
        result.standardErrors = stats.standardErrors(model, x_coords, y_coords)
        result.parameterBounds = stats.parameterBounds(model, x_coords, y_coords)
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
            result = self.results[i]
            # the color follows the model itself rather than its rank, so a
            # curve never changes color just because the ranking moved
            result.colorIndex = self.candidates.index(result.model)
            # top three models are visible
            result.isVisible = True if (i < 3) else False

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