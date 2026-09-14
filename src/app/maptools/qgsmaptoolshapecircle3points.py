from qgis.core import QgsCircle
from .qgsmaptoolshapecircleabstract import QgsMapToolShapeCircleAbstract


class QgsMapToolShapeCircle3Points(QgsMapToolShapeCircleAbstract):
    pointCount = 3
    def shapeCurve(self, points): return self.circleCurve(QgsCircle.from3Points(*points))
