from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.core import Qgis, QgsGeometry
from qgis.gui import QgsMapToolCapture


class QgsMapToolProfileCurve(QgsMapToolCapture):
    curveCaptured = pyqtSignal(QgsGeometry)

    def __init__(self, canvas, cadDock):
        super().__init__(canvas, cadDock, QgsMapToolCapture.CaptureLine)

    def layer(self): return None
    def capabilities(self): return QgsMapToolCapture.SupportsCurves
    def supportsTechnique(self, technique): return technique != Qgis.CaptureTechnique.Shape

    def cadCanvasReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            curve = self.captureCurve()
            geometry = QgsGeometry(curve.clone()) if curve and curve.numPoints() >= 2 else None
            self.stopCapturing()
            if geometry is not None: self.curveCaptured.emit(geometry)
        else: super().cadCanvasReleaseEvent(event)
