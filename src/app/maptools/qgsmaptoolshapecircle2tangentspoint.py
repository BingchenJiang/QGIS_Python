from math import hypot
from qgis.PyQt import sip
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsCircle, QgsPoint, QgsPointXY, QgsGeometry, QgsLineString
from qgis.gui import QgsDoubleSpinBox
from .qgsmaptoolshapecircleabstract import QgsMapToolShapeCircleAbstract


class QgsMapToolShapeCircle2TangentsPoint(QgsMapToolShapeCircleAbstract):
    instructions = '开启线段捕捉；左键选两条相交切线，输入半径，移动选择圆心候选，右键完成；退格退选，Esc 取消'

    def __init__(self, *args):
        super().__init__(*args)
        self.mRadius, self.mRadiusSpinBox = 1.0, None
        self.mCenters = []

    def deleteRadiusSpinBox(self):
        if self.mRadiusSpinBox is not None and not sip.isdeleted(self.mRadiusSpinBox): self.mRadiusSpinBox.deleteLater()
        self.mRadiusSpinBox = None

    def getPossibleCenter(self):
        self.mCenters.clear()
        if len(self.mPoints) != 4 or self.mRadius <= 0: return
        a, b, c, d = self.mPoints
        dx1, dy1, dx2, dy2 = b.x()-a.x(), b.y()-a.y(), d.x()-c.x(), d.y()-c.y()
        length1, length2 = hypot(dx1, dy1), hypot(dx2, dy2)
        if min(length1, length2) == 0: return
        nx1, ny1, nx2, ny2 = -dy1/length1, dx1/length1, -dy2/length2, dx2/length2
        det = nx1*ny2-ny1*nx2
        if abs(det) < 1e-12: return
        # Intersections of the two pairs of offset supporting lines, as upstream.
        for side1 in (-1, 1):
            for side2 in (-1, 1):
                v1 = nx1*a.x()+ny1*a.y()+side1*self.mRadius
                v2 = nx2*c.x()+ny2*c.y()+side2*self.mRadius
                self.mCenters.append(QgsPoint((v1*ny2-ny1*v2)/det, (nx1*v2-v1*nx2)/det))

    def radiusSpinBoxChanged(self, radius):
        self.mRadius = radius
        self.getPossibleCenter()
        self.updatePreview()

    def circleAt(self, point):
        if not self.mCenters: return None
        center = min(self.mCenters, key=lambda p: p.distanceSquared(point))
        return self.circleCurve(QgsCircle(center, self.mRadius))

    def updatePreview(self):
        self.mTempRubberBand.hide()
        if self.mLastPoint is None: return
        curve = self.circleAt(self.mLastPoint)
        if curve is not None:
            self.mTempRubberBand.setToGeometry(QgsGeometry(curve), None)
            self.mTempRubberBand.show()

    def cadCanvasMoveEvent(self, event):
        self.mLastPoint = QgsPoint(event.mapPoint())
        if len(self.mPoints) == 4:
            self.updatePreview()
        else:
            self.mTempRubberBand.hide()
            match = self.tangentMatch(event)
            if match.hasEdge():
                self.mTempRubberBand.setToGeometry(QgsGeometry(QgsLineString([QgsPoint(p) for p in match.edgePoints()])), None)
                self.mTempRubberBand.show()

    def cadCanvasReleaseEvent(self, event):
        if not self.mManager.parentAvailable(self.mParentTool): return
        if event.button() == Qt.LeftButton and len(self.mPoints) < 4:
            match = self.tangentMatch(event)
            if not match.hasEdge():
                self.mManager.mApp.mMessageBar.pushInfo('切线圆', '请开启捕捉并选取线段')
                return
            self.mPoints.extend(QgsPoint(p) for p in match.edgePoints())
            if len(self.mPoints) == 4:
                self.getPossibleCenter()
                if not self.mCenters:
                    del self.mPoints[-2:]
                    self.mManager.mApp.mMessageBar.pushWarning('切线圆', '切线平行或退化，请重选第二条切线')
                    return
                self.mRadiusSpinBox = QgsDoubleSpinBox()
                self.mRadiusSpinBox.setRange(0, 99999999)
                self.mRadiusSpinBox.setDecimals(6)
                self.mRadiusSpinBox.setPrefix('圆半径：')
                self.mRadiusSpinBox.setValue(self.mRadius)
                self.mRadiusSpinBox.valueChanged.connect(self.radiusSpinBoxChanged)
                self.mManager.mApp.addUserInputWidget(self.mRadiusSpinBox)
        elif event.button() == Qt.RightButton and len(self.mPoints) == 4:
            curve = self.circleAt(QgsPoint(event.mapPoint()))
            if curve is not None: self.mManager.finishShape(self, curve, event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            del self.mPoints[-2:]
            self.mCenters.clear()
            self.deleteRadiusSpinBox()
            self.mTempRubberBand.hide()
            event.accept()
        else: super().keyPressEvent(event)

    def clean(self):
        self.deleteRadiusSpinBox()
        self.mCenters.clear()
        super().clean()
