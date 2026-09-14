"""Basic vertex editing counterpart of vertextool/qgsvertextool.cpp.

Drag a vertex to move, double-click a segment to insert; Delete removes the
last picked vertex. The coordinate editor follows the picked feature.
"""
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor
from qgis.core import Qgis, QgsFeatureRequest, QgsPointLocator, QgsPointXY, QgsRectangle, QgsVectorLayer, QgsVectorDataProvider
from qgis.gui import QgsMapToolAdvancedDigitizing, QgsSnapIndicator, QgsVertexMarker


class QgsVertexTool(QgsMapToolAdvancedDigitizing):
    vertexSelected = pyqtSignal(object, object, int)
    ActiveLayer, AllLayers = range(2)

    def __init__(self, canvas, cadDock, mode=AllLayers):
        super().__init__(canvas, cadDock)
        self.mMode = mode
        self.mVertex = None
        self.mDragging = False
        self.mMarker = QgsVertexMarker(canvas)
        self.mMarker.setColor(QColor('red'))
        self.mMarker.setIconType(QgsVertexMarker.ICON_BOX)
        self.mMarker.hide()
        self.mSnapIndicator = QgsSnapIndicator(canvas)

    def pickVertex(self, point, segment=False):
        layers = [self.canvas().currentLayer()] if self.mMode == self.ActiveLayer else self.canvas().layers()
        tolerance = self.canvas().mapUnitsPerPixel() * 10
        rectangle = QgsRectangle(point.x()-tolerance, point.y()-tolerance, point.x()+tolerance, point.y()+tolerance)
        best, distance = None, tolerance * tolerance
        for layer in layers:
            if not isinstance(layer, QgsVectorLayer) or not layer.isEditable() or not layer.dataProvider().capabilities() & QgsVectorDataProvider.ChangeGeometries: continue
            local = self.toLayerCoordinates(layer, point)
            for feature in layer.getFeatures(QgsFeatureRequest().setFilterRect(self.toLayerCoordinates(layer, rectangle))):
                geometry = feature.geometry()
                if geometry.isEmpty(): continue
                if segment:
                    squared, vertex, index, _ = geometry.closestSegmentWithContext(local)
                    if squared < 0: continue
                else:
                    vertex, index, _, _, squared = geometry.closestVertex(local)
                    if index < 0: continue
                onMap = self.toMapCoordinates(layer, QgsPointXY(vertex))
                squared = onMap.sqrDist(point)
                if squared <= distance:
                    best, distance = (layer, feature.id(), index), squared
        return best

    def cadCanvasPressEvent(self, event):
        self.mSnapIndicator.setMatch(event.mapPointMatch())
        if event.button() == Qt.LeftButton:
            self.mVertex = self.pickVertex(event.mapPoint())
            self.mDragging = self.mVertex is not None
            if self.mVertex:
                layer, fid, index = self.mVertex
                self.vertexSelected.emit(layer, fid, index)
                self.mMarker.setCenter(self.toMapCoordinates(layer, QgsPointXY(layer.getFeature(fid).geometry().vertexAt(index))))
                self.mMarker.show()
        elif event.button() == Qt.RightButton: self.cancel()

    def cadCanvasMoveEvent(self, event):
        self.mSnapIndicator.setMatch(event.mapPointMatch())
        if self.mDragging: self.mMarker.setCenter(event.snapPoint())

    def cadCanvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self.mDragging: return
        self.mDragging = False
        layer, fid, index = self.mVertex
        point = self.toLayerCoordinates(layer, event.snapPoint())
        self.editVertex(layer, fid, index, point, 'move')
        self.mSnapIndicator.setMatch(QgsPointLocator.Match())

    def editVertex(self, layer, fid, index, point=None, operation='move'):
        if not layer.isEditable() or not layer.getFeature(fid).isValid(): return False
        layer.beginEditCommand({'move': '移动顶点', 'insert': '插入顶点', 'delete': '删除顶点'}[operation])
        if operation == 'delete': success = layer.deleteVertex(fid, index) == Qgis.VectorEditResult.Success
        elif operation == 'insert': success = layer.insertVertex(point.x(), point.y(), fid, index)
        else:
            vertex = layer.getFeature(fid).geometry().vertexAt(index)
            vertex.setX(point.x())
            vertex.setY(point.y())
            geometry = layer.getFeature(fid).geometry()
            success = geometry.moveVertex(vertex, index) and layer.changeGeometry(fid, geometry)
        if success: layer.endEditCommand()
        else: layer.destroyEditCommand()
        layer.triggerRepaint()
        return success

    def canvasDoubleClickEvent(self, event):
        found = self.pickVertex(event.mapPoint(), True)
        if found:
            layer, fid, index = found
            self.editVertex(layer, fid, index, self.toLayerCoordinates(layer, event.snapPoint()), 'insert')
        self.cancel()
    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Escape: self.cancel()
        elif event.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self.mVertex:
            self.editVertex(*self.mVertex, operation='delete')
            self.cancel()
        else: super().keyReleaseEvent(event)
    def cancel(self):
        self.mVertex = None
        self.mDragging = False
        self.mMarker.hide()
        self.mSnapIndicator.setMatch(QgsPointLocator.Match())
    def deactivate(self):
        self.cancel()
        super().deactivate()
