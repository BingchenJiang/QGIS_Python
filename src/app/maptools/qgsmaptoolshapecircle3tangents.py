from qgis.PyQt.QtCore import Qt
from qgis.core import QgsCircle, QgsPoint, QgsGeometry, QgsLineString
from .qgsmaptoolshapecircleabstract import QgsMapToolShapeCircleAbstract


class QgsMapToolShapeCircle3Tangents(QgsMapToolShapeCircleAbstract):
    instructions = '开启线段捕捉；左键选两条切线，右键选第三条切线完成；退格退选，Esc 取消'

    def __init__(self, *args):
        super().__init__(*args)
        self.mPosPoints = []

    def circleForEdge(self, edge):
        points = self.mPoints + [self.mParentTool.mapPoint(p) for p in edge]
        def parallel(a, b, c, d):
            return abs((b.x()-a.x())*(d.y()-c.y())-(b.y()-a.y())*(d.x()-c.x())) < 1e-8
        pos = QgsPoint()
        if parallel(*points[:4]) or parallel(*points[:2], *points[4:]): pos = self.mPosPoints[0]
        elif parallel(*points[2:]): pos = self.mPosPoints[1]
        return QgsCircle.from3Tangents(*points, 1e-8, pos)

    def cadCanvasMoveEvent(self, event):
        self.mTempRubberBand.hide()
        match = self.tangentMatch(event)
        if not match.hasEdge(): return
        edge = match.edgePoints()
        curve = self.circleForEdge(edge).toLineString(self.segments()) if len(self.mPoints) == 4 else QgsLineString([QgsPoint(p) for p in edge])
        if not curve.isEmpty():
            self.mTempRubberBand.setToGeometry(QgsGeometry(curve), None)
            self.mTempRubberBand.show()

    def cadCanvasReleaseEvent(self, event):
        if not self.mManager.parentAvailable(self.mParentTool): return
        match = self.tangentMatch(event)
        if not match.hasEdge():
            self.mManager.mApp.mMessageBar.pushInfo('切线圆', '请开启捕捉并选取线段')
            return
        if event.button() == Qt.LeftButton and len(self.mPoints) < 4:
            self.mPoints.extend(self.mParentTool.mapPoint(p) for p in match.edgePoints())
            self.mPosPoints.append(self.mParentTool.mapPoint(match.point()))
        elif event.button() == Qt.RightButton and len(self.mPoints) == 4:
            curve = self.circleCurve(self.circleForEdge(match.edgePoints()))
            if curve is not None:
                self.mManager.finishShape(self, curve, event)
            else: self.mManager.mApp.mMessageBar.pushWarning('切线圆', '所选切线无法构造圆，请调整选择')

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            del self.mPoints[-2:]
            if self.mPosPoints: self.mPosPoints.pop()
            self.mTempRubberBand.hide()
            event.accept()
        else: super().keyPressEvent(event)

    def clean(self):
        self.mPosPoints.clear()
        super().clean()
