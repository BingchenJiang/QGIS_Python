from qgis.gui import QgsMapToolCapture
from .qgsmaptoolsplitfeatures import _GeometryEditCapture


class QgsMapToolAddPart(_GeometryEditCapture):
    def __init__(self, canvas, cadDock): super().__init__(canvas, cadDock, 'addPart', QgsMapToolCapture.CaptureNone)
