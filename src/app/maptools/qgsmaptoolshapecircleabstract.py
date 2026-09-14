from src.gui.maptools.qgsmaptoolshapeabstract import QgsMapToolShapeAbstract
from qgis.core import QgsPointLocator, QgsPointXY


class EdgesOnlyFilter(QgsPointLocator.MatchFilter):
    def acceptMatch(self, match): return match.hasEdge()


class QgsMapToolShapeCircleAbstract(QgsMapToolShapeAbstract):
    def tangentMatch(self, event):
        return self.canvas().snappingUtils().snapToMap(QgsPointXY(event.mapPoint()), EdgesOnlyFilter())

    def circleCurve(self, circle):
        if circle.isEmpty(): return None
        if self.layer().crs() != self.canvas().mapSettings().destinationCrs():
            return circle.toLineString(self.segments())
        return circle.toCircularString()
