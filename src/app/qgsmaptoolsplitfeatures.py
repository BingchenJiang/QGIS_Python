"""Application geometry editing capture with the native CAD/snapping pipeline."""
from qgis.core import Qgis, QgsGeometry, QgsFeatureRequest, QgsLineString, QgsVectorLayer, QgsProject, QgsCurvePolygon, QgsPointXY
from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsMapToolCapture


class _GeometryEditCapture(QgsMapToolCapture):
    def __init__(self, canvas, cadDock, operation, mode=QgsMapToolCapture.CaptureLine):
        super().__init__(canvas, cadDock, mode)
        self.mOperation = operation

    def cadCanvasReleaseEvent(self, event):
        geometry = None
        if self.mode() == self.CapturePoint and event.button() == Qt.LeftButton:
            geometry = QgsGeometry.fromPointXY(self.toLayerCoordinates(self.canvas().currentLayer(), event.mapPoint()))
        elif event.button() == Qt.RightButton and self.size() >= (3 if self.mode() == self.CapturePolygon else 2):
            if self.mode() == self.CapturePolygon:
                self.closePolygon()
                polygon = QgsCurvePolygon()
                polygon.setExteriorRing(self.captureCurve().clone())
                geometry = QgsGeometry(polygon)
            else: geometry = QgsGeometry(self.captureCurve().clone())
        # Keep the native CAD event handling and capture cleanup. Apply through
        # this exposed virtual handler instead of an app-private completion hook.
        super().cadCanvasReleaseEvent(event)
        if geometry is not None:
            self.applyGeometry(self.canvas().currentLayer(), geometry)

    def applyGeometry(self, layer, geometry):
        if not isinstance(layer, QgsVectorLayer) or not layer.isEditable(): return False
        labels = {'splitFeatures': '分割要素', 'splitParts': '分割部件', 'addRing': '添加环', 'addPart': '添加部件', 'reshape': '重塑要素'}
        label = labels[self.mOperation]
        layer.beginEditCommand(label)
        try:
            points = list(geometry.vertices())
            if self.mOperation in ('splitFeatures', 'splitParts'):
                result = getattr(layer, self.mOperation)([QgsPointXY(point) for point in points], QgsProject.instance().topologicalEditing())
                success = result == Qgis.GeometryOperationResult.Success
            elif self.mOperation == 'addRing':
                result = layer.addCurvedRing(geometry.constGet().exteriorRing().clone())
                success = (result[0] if isinstance(result, tuple) else result) == Qgis.GeometryOperationResult.Success
            elif self.mOperation == 'addPart':
                result = layer.addPartV2([QgsPointXY(point) for point in points])
                success = result == Qgis.GeometryOperationResult.Success
            else:
                candidates = layer.getSelectedFeatures() if layer.selectedFeatureCount() else layer.getFeatures(QgsFeatureRequest().setFilterRect(geometry.boundingBox()))
                success = False
                for feature in candidates:
                    edited = feature.geometry()
                    if edited.reshapeGeometry(QgsLineString(points)) == Qgis.GeometryOperationResult.Success:
                        if not layer.changeGeometry(feature.id(), edited): raise RuntimeError('图层拒绝几何修改')
                        success = True
            if success: layer.endEditCommand()
            else:
                layer.destroyEditCommand()
                self.messageEmitted.emit(label + '未完成：请检查图层类型、选择的要素及绘制范围', Qgis.Warning)
            layer.triggerRepaint()
            return success
        except Exception:
            layer.destroyEditCommand()
            raise


class QgsMapToolSplitFeatures(_GeometryEditCapture):
    def __init__(self, canvas, cadDock): super().__init__(canvas, cadDock, 'splitFeatures')
