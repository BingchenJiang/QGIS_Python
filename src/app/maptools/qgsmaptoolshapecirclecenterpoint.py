from qgis.core import QgsCircle
from .qgsmaptoolshapecircleabstract import QgsMapToolShapeCircleAbstract


class QgsMapToolShapeCircleCenterPoint(QgsMapToolShapeCircleAbstract):
    def shapeCurve(self, points): return self.circleCurve(QgsCircle.fromCenterPoint(*points))
