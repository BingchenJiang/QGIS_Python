"""QgsMeasureTool: snapped points, live results, right-click finish and undo."""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsPointXY, QgsWkbTypes
from qgis.gui import QgsMapTool, QgsRubberBand, QgsSnapIndicator


class QgsMeasureTool(QgsMapTool):
    def __init__(self, canvas, measureArea=False, app=None, measureMode=None):
        super().__init__(canvas)
        self.mCanvas = canvas
        self.mApp = app or canvas.window()
        self.mMeasureArea = measureArea
        self.mMeasureMode = measureMode or ('area' if measureArea else 'distance')
        self.mPoints, self.mDone = [], True
        self.mRubberBand = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry if measureArea else QgsWkbTypes.LineGeometry)
        self.mRubberBand.setColor(QColor(230, 100, 35, 120))
        self.mRubberBand.setWidth(2)
        self.mSnapIndicator = QgsSnapIndicator(canvas)
        from .qgsmeasuredialog import QgsMeasureDialog
        self.mDialog = QgsMeasureDialog(self)
        canvas.destinationCrsChanged.connect(self.updateSettings)

    def measureArea(self): return self.mMeasureArea
    def done(self): return self.mDone
    def points(self): return list(self.mPoints)
    def restart(self):
        self.mPoints.clear()
        self.mDone = False
        self.updateRubberBand()
    def addPoint(self, point):
        if self.mDone: self.restart()
        self.mPoints.append(QgsPointXY(point))
        self.mDone = (self.mMeasureMode == 'angle' and len(self.mPoints) >= 3) or (self.mMeasureMode == 'bearing' and len(self.mPoints) >= 2)
        self.updateRubberBand()
    def undo(self):
        if self.mPoints: self.mPoints.pop()
        self.mDone = False
        self.updateRubberBand()
    def updateRubberBand(self, temporaryPoint=None):
        points = self.points()
        if temporaryPoint is not None and points: points.append(temporaryPoint)
        self.mRubberBand.reset(QgsWkbTypes.PolygonGeometry if self.mMeasureArea else QgsWkbTypes.LineGeometry)
        for point in points: self.mRubberBand.addPoint(point, False)
        self.mRubberBand.show()
        self.mRubberBand.updatePosition()
        self.mDialog.updateMeasurements(points)
    def canvasMoveEvent(self, event):
        point = event.snapPoint()
        self.mSnapIndicator.setMatch(event.mapPointMatch())
        if not self.mDone: self.updateRubberBand(point)
    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton: self.addPoint(event.snapPoint())
        elif event.button() == Qt.RightButton:
            if self.mMeasureMode in ('angle', 'bearing') and len(self.mPoints) == (2 if self.mMeasureMode == 'angle' else 1):
                self.addPoint(event.snapPoint())
            self.mDone = True
            self.updateRubberBand()
        self.mDialog.show()
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: self.restart()
        elif event.key() in (Qt.Key_Backspace, Qt.Key_Delete): self.undo()
        else: super().keyPressEvent(event)
    def updateSettings(self, *args): self.mDialog.updateMeasurements(self.points())
    def activate(self):
        super().activate()
        self.mDialog.show()
        self.updateSettings()
    def deactivate(self):
        self.mDialog.hide()
        self.mRubberBand.hide()
        self.mSnapIndicator.setVisible(False)
        super().deactivate()
