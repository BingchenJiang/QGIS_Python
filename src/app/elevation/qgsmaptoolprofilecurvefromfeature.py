from qgis.PyQt.QtCore import Qt, QPoint, pyqtSignal
from qgis.core import Qgis, QgsGeometry, QgsCsException
from qgis.gui import QgsMapTool, QgsIdentifyMenu


class QgsMapToolProfileCurveFromFeature(QgsMapTool):
    curveCaptured = pyqtSignal(QgsGeometry)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.setCursor(Qt.CrossCursor)

    def canvasPressEvent(self, event):
        if event.button() != Qt.LeftButton: return
        results = QgsIdentifyMenu.findFeaturesOnCanvas(event, self.canvas(), [Qgis.GeometryType.Line])
        if not results: return
        menu = QgsIdentifyMenu(self.canvas())
        menu.setAllowMultipleReturn(False)
        menu.setExecWithSingleResult(False)
        try: selected = menu.exec(results, self.canvas().mapToGlobal(event.pos() + QPoint(5, 5)))
        finally: menu.deleteLater()
        if not selected or not selected[0].mFeature.hasGeometry(): return
        result = selected[0]
        geometry = QgsGeometry(result.mFeature.geometry())
        try: geometry.transform(self.canvas().mapSettings().layerTransform(result.mLayer))
        except QgsCsException as error:
            self.messageEmitted.emit(str(error), Qgis.Warning)
            return
        self.curveCaptured.emit(geometry)
