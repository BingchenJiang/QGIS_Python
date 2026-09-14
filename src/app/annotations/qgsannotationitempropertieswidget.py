"""QGIS 3.34 annotation item properties: original container and native editors."""
from pathlib import Path
from qgis.PyQt import uic, sip
from qgis.PyQt.QtWidgets import QLabel
from qgis.core import QgsProject
from qgis.gui import QgsGui, QgsMapLayerConfigWidget, QgsSymbolWidgetContext


class QgsAnnotationItemPropertiesWidget(QgsMapLayerConfigWidget):
    def __init__(self, layer, canvas, parent=None):
        super().__init__(layer, canvas, parent)
        self.mLayer, self.mCanvas = layer, canvas
        self.mItemId, self.mItemWidget = '', None
        uic.loadUi(str(Path(__file__).resolve().parents[2] / 'ui/annotations/qgsannotationitempropertieswidgetbase.ui'), self)
        self.mPageNoItem = QLabel('未选中注记项')
        self.mStack.addWidget(self.mPageNoItem)
        self.mStack.setCurrentWidget(self.mPageNoItem)
        self.mBlendModeComboBox.setBlendMode(layer.blendMode())
        self.mOpacityWidget.setOpacity(layer.opacity())
        self.mPaintEffect = layer.paintEffect().clone() if layer.paintEffect() else None
        self.mEffectWidget.setPaintEffect(self.mPaintEffect)
        self.mOpacityWidget.opacityChanged.connect(self.widgetChanged)
        self.mBlendModeComboBox.currentIndexChanged.connect(lambda *_: self.widgetChanged.emit())
        self.mEffectWidget.changed.connect(self.widgetChanged)

    def setItemId(self, itemId):
        self.mItemId = itemId
        item = self.mLayer.item(itemId) if not sip.isdeleted(self.mLayer) and itemId else None
        previous, self.mItemWidget = self.mItemWidget, None
        if previous:
            self.mStack.removeWidget(previous)
            previous.deleteLater()
        if item:
            self.mItemWidget = QgsGui.annotationItemGuiRegistry().createItemWidget(item)
        if not self.mItemWidget:
            self.mStack.setCurrentWidget(self.mPageNoItem)
            return
        context = QgsSymbolWidgetContext()
        context.setMapCanvas(self.mCanvas)
        self.mItemWidget.setContext(context)
        # The host does not yet provide the original nested QgsPanelWidgetStack.
        # Native symbol/font sub-editors therefore use their supported dialogs.
        self.mItemWidget.setDockMode(False)
        self.mStack.addWidget(self.mItemWidget)
        self.mStack.setCurrentWidget(self.mItemWidget)
        self.mItemWidget.itemChanged.connect(self.widgetChanged)

    def apply(self):
        if sip.isdeleted(self.mLayer): return
        current = self.mLayer.item(self.mItemId) if self.mItemId else None
        if current and self.mItemWidget:
            replacement = current.clone()
            self.mItemWidget.updateItem(replacement)
            self.mLayer.replaceItem(self.mItemId, replacement)
        self.mLayer.setOpacity(self.mOpacityWidget.opacity())
        self.mLayer.setBlendMode(self.mBlendModeComboBox.blendMode())
        if self.mPaintEffect: self.mLayer.setPaintEffect(self.mPaintEffect.clone())
        self.mLayer.triggerRepaint()
        QgsProject.instance().setDirty(True)

    def focusDefaultWidget(self):
        if self.mItemWidget: self.mItemWidget.focusDefaultWidget()
