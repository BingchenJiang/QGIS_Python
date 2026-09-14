"""QgsMapToolPointSymbol: snap and resolve symbols from the native renderer."""
from qgis.PyQt import sip
from qgis.PyQt.QtCore import Qt
from qgis.core import Qgis, QgsVectorLayer, QgsPointLocator, QgsRenderContext, QgsExpressionContextUtils, QgsMarkerSymbol, QgsFeature
from qgis.gui import QgsMapToolEdit
from .qgspointmarkeritem import QgsMapCanvasMarkerSymbolItem


class QgsMapToolPointSymbol(QgsMapToolEdit):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.mActiveLayer = None
        self.mPreviewItem = None
        self.mSymbols = []
        self.setCursor(Qt.CrossCursor)

    def canvasPressEvent(self, event):
        if self.mPreviewItem:
            if event.button() == Qt.LeftButton:
                changes = self.calculateChanges(event)
                self.applyChanges(changes)
            self.cancel()
            return
        if event.button() != Qt.LeftButton: return
        layer = self.canvas().currentLayer()
        if not isinstance(layer, QgsVectorLayer) or not layer.isEditable() or layer.geometryType() != Qgis.GeometryType.Point: return
        match = self.canvas().snappingUtils().snapToCurrentLayer(event.pos(), QgsPointLocator.Vertex)
        if not match.isValid():
            self.messageEmitted.emit('没有拾取到点要素，请靠近要素位置点击', Qgis.Warning)
            return
        self.mActiveLayer = layer
        self.mFeatureNumber = match.featureId()
        self.mClickedFeature = layer.getFeature(self.mFeatureNumber)
        self.mClickedPoint, self.mSnappedPoint = event.mapPoint(), match.point()
        context = QgsRenderContext.fromMapSettings(self.canvas().mapSettings())
        context.expressionContext().appendScope(QgsExpressionContextUtils.layerScope(layer))
        context.expressionContext().setFeature(self.mClickedFeature)
        self.mSymbols = []
        renderer = layer.renderer().clone()
        renderer.startRender(context, layer.fields())
        try:
            for symbol in renderer.originalSymbolsForFeature(self.mClickedFeature, context):
                if isinstance(symbol, QgsMarkerSymbol) and self.checkSymbolCompatibility(symbol, context):
                    self.mSymbols.append(symbol.clone())
        finally: renderer.stopRender(context)
        if not self.mSymbols:
            self.messageEmitted.emit('此点符号未将所需的数据定义属性绑定到字段，请先在图层符号设置中指定字段', Qgis.Warning)
            self.cancel()
            return
        self.beginOperation(event, context)
        self.mPreviewItem = QgsMapCanvasMarkerSymbolItem(self.canvas(), layer)
        self.mPreviewItem.setFeature(self.mClickedFeature)
        self.mPreviewItem.setSymbol(self.mSymbols[0].clone())
        self.mPreviewItem.setPointLocation(match.point())

    def canvasMoveEvent(self, event):
        if not self.mPreviewItem: return
        feature = QgsFeature(self.mClickedFeature)
        for index, value in self.calculateChanges(event).items(): feature.setAttribute(index, value)
        self.mPreviewItem.setFeature(feature)

    def applyChanges(self, changes):
        if not changes or not self.mActiveLayer or not self.mActiveLayer.isEditable(): return False
        layer = self.mActiveLayer
        layer.beginEditCommand(self.operationName)
        for index, value in changes.items():
            if index < 0 or not layer.changeAttributeValue(self.mFeatureNumber, index, value):
                layer.destroyEditCommand()
                self.messageEmitted.emit('无法写入点符号数据定义字段', Qgis.Warning)
                return False
        layer.endEditCommand()
        layer.triggerRepaint()
        return True

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: self.cancel()
        else: super().keyPressEvent(event)

    def cancel(self):
        if self.mPreviewItem and not sip.isdeleted(self.mPreviewItem): sip.delete(self.mPreviewItem)
        self.mPreviewItem = None
        self.mActiveLayer = None
        self.mSymbols = []

    def deactivate(self): self.cancel(); super().deactivate()
