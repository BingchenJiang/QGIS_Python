from qgis.core import QgsRegularPolygon
from .qgsmaptoolshaperegularpolygonabstract import QgsMapToolShapeRegularPolygonAbstract


class QgsMapToolShapeRegularPolygonCenterCorner(QgsMapToolShapeRegularPolygonAbstract):
    def shapeCurve(self, points): return self.polygonCurve(QgsRegularPolygon(*points, self.mNumberSides, QgsRegularPolygon.InscribedCircle))
