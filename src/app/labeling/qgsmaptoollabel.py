"""Shared label editing, corresponding to QGIS 3.34 QgsMapToolLabel."""
import math
from dataclasses import dataclass
from qgis.PyQt import sip
from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtGui import QColor, QFontMetricsF
from qgis.PyQt.QtWidgets import QUndoCommand
from qgis.core import (
    Qgis, QgsProject, QgsVectorLayer, QgsPalLayerSettings, QgsDiagramLayerSettings,
    QgsCallout, QgsProperty, QgsExpression, QgsExpressionNodeColumnRef,
    QgsExpressionNodeFunction, QgsAuxiliaryLayer, QgsFields, QgsPointXY,
    QgsGeometry, QgsRectangle, QgsVariantUtils, QgsReferencedGeometry,
)
from qgis.gui import QgsMapToolAdvancedDigitizing, QgsRubberBand, QgsNewAuxiliaryLayerDialog


def isNull(value):
    return value is None or QgsVariantUtils.isNull(value)


@dataclass
class LabelDetails:
    pos: object
    layer: object
    settings: object


class _QgsLabelAuxiliaryUndoCommand(QUndoCommand):
    """Join the native auxiliary undo macro to its owning layer's command."""
    def __init__(self, layer, auxiliary, before, after):
        super().__init__('标注辅助字段')
        self.layer, self.auxiliary = layer, auxiliary
        self.before, self.after = before, after
        self.firstRedo = True

    def restore(self, index):
        if sip.isdeleted(self.auxiliary) or sip.isdeleted(self.layer): return
        stack = self.auxiliary.undoStack()
        if stack.count() >= self.after:
            stack.setIndex(index)
            self.layer.triggerRepaint()

    def undo(self): self.restore(self.before)
    def redo(self):
        if self.firstRedo: self.firstRedo = False
        else: self.restore(self.after)


class QgsMapToolLabel(QgsMapToolAdvancedDigitizing):
    def __init__(self, canvas, cadDock):
        super().__init__(canvas, cadDock)
        self.mCurrentLabel = None
        self.mLabelRubberBand = None
        self.mHoverRubberBand = None
        self.mSelectStart = None
        self.mSelectBand = None
        self.setCursor(Qt.CrossCursor)

    def details(self, pos):
        layer = QgsProject.instance().mapLayer(pos.layerID)
        if not isinstance(layer, QgsVectorLayer) or layer not in self.canvas().layers(): return None
        if pos.isDiagram:
            if not layer.diagramsEnabled(): return None
            settings = QgsDiagramLayerSettings(layer.diagramLayerSettings())
        else:
            if not layer.labelsEnabled() or not layer.labeling(): return None
            settings = QgsPalLayerSettings(layer.labeling().settings(pos.providerID))
        return LabelDetails(pos, layer, settings)

    def labelAtPosition(self, event):
        results = self.canvas().labelingResults(False)
        if not results: return None
        candidates = [p for p in results.labelsAtPosition(self.toMapCoordinates(event.pos())) if self.details(p)]
        current = self.canvas().currentLayer()
        active = [p for p in candidates if current and p.layerID == current.id()]
        candidates = active or candidates
        unplaced = [p for p in candidates if p.isUnplaced]
        return min(unplaced or candidates, key=lambda p: p.width * p.height) if candidates else None

    def properties(self, details, kind='label'):
        if kind == 'callout': return details.settings.callout().dataDefinedProperties()
        return details.settings.dataDefinedProperties()

    def dataDefinedColumnName(self, prop, details, kind='label'):
        property = self.properties(details, kind).property(prop)
        if not property.isActive(): return ''
        if property.propertyType() == QgsProperty.FieldBasedProperty: return property.field()
        if property.propertyType() != QgsProperty.ExpressionBasedProperty: return ''
        context = self.canvas().createExpressionContext()
        context.appendScope(details.layer.createExpressionContextScope())
        expression = QgsExpression(property.expressionString())
        if not expression.prepare(context): raise ValueError('数据定义表达式无效：' + property.expressionString())
        node = expression.rootNode().effectiveNode()
        if isinstance(node, QgsExpressionNodeColumnRef): return node.name()
        if isinstance(node, QgsExpressionNodeFunction) and QgsExpression.Functions()[node.fnIndex()].name() == 'coalesce':
            args = node.args().list()
            first = args[0].effectiveNode() if args else None
            if isinstance(first, QgsExpressionNodeColumnRef): return first.name()
        return ''

    def dataDefinedColumnIndex(self, prop, details, kind='label'):
        return details.layer.fields().lookupField(self.dataDefinedColumnName(prop, details, kind))

    def createAuxiliaryFields(self, details, properties, kind='label'):
        """Keep native field/expression mappings; add missing storage using QGIS."""
        layer = details.layer
        try: indexes = {p: self.dataDefinedColumnIndex(p, details, kind) for p in properties}
        except ValueError as error:
            self.messageEmitted.emit(str(error), Qgis.Warning)
            return None
        if all(i >= 0 for i in indexes.values()): return indexes
        if not layer.auxiliaryLayer():
            dialog = QgsNewAuxiliaryLayerDialog(layer, self.canvas())
            dialog.exec_()
            if not layer.auxiliaryLayer(): return None
        for p, index in indexes.items():
            if index < 0:
                indexes[p] = QgsAuxiliaryLayer.createProperty(p, layer, False)
                if indexes[p] < 0: raise ValueError('不能创建标注辅助字段')
        if kind == 'callout': details.settings = QgsPalLayerSettings(layer.labeling().settings(details.pos.providerID))
        else:
            refreshed = self.details(details.pos)
            if refreshed: details.settings = refreshed.settings
        layer.styleChanged.emit()
        QgsProject.instance().setDirty(True)
        return indexes

    def writeChanges(self, details, changes, title):
        """One undo command; native auxiliary joins can be edited without editing the source."""
        if not changes: return False
        layer = details.layer
        if sip.isdeleted(layer) or not layer.getFeature(details.pos.featureId).isValid(): return False
        if any(i < 0 or i >= layer.fields().count() for i in changes): return False
        physical = any(layer.fields().fieldOrigin(i) != QgsFields.OriginJoin for i in changes)
        if physical and not layer.isEditable() and not layer.startEditing():
            self.messageEmitted.emit('无法编辑图层“' + layer.name() + '”的标注字段', Qgis.Warning)
            return False
        layer.beginEditCommand(title)
        auxiliary = layer.auxiliaryLayer()
        usesAuxiliary = bool(auxiliary and any(layer.fields()[i].name().startswith('auxiliary_storage_') for i in changes))
        if usesAuxiliary:
            auxiliaryIndex = auxiliary.undoStack().index()
            auxiliary.beginEditCommand(title)
        try:
            for index, value in changes.items():
                if not layer.changeAttributeValue(details.pos.featureId, index, QVariant() if value is None else value):
                    raise ValueError('无法写入字段：' + layer.fields()[index].name())
        except Exception as error:
            if usesAuxiliary: auxiliary.destroyEditCommand()
            layer.destroyEditCommand()
            self.messageEmitted.emit(str(error), Qgis.Warning)
            return False
        if usesAuxiliary:
            auxiliary.endEditCommand()
            layer.undoStack().push(_QgsLabelAuxiliaryUndoCommand(layer, auxiliary, auxiliaryIndex, auxiliary.undoStack().index()))
        layer.endEditCommand()
        QgsProject.instance().setDirty(True)
        layer.triggerRepaint()
        return True

    def value(self, details, prop, default=None, kind='label'):
        context = self.canvas().createExpressionContext()
        context.appendScope(details.layer.createExpressionContextScope())
        context.setFeature(details.layer.getFeature(details.pos.featureId))
        value, ok = self.properties(details, kind).property(prop).value(context, default)
        return value if ok and not isNull(value) else default

    def positionProperties(self, details):
        cls = QgsDiagramLayerSettings if details.pos.isDiagram else QgsPalLayerSettings
        if not details.pos.isDiagram and self.dataDefinedColumnIndex(cls.PositionPoint, details) >= 0:
            return [cls.PositionPoint]
        return [cls.PositionX, cls.PositionY]

    def positionChanges(self, details, point, create=True):
        props = self.positionProperties(details)
        indexes = self.createAuxiliaryFields(details, props) if create else {p: self.dataDefinedColumnIndex(p, details) for p in props}
        if not indexes or any(i < 0 for i in indexes.values()): return None
        if point is None: return {i: None for i in indexes.values()}
        point = self.canvas().mapSettings().mapToLayerCoordinates(details.layer, point)
        if len(props) == 1: return {indexes[props[0]]: QgsReferencedGeometry(QgsGeometry.fromPointXY(point), details.layer.crs())}
        return {indexes[props[0]]: point.x(), indexes[props[1]]: point.y()}

    def isPinned(self, details=None):
        details = details or self.mCurrentLabel
        if not details: return False
        props = self.positionProperties(details)
        if all(self.value(details, p) is not None for p in props): return True
        return not details.pos.isDiagram and self.value(details, QgsPalLayerSettings.LineAnchorPercent) is not None

    def currentLabelRotationPoint(self, details=None, ignoreUpsideDown=False):
        details = details or self.mCurrentLabel
        pos = details.pos
        if pos.isDiagram: return pos.labelRect.center()
        corners = pos.cornerPoints
        if len(corners) < 4: return pos.labelRect.center()
        upside = pos.upsideDown and not ignoreUpsideDown
        point = QgsPointXY(corners[2] if upside else corners[0])
        hali = str(self.value(details, QgsPalLayerSettings.Hali, 'Left')).lower()
        vali = str(self.value(details, QgsPalLayerSettings.Vali, 'Bottom')).lower()
        width = math.sqrt(corners[0].sqrDist(corners[1]))
        height = math.sqrt(corners[0].sqrDist(corners[3]))
        metrics = QFontMetricsF(pos.labelFont)
        descent = 1 / max(metrics.ascent() * metrics.height(), 1)
        cap = (metrics.boundingRect('H').height()+1+metrics.descent()) / max(metrics.height(), 1)
        dx = width * {'center': .5, 'right': 1}.get(hali, 0)
        dy = height * {'half': .5*(cap-descent), 'top': 1, 'base': descent, 'cap': cap}.get(vali, 0)
        angle = math.radians(pos.rotation)
        sign = -1 if upside else 1
        return QgsPointXY(point.x()+sign*(dx*math.cos(angle)-dy*math.sin(angle)), point.y()+sign*(dx*math.sin(angle)+dy*math.cos(angle)))

    def createRubberBands(self):
        self.deleteRubberBands()
        if self.mCurrentLabel:
            self.mLabelRubberBand = self.labelBand(self.mCurrentLabel.pos, QColor(0, 120, 255, 90))

    def labelBand(self, pos, color):
        band = QgsRubberBand(self.canvas(), Qgis.GeometryType.Polygon)
        points = list(pos.cornerPoints)
        if points:
            band.setToGeometry(QgsGeometry.fromPolygonXY([points + [points[0]]]), None)
        else: band.setToGeometry(QgsGeometry.fromRect(pos.labelRect), None)
        band.setColor(color)
        band.setWidth(1)
        return band

    def clearBand(self, name):
        band = getattr(self, name, None)
        if band and not sip.isdeleted(band): sip.delete(band)
        setattr(self, name, None)

    def deleteRubberBands(self): self.clearBand('mLabelRubberBand')
    def clearHoveredLabel(self): self.clearBand('mHoverRubberBand')

    def updateHoveredLabel(self, event):
        self.clearHoveredLabel()
        pos = self.labelAtPosition(event)
        if pos: self.mHoverRubberBand = self.labelBand(pos, QColor(255, 200, 0, 70))

    def cadCanvasMoveEvent(self, event): self.updateHoveredLabel(event)

    def beginSelect(self, event):
        if event.button() != Qt.LeftButton: return
        self.cancel()
        self.mSelectStart = event.pos()
        self.mSelectBand = QgsRubberBand(self.canvas(), Qgis.GeometryType.Polygon)
        self.mSelectBand.setColor(QColor(0, 120, 255, 60))

    def updateSelect(self, event):
        if self.mSelectStart is None: return
        rect = QgsRectangle(self.toMapCoordinates(self.mSelectStart), self.toMapCoordinates(event.pos()))
        self.mSelectBand.setToGeometry(QgsGeometry.fromRect(rect), None)

    def endSelect(self, event):
        if self.mSelectStart is None: return None
        drag = (event.pos()-self.mSelectStart).manhattanLength() > 3
        a, b = self.toMapCoordinates(self.mSelectStart), self.toMapCoordinates(event.pos())
        rect = QgsRectangle(a, b)
        if not drag: rect.grow(self.canvas().mapUnitsPerPixel()*2)
        self.mSelectStart = None
        self.clearBand('mSelectBand')
        return rect, drag

    def cancel(self):
        self.deleteRubberBands()
        self.clearHoveredLabel()
        self.clearBand('mSelectBand')
        self.mSelectStart = None
        self.mCurrentLabel = None

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Escape): event.ignore()
        else: super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Escape: self.cancel()
        else: super().keyReleaseEvent(event)

    def deactivate(self):
        self.cancel()
        super().deactivate()
