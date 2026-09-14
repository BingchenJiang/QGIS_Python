from qgis.core import QgsEllipse
from .qgsmaptoolshapeellipseabstract import QgsMapToolShapeEllipseAbstract


class QgsMapToolShapeEllipseCenter2Points(QgsMapToolShapeEllipseAbstract):
    pointCount = 3
    def shapeCurve(self, points): return self.ellipseCurve(QgsEllipse.fromCenter2Points(*points))
