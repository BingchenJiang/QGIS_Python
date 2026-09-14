"""QGIS 3.34 Processing locator, excluding GPS from the desktop search.

Based on python/plugins/processing/gui/AlgorithmLocatorFilter.py, GPL-2.0-or-later.
The installed Processing package is unchanged.
"""
from qgis.core import QgsApplication, QgsProcessingAlgorithm, QgsLocatorResult, QgsStringUtils
from processing.gui.AlgorithmLocatorFilter import AlgorithmLocatorFilter as UpstreamAlgorithmLocatorFilter
from processing.core.ProcessingConfig import ProcessingConfig


class AlgorithmLocatorFilter(UpstreamAlgorithmLocatorFilter):
    def clone(self): return AlgorithmLocatorFilter()

    def fetchResults(self, string, context, feedback):
        query = string.lower()
        if not query and not context.usingPrefix: return
        for algorithm in QgsApplication.processingRegistry().algorithms():
            if feedback.isCanceled(): break
            if any(part in algorithm.id().lower() for part in ('gps', 'gpx')): continue
            if algorithm.flags() & QgsProcessingAlgorithm.FlagHideFromToolbox: continue
            if not ProcessingConfig.getSetting(ProcessingConfig.SHOW_ALGORITHMS_KNOWN_ISSUES) and algorithm.flags() & QgsProcessingAlgorithm.FlagKnownIssues: continue
            result = QgsLocatorResult()
            result.filter = self
            result.displayString = algorithm.displayName()
            result.icon = algorithm.icon()
            result.userData = algorithm.id()
            tags = list(algorithm.tags()) + [algorithm.group()]
            if algorithm.provider(): tags.append(algorithm.provider().name())
            tagScore = 1 if any(query in tag.lower() for tag in tags) else 0
            result.score = QgsStringUtils.fuzzyScore(result.displayString, query) * .5 + tagScore * .5 if query else 1
            if result.score > 0: self.resultFetched.emit(result)
