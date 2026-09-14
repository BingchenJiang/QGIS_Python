"""QgsMapToolShowHideLabels: current-layer label/feature rectangle interaction."""
from qgis.PyQt.QtCore import Qt
from qgis.core import (
    QgsVectorLayer, QgsLabelPosition, QgsPalLayerSettings, QgsDiagramLayerSettings,
    QgsFeatureRequest, QgsGeometry, QgsCoordinateTransform, QgsProject,
)
from .qgsmaptoollabel import QgsMapToolLabel


class QgsMapToolShowHideLabels(QgsMapToolLabel):
    def canvasPressEvent(self, event): self.beginSelect(event)
    def canvasMoveEvent(self, event): self.updateSelect(event)

    def canvasReleaseEvent(self, event):
        selection = self.endSelect(event)
        if selection and event.button() == Qt.LeftButton:
            self.showHideLabels(*selection, event.modifiers())

    def showHideLabels(self, extent, dragging=False, modifiers=Qt.NoModifier):
        layer = self.canvas().currentLayer()
        if not isinstance(layer, QgsVectorLayer): return 0
        results = self.canvas().labelingResults(False)
        positions = [p for p in results.labelsWithinRect(extent) if p.layerID == layer.id()] if results else []
        hide = bool(modifiers & Qt.ShiftModifier) if dragging else bool(positions)
        if not hide:
            geometry = QgsGeometry.fromRect(extent)
            geometry.transform(QgsCoordinateTransform(self.canvas().mapSettings().destinationCrs(), layer.crs(), QgsProject.instance()))
            request = QgsFeatureRequest().setFilterRect(geometry.boundingBox()).setFlags(QgsFeatureRequest.ExactIntersect)
            features = list(layer.getFeatures(request))
            if not dragging: features = features[:1]
            positions = []
            for feature in features:
                # Rules retain their provider IDs, so each mapped Show field is updated.
                providers = layer.labeling().subProviders() if layer.labelsEnabled() else []
                for provider in providers:
                    pos = QgsLabelPosition()
                    pos.layerID, pos.providerID, pos.featureId, pos.isDiagram = layer.id(), provider, feature.id(), False
                    positions.append(pos)
                if layer.diagramsEnabled():
                    pos = QgsLabelPosition()
                    pos.layerID, pos.featureId, pos.isDiagram = layer.id(), feature.id(), True
                    positions.append(pos)
        elif not dragging: positions = positions[:1]
        changed, seen = 0, set()
        for pos in positions:
            key = (pos.providerID, pos.featureId, pos.isDiagram)
            if key in seen: continue
            seen.add(key)
            if self.showHide(pos, not hide): changed += 1
        return changed

    def showHide(self, pos, show):
        details = self.details(pos)
        if not details: return False
        prop = QgsDiagramLayerSettings.Show if pos.isDiagram else QgsPalLayerSettings.Show
        indexes = self.createAuxiliaryFields(details, [prop])
        return bool(indexes and self.writeChanges(details, {indexes[prop]: int(show)}, '显示标注' if show else '隐藏标注'))
