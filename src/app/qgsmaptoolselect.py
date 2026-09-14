"""Application selection tool; capture belongs to QgsMapToolSelectionHandler."""
from qgis.gui import QgsMapTool
from .qgsmaptoolselectionhandler import QgsMapToolSelectionHandler
from .qgsmaptoolselectutils import QgsMapToolSelectUtils


class QgsMapToolSelect(QgsMapTool):
    def __init__(self, canvas, mode=QgsMapToolSelectionHandler.SelectSimple):
        super().__init__(canvas)
        self.mSelectionHandler = QgsMapToolSelectionHandler(canvas)
        self.mSelectionHandler.geometryChanged.connect(self.selectFeatures)
        self.setSelectionMode(mode)

    def setSelectionMode(self, mode): self.mSelectionHandler.setSelectionMode(mode)
    def canvasPressEvent(self, event): self.mSelectionHandler.canvasPressEvent(event)
    def canvasMoveEvent(self, event): self.mSelectionHandler.canvasMoveEvent(event)
    def canvasReleaseEvent(self, event): self.mSelectionHandler.canvasReleaseEvent(event)
    def keyReleaseEvent(self, event): self.mSelectionHandler.keyReleaseEvent(event)
    def selectFeatures(self, geometry, modifiers, single):
        QgsMapToolSelectUtils.setSelectedFeatures(self.canvas(), geometry, modifiers, single)
    def deactivate(self):
        self.mSelectionHandler.cancel()
        super().deactivate()
