"""Capture modes from src/app/qgsmaptoolselectionhandler.cpp (QGIS 3.34)."""
from math import sqrt
from qgis.PyQt.QtCore import QObject, Qt, QEvent, pyqtSignal
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QLabel
from qgis.core import QgsGeometry, QgsPointXY, QgsPointLocator, QgsRectangle, QgsWkbTypes, QgsUnitTypes
from qgis.gui import QgsRubberBand, QgsSnapIndicator, QgsDoubleSpinBox


class QgsDistanceWidget(QWidget):
    distanceChanged = pyqtSignal(float)
    distanceEditingFinished = pyqtSignal(float, object)
    distanceEditingCanceled = pyqtSignal()

    def __init__(self, label, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(label, self))
        self.mDistanceSpinBox = QgsDoubleSpinBox(self)
        self.mDistanceSpinBox.setRange(0, 1000000000)
        self.mDistanceSpinBox.setDecimals(6)
        self.mDistanceSpinBox.setShowClearButton(False)
        layout.addWidget(self.mDistanceSpinBox)
        self.mDistanceSpinBox.valueChanged.connect(self.distanceChanged)
        self.mDistanceSpinBox.installEventFilter(self)
        self.setFocusProxy(self.mDistanceSpinBox)

    def setDistance(self, value):
        self.mDistanceSpinBox.setValue(value)
        self.mDistanceSpinBox.selectAll()
    def distance(self): return self.mDistanceSpinBox.value()
    def eventFilter(self, watched, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                self.distanceEditingCanceled.emit()
                return True
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.mDistanceSpinBox.interpretText()
                self.distanceEditingFinished.emit(self.distance(), event.modifiers())
                return True
        return super().eventFilter(watched, event)


class QgsMapToolSelectionHandler(QObject):
    SelectSimple, SelectPolygon, SelectFreehand, SelectRadius = range(4)
    geometryChanged = pyqtSignal(object, object, bool)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.mCanvas = canvas
        self.mSelectionMode = self.SelectSimple
        self.mDistanceWidget = None
        self.mPoints = []
        self.mSelectionRubberBand = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
        self.mSelectionRubberBand.setFillColor(QColor(40, 125, 220, 60))
        self.mSelectionRubberBand.setStrokeColor(QColor(40, 125, 220))
        self.mSnapIndicator = QgsSnapIndicator(canvas)

    def setSelectionMode(self, mode):
        self.cancel()
        self.mSelectionMode = mode

    def selectionMode(self): return self.mSelectionMode

    def cancel(self):
        self.mPoints = []
        self.mSelectionRubberBand.reset(QgsWkbTypes.PolygonGeometry)
        self.mSnapIndicator.setMatch(QgsPointLocator.Match())
        if self.mDistanceWidget:
            self.mDistanceWidget.hide()
            self.mDistanceWidget.deleteLater()
            self.mDistanceWidget = None

    def polygon(self, points):
        return QgsGeometry.fromPolygonXY([points + [points[0]]]) if len(points) >= 3 else QgsGeometry()

    def geometry(self, point):
        if not self.mPoints: return QgsGeometry()
        if self.mSelectionMode == self.SelectSimple:
            return QgsGeometry.fromRect(QgsRectangle(self.mPoints[0], point))
        if self.mSelectionMode == self.SelectRadius:
            return QgsGeometry.fromPointXY(self.mPoints[0]).buffer(sqrt(self.mPoints[0].sqrDist(point)), 20)
        return self.polygon(self.mPoints + [point])

    def finish(self, geometry, modifiers, single=False):
        if not geometry.isEmpty(): self.geometryChanged.emit(geometry, modifiers, single)
        self.cancel()

    def canvasPressEvent(self, event):
        if self.mSelectionMode == self.SelectPolygon:
            if event.button() == Qt.LeftButton:
                self.mPoints.append(QgsPointXY(event.mapPoint()))
            elif event.button() == Qt.RightButton:
                self.finish(self.polygon(self.mPoints), event.modifiers())
        elif self.mSelectionMode == self.SelectSimple and event.button() == Qt.LeftButton:
            self.mPoints = [QgsPointXY(event.mapPoint())]

    def canvasMoveEvent(self, event):
        point = event.snapPoint() if self.mSelectionMode == self.SelectRadius else event.mapPoint()
        if self.mSelectionMode == self.SelectRadius:
            self.mSnapIndicator.setMatch(event.mapPointMatch())
        if not self.mPoints: return
        if self.mSelectionMode == self.SelectRadius and self.mDistanceWidget:
            self.mDistanceWidget.setDistance(sqrt(self.mPoints[0].sqrDist(point)))
            self.mDistanceWidget.setFocus(Qt.TabFocusReason)
        if self.mSelectionMode == self.SelectFreehand:
            if self.mPoints[-1].sqrDist(point) >= self.mCanvas.mapUnitsPerPixel() ** 2:
                self.mPoints.append(QgsPointXY(point))
        self.mSelectionRubberBand.setToGeometry(self.geometry(point), None)

    def canvasReleaseEvent(self, event):
        mode = self.mSelectionMode
        if mode == self.SelectPolygon: return
        if event.button() == Qt.RightButton:
            self.cancel()
            return
        if event.button() != Qt.LeftButton: return
        point = event.snapPoint() if mode == self.SelectRadius else event.mapPoint()
        if mode == self.SelectSimple:
            if not self.mPoints: return
            tolerance = self.mCanvas.mapUnitsPerPixel() * 3
            single = self.mPoints[0].sqrDist(point) < tolerance ** 2
            if single:
                tolerance = self.mCanvas.mapUnitsPerPixel() * 5
                geometry = QgsGeometry.fromRect(QgsRectangle(point.x()-tolerance, point.y()-tolerance, point.x()+tolerance, point.y()+tolerance))
            else:
                geometry = self.geometry(point)
            self.finish(geometry, event.modifiers(), single)
        elif not self.mPoints:
            self.mPoints = [QgsPointXY(point)]
            if mode == self.SelectRadius: self.createDistanceWidget()
        else:
            self.finish(self.geometry(point), event.modifiers())

    def createDistanceWidget(self):
        from .qgisapp import QgisApp
        self.mDistanceWidget = QgsDistanceWidget('选择半径：', self.mCanvas)
        self.mDistanceWidget.mDistanceSpinBox.setSuffix(' ' + QgsUnitTypes.toAbbreviatedString(self.mCanvas.mapUnits()))
        QgisApp.instance().addUserInputWidget(self.mDistanceWidget)
        self.mDistanceWidget.distanceChanged.connect(self.updateRadiusRubberband)
        self.mDistanceWidget.distanceEditingFinished.connect(self.radiusValueEntered)
        self.mDistanceWidget.distanceEditingCanceled.connect(self.cancel)
        self.mDistanceWidget.setFocus(Qt.TabFocusReason)

    def updateRadiusRubberband(self, radius):
        if self.mPoints:
            geometry = QgsGeometry.fromPointXY(self.mPoints[0]).buffer(radius, 20)
            self.mSelectionRubberBand.setToGeometry(geometry, None)

    def radiusValueEntered(self, radius, modifiers):
        if self.mPoints:
            geometry = QgsGeometry.fromPointXY(self.mPoints[0]).buffer(radius, 20)
            self.finish(geometry, modifiers)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Escape: self.cancel()
        elif event.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self.mSelectionMode == self.SelectPolygon and self.mPoints:
            self.mPoints.pop()
            self.mSelectionRubberBand.setToGeometry(self.polygon(self.mPoints), None)
