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
