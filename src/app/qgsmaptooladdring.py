from qgis.gui import QgsMapToolCapture
from .qgsmaptoolsplitfeatures import _GeometryEditCapture


class QgsMapToolAddRing(_GeometryEditCapture):
    def __init__(self, canvas, cadDock): super().__init__(canvas, cadDock, 'addRing', QgsMapToolCapture.CapturePolygon)
