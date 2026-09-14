from math import sqrt
from qgis.PyQt import sip
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsPoint, QgsCircularString, QgsLineString, QgsGeometry, QgsGeometryUtils
from qgis.gui import QgsDoubleSpinBox
from src.gui.maptools.qgsmaptoolshapeabstract import QgsMapToolShapeAbstract


class QgsMapToolShapeCircularStringRadius(QgsMapToolShapeAbstract):
    instructions = '左键起点、终点；输入半径并移动选择弧侧，再左键确认；可继续下一段，右键完成已确认弧段；退格撤段，Esc 取消'

    def __init__(self, *args):
        super().__init__(*args)
        self.mTemporaryEndPoint = None
        self.mRadiusSpinBox, self.mRadius = None, 0.0

    def deleteRadiusSpinBox(self):
        if self.mRadiusSpinBox is not None and not sip.isdeleted(self.mRadiusSpinBox): self.mRadiusSpinBox.deleteLater()
        self.mRadiusSpinBox = None

    def updateRadiusFromSpinBox(self, radius):
        self.mRadius = radius
        self.updatePreview()

    def updatePreview(self):
        self.mTempRubberBand.hide()
        if not self.mPoints: return
        points = self.mPoints[:]
        if self.mTemporaryEndPoint is not None and self.mLastPoint is not None:
            ok, middle = QgsGeometryUtils.segmentMidPoint(points[-1], self.mTemporaryEndPoint, self.mRadius, self.mLastPoint)
            if not ok: return
            points.extend((middle, self.mTemporaryEndPoint))
        if len(points) >= 3:
            curve = QgsCircularString()
            curve.setPoints(points)
        elif self.mLastPoint is not None:
            curve = QgsLineString([points[-1], self.mLastPoint])
        else: return
        self.mTempRubberBand.setToGeometry(QgsGeometry(curve), None)
        self.mTempRubberBand.show()

    def cadCanvasMoveEvent(self, event):
        self.mLastPoint = self.mParentTool.mapPoint(event)
        self.updatePreview()

    def cadCanvasReleaseEvent(self, event):
        if not self.mManager.parentAvailable(self.mParentTool): return
        point = self.mParentTool.mapPoint(event)
        self.mLastPoint = point
        if event.button() == Qt.LeftButton:
            if not self.mPoints: self.mPoints.append(point)
            elif self.mTemporaryEndPoint is None:
                minimum = sqrt(self.mPoints[-1].distanceSquared(point))/2
                if minimum == 0: return
                self.mTemporaryEndPoint = point
                self.mRadius = minimum*1.1
                self.mRadiusSpinBox = QgsDoubleSpinBox()
                self.mRadiusSpinBox.setDecimals(8)
                self.mRadiusSpinBox.setRange(minimum, max(minimum*10, 99999999))
                self.mRadiusSpinBox.setPrefix('圆弧半径：')
                self.mRadiusSpinBox.setValue(self.mRadius)
                self.mRadiusSpinBox.valueChanged.connect(self.updateRadiusFromSpinBox)
                self.mManager.mApp.addUserInputWidget(self.mRadiusSpinBox)
            else:
                ok, middle = QgsGeometryUtils.segmentMidPoint(self.mPoints[-1], self.mTemporaryEndPoint, self.mRadius, point)
                if ok:
                    self.mPoints.extend((middle, self.mTemporaryEndPoint))
                    self.mTemporaryEndPoint = None
                    self.deleteRadiusSpinBox()
            self.updatePreview()
        elif event.button() == Qt.RightButton:
            if len(self.mPoints) >= 3:
                curve = QgsCircularString()
                curve.setPoints(self.mPoints)
                self.mManager.finishShape(self, curve, event)
            else: self.clean()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            if self.mTemporaryEndPoint is not None:
                self.mTemporaryEndPoint = None
                self.deleteRadiusSpinBox()
            elif len(self.mPoints) >= 3: del self.mPoints[-2:]
            else: self.mPoints.clear()
            self.updatePreview()
            event.accept()
        else: super().keyPressEvent(event)

    def clean(self):
        self.deleteRadiusSpinBox()
        self.mTemporaryEndPoint = None
        super().clean()
