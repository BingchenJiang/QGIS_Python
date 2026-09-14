from qgis.core import QgsRegularPolygon
from .qgsmaptoolshaperegularpolygonabstract import QgsMapToolShapeRegularPolygonAbstract


class QgsMapToolShapeRegularPolygonCenterPoint(QgsMapToolShapeRegularPolygonAbstract):
    def shapeCurve(self, points): return self.polygonCurve(QgsRegularPolygon(*points, self.mNumberSides, QgsRegularPolygon.CircumscribedCircle))
