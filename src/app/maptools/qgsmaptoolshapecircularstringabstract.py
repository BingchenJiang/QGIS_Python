"""Circular-string shared R-key center/radius aid, as in the native tool."""
from qgis.PyQt import sip
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsCircle, QgsCircularString, QgsPointXY, QgsGeometry, Qgis
from qgis.gui import QgsRubberBand
from src.gui.maptools.qgsmaptoolshapeabstract import QgsMapToolShapeAbstract


class QgsMapToolShapeCircularStringAbstract(QgsMapToolShapeAbstract):
    continuePreviousCurve = True

    def activate(self):
        super().activate()
        curve = self.mParentTool.captureCurve()
        if not self.mPoints and curve is not None and not curve.isEmpty():
            point = curve.endPoint()
            transform = self.canvas().mapSettings().layerTransform(self.layer())
            if transform.isValid() and not transform.isShortCircuited(): point.transform(transform)
            self.mPoints.append(point)
            self.mLastPoint = point

    def __init__(self, *args):
        super().__init__(*args)
        self.mShowCenterPointRubberBand = False
        self.mCenterPointRubberBand = QgsRubberBand(self.canvas(), Qgis.GeometryType.Polygon)
        self.mCenterPointRubberBand.setColor(QColor(255, 100, 30, 80))
        self.mCenterPointRubberBand.setStrokeColor(QColor(255, 100, 30, 200))
        self.mCenterPointRubberBand.hide()

    def updateCenterPointRubberBand(self, points):
        self.mCenterPointRubberBand.hide()
        if not self.mShowCenterPointRubberBand or len(points) != 3: return
        circle = QgsCircle.from3Points(*points)
        if circle.isEmpty(): return
        arc = QgsCircularString()
        arc.setPoints(points)
        line = arc.curveToLine()
        center = QgsPointXY(circle.center())
        ring = [center] + [QgsPointXY(p) for p in line.points()] + [center]
        self.mCenterPointRubberBand.setToGeometry(QgsGeometry.fromPolygonXY([ring]), None)
        self.mCenterPointRubberBand.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_R:
            self.mShowCenterPointRubberBand = True
            self.updatePreview()
            event.ignore()
        else: super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_R and not event.isAutoRepeat():
            self.mShowCenterPointRubberBand = False
            self.mCenterPointRubberBand.hide()
            event.ignore()
        else: super().keyReleaseEvent(event)

    def clean(self):
        self.mShowCenterPointRubberBand = False
        self.mCenterPointRubberBand.hide()
        super().clean()

    def dispose(self):
        super().dispose()
        self.canvas().scene().removeItem(self.mCenterPointRubberBand)
        sip.delete(self.mCenterPointRubberBand)
