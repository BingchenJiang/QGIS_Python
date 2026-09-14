from qgis.core import QgsQuadrilateral
from .qgsmaptoolshaperectangleabstract import QgsMapToolShapeRectangleAbstract


class QgsMapToolShapeRectangle3Points(QgsMapToolShapeRectangleAbstract):
    pointCount = 3
    def shapeCurve(self, points):
        mode = QgsQuadrilateral.Distance if self.mId.endswith('distance') else QgsQuadrilateral.Projected
        return self.rectangleCurve(QgsQuadrilateral.rectangleFrom3Points(*points, mode))
