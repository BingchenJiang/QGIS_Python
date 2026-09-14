from qgis.core import QgsEllipse
from .qgsmaptoolshapeellipseabstract import QgsMapToolShapeEllipseAbstract


class QgsMapToolShapeEllipseFoci(QgsMapToolShapeEllipseAbstract):
    pointCount = 3
    def shapeCurve(self, points): return self.ellipseCurve(QgsEllipse.fromFoci(*points))
