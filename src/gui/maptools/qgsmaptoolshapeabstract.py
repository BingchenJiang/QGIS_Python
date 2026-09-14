"""Shape capture adapter, corresponding to gui/maptools/qgsmaptoolshapeabstract.

QGIS 3.34 does not bind QgsMapToolShapeAbstract or its registry. This adapter
uses native CAD events, geometry constructors and a native capture parent.
"""
from qgis.PyQt import sip
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import Qgis, QgsGeometry, QgsPointXY, QgsSettings
from qgis.gui import QgsMapToolAdvancedDigitizing, QgsRubberBand, QgsSpinBox


class QgsMapToolShapeAbstract(QgsMapToolAdvancedDigitizing):
    pointCount = 2
    regularPolygon = False

    def __init__(self, toolId, parentTool, manager):
        super().__init__(parentTool.canvas(), manager.mApp.mAdvancedDigitizingDockWidget)
        self.mId, self.mParentTool, self.mManager = toolId, parentTool, manager
        self.mPoints, self.mLastPoint = [], None
        self.mNumberSidesSpinBox = None
        self.mNumberSides = 6
        self.mTempRubberBand = QgsRubberBand(self.canvas(), Qgis.GeometryType.Line)
        self.mTempRubberBand.setColor(QColor(255, 100, 30, 220))
        self.mTempRubberBand.setWidth(2)
        self.mTempRubberBand.hide()
        self.setCursor(Qt.CrossCursor)

    def layer(self): return self.mParentTool.layer()

    def activate(self):
        super().activate()
        if self.regularPolygon:
            self.mNumberSidesSpinBox = QgsSpinBox()
            self.mNumberSidesSpinBox.setRange(3, 99999999)
            self.mNumberSidesSpinBox.setPrefix('边数：')
            self.mNumberSidesSpinBox.setValue(self.mNumberSides)
            self.mNumberSidesSpinBox.valueChanged.connect(self.setNumberSides)
            self.mManager.mApp.addUserInputWidget(self.mNumberSidesSpinBox)

    def setNumberSides(self, count):
        self.mNumberSides = count
        self.updatePreview()

    def segments(self):
        return max(12, QgsSettings().value('qgis/digitizing/offset_quad_seg', 8, type=int) * 12)

    def shapeCurve(self, points): raise NotImplementedError

    def updatePreview(self):
        self.mTempRubberBand.hide()
        if not self.mPoints or self.mLastPoint is None: return
        points = self.mPoints + [self.mLastPoint]
        if len(points) != self.pointCount: return
        curve = self.shapeCurve(points)
        if curve is None or curve.isEmpty(): return
        self.mTempRubberBand.setToGeometry(QgsGeometry(curve), None)
        self.mTempRubberBand.show()

    def cadCanvasMoveEvent(self, event):
        self.mLastPoint = self.mParentTool.mapPoint(event)
        self.updatePreview()

    def cadCanvasReleaseEvent(self, event):
        if not self.mManager.parentAvailable(self.mParentTool):
            self.clean()
            self.mManager.mApp.mMessageBar.pushWarning('形状数字化', '目标图层或捕获工具已不可用')
            return
        point = self.mParentTool.mapPoint(event)
        if event.button() == Qt.LeftButton:
            if len(self.mPoints) < self.pointCount - 1: self.mPoints.append(point)
            self.mLastPoint = point
            self.updatePreview()
        elif event.button() == Qt.RightButton:
            if len(self.mPoints) != self.pointCount - 1:
                self.clean()
                return
            curve = self.shapeCurve(self.mPoints + [point])
            if curve is None or curve.isEmpty():
                self.mManager.mApp.mMessageBar.pushWarning('形状数字化', '无法构造形状，请调整位置（避免重合点或共线点）')
                return
            if curve.length() <= 0: return
            self.mManager.finishShape(self, curve, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.clean()
            self.cadDockWidget().clearPoints()
            event.accept()
        elif event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            if self.mPoints: self.mPoints.pop()
            self.updatePreview()
            event.accept()
        else: super().keyPressEvent(event)

    def clean(self):
        self.mPoints.clear()
        self.mLastPoint = None
        self.mTempRubberBand.reset(Qgis.GeometryType.Line)
        self.mTempRubberBand.hide()

    def deactivate(self):
        self.clean()
        if self.mNumberSidesSpinBox and not sip.isdeleted(self.mNumberSidesSpinBox):
            self.mNumberSidesSpinBox.deleteLater()
        self.mNumberSidesSpinBox = None
        super().deactivate()

    def dispose(self):
        self.clean()
        if not sip.isdeleted(self.mTempRubberBand):
            self.canvas().scene().removeItem(self.mTempRubberBand)
            sip.delete(self.mTempRubberBand)
