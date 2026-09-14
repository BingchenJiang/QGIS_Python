from qgis.core import QgsCircle
from .qgsmaptoolshapecircleabstract import QgsMapToolShapeCircleAbstract


class QgsMapToolShapeCircle2Points(QgsMapToolShapeCircleAbstract):
    def shapeCurve(self, points): return self.circleCurve(QgsCircle.from2Points(*points))
