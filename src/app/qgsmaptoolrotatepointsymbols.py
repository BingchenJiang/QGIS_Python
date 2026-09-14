"""QgsMapToolRotatePointSymbols: field-based angle editing with native-symbol preview."""
import math
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProperty
from .qgsmaptoolpointsymbol import QgsMapToolPointSymbol
from .labeling.qgsmaptoollabel import isNull


class QgsMapToolRotatePointSymbols(QgsMapToolPointSymbol):
    operationName = '旋转点符号'

    def checkSymbolCompatibility(self, symbol, context):
        prop = symbol.dataDefinedAngle()
        return prop.isActive() and prop.propertyType() == QgsProperty.FieldBasedProperty and self.mActiveLayer.fields().lookupField(prop.field()) >= 0

    def calculateAzimut(self, mousePos):
        center = self.toCanvasCoordinates(self.mSnappedPoint)
        return 180-math.degrees(math.atan2(mousePos.x()-center.x(), mousePos.y()-center.y()))

    def beginOperation(self, event, context):
        self.mCurrentRotationAttributes = {self.mActiveLayer.fields().lookupField(s.dataDefinedAngle().field()) for s in self.mSymbols}
        value = self.mClickedFeature[next(iter(self.mCurrentRotationAttributes))]
        self.mStartRotation = 0 if isNull(value) else float(value)
        self.mStartMouseAzimut = self.calculateAzimut(event.pos())

    def calculateChanges(self, event):
        angle = (self.mStartRotation+self.calculateAzimut(event.pos())-self.mStartMouseAzimut) % 360
        rotation = math.floor(angle/15+.5)*15 if event.modifiers() & Qt.ControlModifier else int(angle)
        return {index: rotation for index in self.mCurrentRotationAttributes}
