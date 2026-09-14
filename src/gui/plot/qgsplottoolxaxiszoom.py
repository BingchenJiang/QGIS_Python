"""QgsPlotToolXAxisZoom -- the protected 3.34 zoom hooks are not in SIP."""
from qgis.PyQt.QtCore import Qt, QPointF, QRectF
from qgis.PyQt.QtWidgets import QRubberBand
from qgis.gui import QgsPlotTool


class QgsPlotToolXAxisZoom(QgsPlotTool):
    def __init__(self, canvas):
        super().__init__(canvas, '缩放 X 轴')
        self.mMarqueeZoom = False
        self.mRubberBandStartPos = QPointF()
        self.mRubberBand = QRubberBand(QRubberBand.Rectangle, canvas.viewport())
        self.setCursor(Qt.CrossCursor)

    def constrainStartPoint(self, point):
        return point if self.canvas().lockAxisScales() else QPointF(point.x(), self.canvas().plotArea().top())

    def constrainMovePoint(self, point):
        area = self.canvas().plotArea()
        if self.canvas().lockAxisScales():
            height = area.height() / max(area.width(), 1.) * abs(point.x() - self.mRubberBandStartPos.x())
            return QPointF(point.x(), self.mRubberBandStartPos.y() + height)
        return QPointF(point.x(), area.bottom())

    def constrainBounds(self, bounds):
        if self.canvas().lockAxisScales(): return bounds
        area = self.canvas().plotArea()
        return QRectF(bounds.left(), area.top(), bounds.width(), area.height())

    def zoomOutClickOn(self, point): self.zoomClickOn(point, .5)
    def zoomInClickOn(self, point): self.zoomClickOn(point, 2.)

    def zoomClickOn(self, point, factor):
        self.canvas().centerPlotOn(point.x(), self.canvas().plotArea().center().y())
        self.canvas().scalePlot(factor, 1.)

    def plotPressEvent(self, event):
        self.mRubberBand.hide()
        self.mMarqueeZoom = False
        if event.button() != Qt.LeftButton: event.ignore(); return
        self.mRubberBandStartPos = QPointF(event.pos())
        if event.modifiers() & Qt.AltModifier: self.zoomOutClickOn(self.mRubberBandStartPos)
        else: self.mMarqueeZoom = True

    def plotMoveEvent(self, event):
        if not self.mMarqueeZoom: event.ignore(); return
        bounds = QRectF(self.constrainStartPoint(self.mRubberBandStartPos), self.constrainMovePoint(QPointF(event.pos()))).normalized()
        self.mRubberBand.setGeometry(bounds.toRect())
        self.mRubberBand.show()

    def plotReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self.mMarqueeZoom: event.ignore(); return
        self.mMarqueeZoom = False
        self.mRubberBand.hide()
        if not self.isClickAndDrag(self.mRubberBandStartPos.toPoint(), event.pos()):
            self.zoomInClickOn(QPointF(event.pos()))
        else:
            bounds = QRectF(self.constrainStartPoint(self.mRubberBandStartPos), self.constrainMovePoint(QPointF(event.pos()))).normalized()
            if bounds.width() > 0: self.canvas().zoomToRect(self.constrainBounds(bounds))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.mMarqueeZoom = False
            self.mRubberBand.hide()
        else: super().keyPressEvent(event)

    def deactivate(self):
        self.mMarqueeZoom = False
        self.mRubberBand.hide()
        super().deactivate()
