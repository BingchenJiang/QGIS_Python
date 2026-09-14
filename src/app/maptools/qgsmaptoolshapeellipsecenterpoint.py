from qgis.core import QgsEllipse
from .qgsmaptoolshapeellipseabstract import QgsMapToolShapeEllipseAbstract


class QgsMapToolShapeEllipseCenterPoint(QgsMapToolShapeEllipseAbstract):
    def shapeCurve(self, points): return self.ellipseCurve(QgsEllipse.fromCenterPoint(*points))
