from qgis.core import QgsQuadrilateral
from .qgsmaptoolshaperectangleabstract import QgsMapToolShapeRectangleAbstract


class QgsMapToolShapeRectangleExtent(QgsMapToolShapeRectangleAbstract):
    def shapeCurve(self, points): return self.rectangleCurve(QgsQuadrilateral.rectangleFromExtent(*points))
