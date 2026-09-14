"""QgsMapToolOffsetPointSymbol: offsets in the symbol layer's original render unit."""
import math
from qgis.PyQt.QtCore import QPointF
from qgis.core import Qgis, QgsProperty, QgsSymbolLayer, QgsMarkerSymbolLayer, QgsSymbolLayerUtils, QgsDistanceArea, QgsProject
from .qgsmaptoolpointsymbol import QgsMapToolPointSymbol


class QgsMapToolOffsetPointSymbol(QgsMapToolPointSymbol):
    operationName = '偏移点符号'

    def checkSymbolCompatibility(self, symbol, context):
        return any(isinstance(layer, QgsMarkerSymbolLayer) and layer.dataDefinedProperties().property(QgsSymbolLayer.PropertyOffset).isActive()
                   and layer.dataDefinedProperties().property(QgsSymbolLayer.PropertyOffset).propertyType() == QgsProperty.FieldBasedProperty
                   and self.mActiveLayer.fields().lookupField(layer.dataDefinedProperties().property(QgsSymbolLayer.PropertyOffset).field()) >= 0
                   for layer in symbol.symbolLayers())

    def beginOperation(self, event, context):
        self.mSymbolRotation = self.mSymbols[0].angle()
        for layer in self.mSymbols[0].symbolLayers():
            prop = layer.dataDefinedProperties().property(QgsSymbolLayer.PropertyAngle)
            if prop.isActive():
                self.mSymbolRotation = prop.valueAsDouble(context.expressionContext(), self.mSymbolRotation)[0]
                break

    def calculateChanges(self, event): return self.calculateNewOffsetAttributes(self.mClickedPoint, event.mapPoint())

    def calculateNewOffsetAttributes(self, startPoint, endPoint):
        changes = {}
        for symbol in self.mSymbols:
            for layer in symbol.symbolLayers():
                if not isinstance(layer, QgsMarkerSymbolLayer): continue
                prop = layer.dataDefinedProperties().property(QgsSymbolLayer.PropertyOffset)
                if not prop.isActive() or prop.propertyType() != QgsProperty.FieldBasedProperty: continue
                index = self.mActiveLayer.fields().lookupField(prop.field())
                if index >= 0: changes[index] = QgsSymbolLayerUtils.encodePoint(self.calculateOffset(startPoint, endPoint, layer.offsetUnit()))
        return changes

    def calculateOffset(self, startPoint, endPoint, unit):
        settings = self.canvas().mapSettings()
        pixel = settings.mapUnitsPerPixel()
        dpi = settings.outputDpi()
        factor = {
            Qgis.RenderUnit.Millimeters: 25.4/dpi/pixel,
            Qgis.RenderUnit.Points: 72/dpi/pixel,
            Qgis.RenderUnit.Inches: 1/dpi/pixel,
            Qgis.RenderUnit.Pixels: 1/pixel,
        }.get(unit, 1)
        if unit == Qgis.RenderUnit.MetersInMapUnits:
            distance = QgsDistanceArea()
            distance.setSourceCrs(settings.destinationCrs(), QgsProject.instance().transformContext())
            distance.setEllipsoid(settings.ellipsoid())
            length = distance.measureLineProjected(startPoint)[0]
            factor = 1/length if length else 1
        offset = QPointF((endPoint.x()-startPoint.x())*factor, -(endPoint.y()-startPoint.y())*factor)
        return self.rotatedOffset(offset, self.mSymbolRotation)

    @staticmethod
    def rotatedOffset(offset, angle):
        angle = math.radians(360-angle)
        return QPointF(offset.x()*math.cos(angle)-offset.y()*math.sin(angle), offset.x()*math.sin(angle)+offset.y()*math.cos(angle))
