"""QgsMapCanvasMarkerSymbolItem: render the original symbol with preview attributes."""
from qgis.PyQt.QtCore import QPointF, QRectF
from qgis.core import QgsRenderContext, QgsFeature, QgsExpressionContextUtils, QgsPointXY
from qgis.gui import QgsMapCanvasItem


class QgsMapCanvasMarkerSymbolItem(QgsMapCanvasItem):
    def __init__(self, canvas, layer):
        super().__init__(canvas)
        self.mCanvas, self.mLayer = canvas, layer
        self.mSymbol = None
        self.mFeature = QgsFeature()
        self.mPoint = QgsPointXY()
        self.mBounds = QRectF(-10, -10, 20, 20)
        self.setZValue(200)
        self.setOpacity(.7)

    def setSymbol(self, symbol): self.mSymbol = symbol; self.updateSize()
    def setFeature(self, feature): self.mFeature = QgsFeature(feature); self.updateSize()
    def setPointLocation(self, point): self.mPoint = QgsPointXY(point); self.updatePosition()
    def boundingRect(self): return self.mBounds

    def renderContext(self):
        context = QgsRenderContext.fromMapSettings(self.mCanvas.mapSettings())
        context.expressionContext().appendScope(QgsExpressionContextUtils.layerScope(self.mLayer))
        context.expressionContext().setFeature(self.mFeature)
        return context

    def updateSize(self):
        if not self.mSymbol: return
        context = self.renderContext()
        self.mSymbol.startRender(context, self.mLayer.fields())
        try:
            bounds = self.mSymbol.bounds(QPointF(0, 0), context, self.mFeature).adjusted(-3, -3, 3, 3)
        finally: self.mSymbol.stopRender(context)
        self.prepareGeometryChange()
        self.mBounds = bounds
        self.update()

    def updatePosition(self):
        self.setPos(self.toCanvasCoordinates(self.mPoint))
        self.updateSize()

    def paint(self, painter, *args):
        if not self.mSymbol: return
        context = self.renderContext()
        context.setPainter(painter)
        self.mSymbol.startRender(context, self.mLayer.fields())
        try: self.mSymbol.renderPoint(QPointF(0, 0), self.mFeature, context)
        finally: self.mSymbol.stopRender(context)
