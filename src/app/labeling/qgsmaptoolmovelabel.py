"""QgsMapToolMoveLabel: labels, diagrams, line anchors and callout endpoints."""
import math
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import Qgis, QgsPalLayerSettings, QgsCallout, QgsPointXY, QgsGeometry, QgsRectangle, QgsSettings
from qgis.gui import QgsRubberBand
from .qgsmaptoollabel import QgsMapToolLabel, LabelDetails


class QgsMapToolMoveLabel(QgsMapToolLabel):
    ANCHOR_PROPERTIES = [QgsPalLayerSettings.LineAnchorPercent, QgsPalLayerSettings.LineAnchorClipping,
                         QgsPalLayerSettings.LineAnchorType, QgsPalLayerSettings.LineAnchorTextPoint]

    def __init__(self, canvas, cadDock):
        super().__init__(canvas, cadDock)
        self.mCurrentCallout = None
        self.mCalloutMoveRubberBand = None
        self.mAnchorBand = None
        self.mLabelTearFromLineThreshold = canvas.fontMetrics().horizontalAdvance('X') * 5

    def calloutAtPosition(self, event):
        results = self.canvas().labelingResults(False)
        if not results: return None
        point = self.toMapCoordinates(event.pos())
        radius = self.searchRadiusMU(self.canvas())
        rect = QgsRectangle(point.x()-radius, point.y()-radius, point.x()+radius, point.y()+radius)
        hits = []
        for callout in results.calloutsWithinRectangle(rect):
            for origin, endpoint in [(True, callout.origin()), (False, callout.destination())]:
                distance = point.sqrDist(QgsPointXY(endpoint))
                if distance <= radius*radius: hits.append((distance, callout, origin))
        return min(hits, key=lambda item: item[0])[1:] if hits else None

    def calloutDetails(self, callout):
        from qgis.core import QgsProject, QgsVectorLayer
        layer = QgsProject.instance().mapLayer(callout.layerID)
        if not isinstance(layer, QgsVectorLayer) or not layer.labeling(): return None
        return LabelDetails(callout, layer, QgsPalLayerSettings(layer.labeling().settings(callout.providerID)))

    def calloutProperties(self):
        return [QgsCallout.OriginX, QgsCallout.OriginY] if self.mCurrentCalloutMoveOrigin else [QgsCallout.DestinationX, QgsCallout.DestinationY]

    def cadCanvasPressEvent(self, event):
        if self.mCurrentLabel or self.mCurrentCallout:
            if event.button() == Qt.RightButton: self.cancel(); return
            if event.button() == Qt.LeftButton:
                if self.mCurrentCallout: self.moveCallout(event.mapPoint(), event.modifiers())
                else: self.moveLabel(event.mapPoint())
                self.cancel()
            return
        if event.button() != Qt.LeftButton: return
        self.clearHoveredLabel()
        hit = self.calloutAtPosition(event)
        if hit:
            self.mCurrentCallout, self.mCurrentCalloutMoveOrigin = hit
            details = self.calloutDetails(self.mCurrentCallout)
            if not details or not self.createAuxiliaryFields(details, self.calloutProperties(), 'callout'):
                self.cancel(); return
            self.mCalloutMoveRubberBand = QgsRubberBand(self.canvas(), Qgis.GeometryType.Line)
            self.mCalloutMoveRubberBand.setColor(QColor(0, 120, 255))
            self.mCalloutMoveRubberBand.addPoint(QgsPointXY(self.mCurrentCallout.origin()))
            self.mCalloutMoveRubberBand.addPoint(QgsPointXY(self.mCurrentCallout.destination()))
            return
        pos = self.labelAtPosition(event)
        if not pos: return
        self.mCurrentLabel = self.details(pos)
        self.mStartPointMapCoords = event.mapPoint()
        self.mRotationPoint = self.currentLabelRotationPoint()
        props = self.positionProperties(self.mCurrentLabel)
        if self.isLineLabel(): props += self.ANCHOR_PROPERTIES
        if not self.createAuxiliaryFields(self.mCurrentLabel, props): self.cancel(); return
        self.createRubberBands()

    def isLineLabel(self):
        return bool(self.mCurrentLabel and not self.mCurrentLabel.pos.isDiagram and self.mCurrentLabel.settings.placement in (
            Qgis.LabelPlacement.Line, Qgis.LabelPlacement.Curved, Qgis.LabelPlacement.PerimeterCurved))

    def lineGeometry(self):
        details = self.mCurrentLabel
        geometry = details.layer.getFeature(details.pos.featureId).geometry()
        if geometry.type() == Qgis.GeometryType.Polygon: geometry = QgsGeometry(geometry.constGet().boundary())
        return geometry

    def lineAnchor(self, point):
        if not self.isLineLabel(): return None
        geometry = self.lineGeometry()
        mapGeometry = QgsGeometry(geometry)
        mapGeometry.transform(self.canvas().mapSettings().layerTransform(self.mCurrentLabel.layer))
        pointGeometry = QgsGeometry.fromPointXY(point)
        if mapGeometry.distance(pointGeometry) / self.canvas().mapUnitsPerPixel() > self.mLabelTearFromLineThreshold: return None
        layerPoint = self.canvas().mapSettings().mapToLayerCoordinates(self.mCurrentLabel.layer, point)
        if geometry.isMultipart():
            parts = geometry.asGeometryCollection()
            geometry = min(parts, key=lambda g: g.distance(QgsGeometry.fromPointXY(layerPoint)))
        length = geometry.length()
        fraction = geometry.lineLocatePoint(QgsGeometry.fromPointXY(layerPoint))/length if length > 0 else -1
        return max(0, min(1, fraction)) if fraction >= 0 else None

    def moveLabel(self, point):
        details = self.mCurrentLabel
        if not details: return False
        anchor = self.lineAnchor(point)
        if anchor is not None:
            indexes = self.createAuxiliaryFields(details, self.ANCHOR_PROPERTIES)
            if not indexes: return False
            changes = dict(zip([indexes[p] for p in self.ANCHOR_PROPERTIES], [anchor, 'entire', 'strict', 'start']))
            changes.update(self.positionChanges(details, None, False) or {})
        else:
            point = QgsPointXY(self.mRotationPoint.x()+point.x()-self.mStartPointMapCoords.x(), self.mRotationPoint.y()+point.y()-self.mStartPointMapCoords.y())
            changes = self.positionChanges(details, point)
            if changes is None: return False
            if self.isLineLabel():
                for prop in self.ANCHOR_PROPERTIES:
                    index = self.dataDefinedColumnIndex(prop, details)
                    if index >= 0: changes[index] = None
        return self.writeChanges(details, changes, '移动标注')

    def snapCalloutPointToCommonAngle(self, point):
        other = self.mCurrentCallout.destination() if self.mCurrentCalloutMoveOrigin else self.mCurrentCallout.origin()
        dx, dy = point.x()-other.x(), point.y()-other.y()
        angle = round(math.atan2(dy, dx)/(math.pi/12))*(math.pi/12)
        distance = math.hypot(dx, dy)
        return QgsPointXY(other.x()+distance*math.cos(angle), other.y()+distance*math.sin(angle))

    def moveCallout(self, point, modifiers=Qt.NoModifier):
        details = self.calloutDetails(self.mCurrentCallout)
        if not details: return False
        indexes = self.createAuxiliaryFields(details, self.calloutProperties(), 'callout')
        if not indexes: return False
        if modifiers & Qt.ShiftModifier: point = self.snapCalloutPointToCommonAngle(point)
        point = self.canvas().mapSettings().mapToLayerCoordinates(details.layer, point)
        return self.writeChanges(details, dict(zip(indexes.values(), [point.x(), point.y()])), '移动引线端点')

    def cadCanvasMoveEvent(self, event):
        if self.mCurrentLabel:
            point = event.mapPoint()
            anchor = self.lineAnchor(point)
            self.clearBand('mAnchorBand')
            if anchor is not None:
                geometry = self.lineGeometry()
                geometry.transform(self.canvas().mapSettings().layerTransform(self.mCurrentLabel.layer))
                nearest = geometry.nearestPoint(QgsGeometry.fromPointXY(point))
                self.mAnchorBand = QgsRubberBand(self.canvas(), Qgis.GeometryType.Point)
                self.mAnchorBand.setToGeometry(nearest, None)
                self.mLabelRubberBand.hide()
            else:
                self.mLabelRubberBand.setTranslationOffset(point.x()-self.mStartPointMapCoords.x(), point.y()-self.mStartPointMapCoords.y())
                self.mLabelRubberBand.show()
        elif self.mCurrentCallout:
            point = self.snapCalloutPointToCommonAngle(event.mapPoint()) if event.modifiers() & Qt.ShiftModifier else event.mapPoint()
            self.mCalloutMoveRubberBand.movePoint(0 if self.mCurrentCalloutMoveOrigin else 1, point)
        else: self.updateHoveredLabel(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Delete:
            if self.mCurrentLabel:
                details = self.mCurrentLabel
                changes = self.positionChanges(details, None, False) or {}
                if self.isLineLabel():
                    changes.update({self.dataDefinedColumnIndex(p, details): None for p in self.ANCHOR_PROPERTIES if self.dataDefinedColumnIndex(p, details) >= 0})
                self.writeChanges(details, changes, '删除标注位置覆盖')
            elif self.mCurrentCallout:
                details = self.calloutDetails(self.mCurrentCallout)
                changes = {self.dataDefinedColumnIndex(p, details, 'callout'): None for p in self.calloutProperties()}
                self.writeChanges(details, changes, '删除引线位置覆盖')
            self.cancel()
        else: super().keyReleaseEvent(event)

    def cancel(self):
        super().cancel()
        self.mCurrentCallout = None
        self.clearBand('mCalloutMoveRubberBand')
        self.clearBand('mAnchorBand')
