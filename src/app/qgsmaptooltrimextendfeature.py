"""QGIS 3.34 trim/extend: choose a limit edge, then the edge to edit."""
from math import isfinite
from qgis.PyQt import sip
from qgis.PyQt.QtCore import Qt
from qgis.core import (Qgis, QgsPoint, QgsPointXY, QgsPointLocator, QgsGeometry,
                       QgsGeometryUtils, QgsLineString, QgsVectorLayer,
                       QgsCoordinateTransform, QgsCsException, QgsProject)
from qgis.gui import QgsMapToolEdit


class FeatureFilter(QgsPointLocator.MatchFilter):
    def __init__(self, layer=None):
        super().__init__()
        self.mLayer = layer

    def setLayer(self, layer): self.mLayer = layer

    def acceptMatch(self, match):
        return match.hasEdge() and (self.mLayer is None or match.layer() == self.mLayer)


class QgsMapToolTrimExtendFeature(QgsMapToolEdit):
    StepLimit, StepExtend = range(2)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.setToolName('修剪/延伸要素')
        self.mRubberBandLimit = self.createRubberBand(Qgis.GeometryType.Line)
        self.mRubberBandExtend = self.createRubberBand(Qgis.GeometryType.Line)
        self.mRubberBandIntersection = self.createRubberBand(Qgis.GeometryType.Point)
        self.reset()
        canvas.currentLayerChanged.connect(self.reset)

    def reset(self, *args):
        self.mStep = self.StepLimit
        self.mLimitMatch = QgsPointLocator.Match()
        self.mLimitLayer = self.mVlayer = None
        self.clearPreview()
        self.mRubberBandLimit.hide()

    def clearPreview(self):
        self.mIsModified = False
        self.mGeom = QgsGeometry()
        self.mFeatureId = None
        self.mRubberBandExtend.hide()
        self.mRubberBandIntersection.hide()

    def activate(self):
        self.reset()
        super().activate()
        self.messageEmitted.emit('先捕捉并点击限制边，再点击要修剪/延伸的边；鼠标所在一侧会被修剪。请启用线段捕捉。', Qgis.Info)

    @staticmethod
    def getPoints(match):
        layer = match.layer()
        if not match.hasEdge() or layer is None or sip.isdeleted(layer): return None
        geometry = layer.getGeometry(match.featureId())
        index = match.vertexIndex()
        if geometry.isNull() or geometry.isEmpty() or index < 0 or index + 1 >= geometry.constGet().nCoordinates(): return None
        return geometry.vertexAt(index), geometry.vertexAt(index + 1)

    def snap(self, point, relaxed=False):
        layer = self.canvas().currentLayer() if self.mStep == self.StepExtend else None
        return self.canvas().snappingUtils().snapToMap(point, FeatureFilter(layer), relaxed)

    def showLimit(self, match):
        points = self.getPoints(match)
        self.mRubberBandLimit.hide()
        if points is None: return False
        self.mRubberBandLimit.setToGeometry(QgsGeometry(QgsLineString(list(points))), match.layer())
        self.mRubberBandLimit.show()
        return True

    def setLimit(self, match):
        if not self.showLimit(match): return False
        self.mLimitMatch = match
        self.mLimitLayer = match.layer()
        self.mStep = self.StepExtend
        return True

    def preview(self, match, mapPoint):
        # Always discard the previous candidate, including invalid/parallel snaps.
        self.clearPreview()
        layer = self.canvas().currentLayer()
        if not isinstance(layer, QgsVectorLayer) or not layer.isEditable() or match.layer() != layer: return False
        limit, extended = self.getPoints(self.mLimitMatch), self.getPoints(match)
        if limit is None or extended is None: return False
        pLimit1, pLimit2 = limit
        pExtend1, pExtend2 = extended
        try:
            if self.mLimitLayer.crs() != layer.crs():
                transform = QgsCoordinateTransform(self.mLimitLayer.crs(), layer.crs(), QgsProject.instance())
                pLimit1.transform(transform)
                pLimit2.transform(transform)
            mouse = QgsPoint(self.toLayerCoordinates(layer, mapPoint))
        except QgsCsException:
            return False
        if any(QgsPointXY(a) == QgsPointXY(b) for a in (pLimit1, pLimit2) for b in extended): return False
        intersects, intersection, hasIntersection = QgsGeometryUtils.segmentIntersection(pLimit1, pLimit2, pExtend1, pExtend2, 1e-8, True)
        if not hasIntersection or not all(isfinite(value) for value in (intersection.x(), intersection.y())): return False
        index = match.vertexIndex()
        if not intersects:
            if pExtend2.distance(intersection) < pExtend1.distance(intersection): index += 1
        elif QgsGeometryUtils.leftOfLine(mouse, pLimit1, pLimit2) != QgsGeometryUtils.leftOfLine(pExtend1, pLimit1, pLimit2):
            index += 1
        geometry = layer.getGeometry(match.featureId())
        point = geometry.vertexAt(index)
        point.setX(intersection.x())
        point.setY(intersection.y())
        if pLimit1.is3D() and point.is3D():
            interpolated = QgsGeometryUtils.closestPoint(QgsLineString([pLimit1, pLimit2]), intersection)
            point.setZ(interpolated.z())
            if interpolated.isMeasure() and point.isMeasure(): point.setM(interpolated.m())
        if not geometry.moveVertex(point, index): return False
        geometry.removeDuplicateNodes()
        if geometry.isEmpty(): return False
        self.mGeom, self.mIntersection, self.mFeatureId, self.mVlayer = geometry, point, match.featureId(), layer
        self.mRubberBandExtend.setToGeometry(geometry, layer)
        self.mRubberBandIntersection.setToGeometry(QgsGeometry(point.clone()), layer)
        self.mRubberBandExtend.show()
        self.mRubberBandIntersection.show()
        self.mIsModified = True
        return True

    def apply(self):
        layer = self.mVlayer
        if not self.mIsModified or layer is None or sip.isdeleted(layer) or not layer.isEditable(): return False
        layer.beginEditCommand('修剪/延伸要素')
        try:
            if not layer.changeGeometry(self.mFeatureId, self.mGeom):
                layer.destroyEditCommand()
                return False
            if QgsProject.instance().topologicalEditing(): layer.addTopologicalPoints(self.mIntersection)
            layer.endEditCommand()
        except Exception:
            layer.destroyEditCommand()
            raise
        # The boundary may belong to a different editable layer. Its undo stack
        # is independent, as for the other native cross-layer topology edits.
        limit = self.mLimitLayer
        if (QgsProject.instance().topologicalEditing() and limit is not None and
                not sip.isdeleted(limit) and limit != layer and limit.isEditable()):
            point = self.mIntersection.clone()
            try:
                point.transform(QgsCoordinateTransform(layer.crs(), limit.crs(), QgsProject.instance()))
                limit.beginEditCommand('修剪/延伸：添加拓扑节点')
                result = limit.addTopologicalPoints(point)
                if result == 0: limit.endEditCommand()
                else: limit.destroyEditCommand()
                limit.triggerRepaint()
            except QgsCsException:
                self.messageEmitted.emit('要素已修改，但限制图层的拓扑节点坐标转换失败。', Qgis.Warning)
        layer.triggerRepaint()
        return True

    def canvasMoveEvent(self, event):
        match = self.snap(event.mapPoint(), True)
        if self.mStep == self.StepLimit: self.showLimit(match)
        else: self.preview(match, event.mapPoint())

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.reset()
            return
        if event.button() != Qt.LeftButton: return
        match = self.snap(event.mapPoint())
        if self.mStep == self.StepLimit:
            if not self.setLimit(match): self.messageEmitted.emit('未捕捉到限制边，请检查捕捉图层及线段捕捉设置。', Qgis.Warning)
            return
        success = self.preview(match, event.mapPoint()) and self.apply()
        self.messageEmitted.emit('已修剪/延伸要素。' if success else '无法修剪/延伸：请选择与限制边有交点的线段。', Qgis.Info if success else Qgis.Warning)
        self.reset()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if not event.isAutoRepeat(): self.reset()
            event.ignore()
        else: super().keyPressEvent(event)

    def deactivate(self):
        self.reset()
        super().deactivate()
