from qgis.core import QgsEllipse
from .qgsmaptoolshapeellipseabstract import QgsMapToolShapeEllipseAbstract


class QgsMapToolShapeEllipseExtent(QgsMapToolShapeEllipseAbstract):
    def shapeCurve(self, points): return self.ellipseCurve(QgsEllipse.fromExtent(*points))
