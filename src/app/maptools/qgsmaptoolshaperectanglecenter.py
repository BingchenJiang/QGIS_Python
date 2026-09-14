from qgis.core import QgsQuadrilateral
from .qgsmaptoolshaperectangleabstract import QgsMapToolShapeRectangleAbstract


class QgsMapToolShapeRectangleCenter(QgsMapToolShapeRectangleAbstract):
    def shapeCurve(self, points): return self.rectangleCurve(QgsQuadrilateral.rectangleFromCenterPoint(*points))
