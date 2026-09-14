"""QgsMapToolPinLabels: pin/unpin labels and diagrams, highlight pins/callouts."""
from qgis.PyQt import sip
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import Qgis, QgsPalLayerSettings, QgsUnitTypes, QgsPointXY
from qgis.gui import QgsRubberBand
from .qgsmaptoollabel import QgsMapToolLabel


class QgsMapToolPinLabels(QgsMapToolLabel):
    def __init__(self, canvas, cadDock):
        super().__init__(canvas, cadDock)
        self.mShowPinned = False
        self.mHighlights = []
        canvas.mapCanvasRefreshed.connect(self.highlightPinnedLabels)

    def canvasPressEvent(self, event): self.beginSelect(event)
    def canvasMoveEvent(self, event): self.updateSelect(event)

    def canvasReleaseEvent(self, event):
        selection = self.endSelect(event)
        if not selection or event.button() != Qt.LeftButton: return
        self.pinUnpinLabels(selection[0], event.modifiers())

    def pinUnpinLabels(self, extent, modifiers=Qt.NoModifier):
        results = self.canvas().labelingResults(False)
        if not results: return 0
        changed, seen = 0, set()
        for pos in results.labelsWithinRect(extent):
            key = (pos.layerID, pos.providerID, pos.featureId, pos.isDiagram)
            if key in seen: continue
            seen.add(key)
            details = self.details(pos)
            if not details: continue
            pinned = self.isPinned(details)
            pin = not pinned if modifiers & Qt.ControlModifier else not bool(modifiers & Qt.ShiftModifier)
            if pin != pinned and self.pinUnpinCurrentFeature(pin, details): changed += 1
        if changed:
            self.showPinnedLabels(True)
            from ..qgisapp import QgisApp
            QgisApp.instance().mActionShowPinnedLabels.setChecked(True)
        return changed

    def pinUnpinCurrentFeature(self, pin, details=None):
        details = details or self.mCurrentLabel
        if not details: return False
        point = self.currentLabelRotationPoint(details) if pin else None
        changes = self.positionChanges(details, point, create=pin)
        if changes is None:
            if pin: return False
            changes = {}
        if not pin and not details.pos.isDiagram:
            for prop in (QgsPalLayerSettings.LineAnchorPercent, QgsPalLayerSettings.LineAnchorClipping,
                         QgsPalLayerSettings.LineAnchorType, QgsPalLayerSettings.LineAnchorTextPoint):
                index = self.dataDefinedColumnIndex(prop, details)
                if index >= 0: changes[index] = None
        if not details.pos.isDiagram and not details.settings.preserveRotation:
            index = self.dataDefinedColumnIndex(QgsPalLayerSettings.LabelRotation, details)
            if index >= 0:
                factor = QgsUnitTypes.fromUnitToUnitFactor(Qgis.AngleUnit.Degrees, details.settings.rotationUnit())
                changes[index] = details.pos.rotation * factor if pin else None
        return self.writeChanges(details, changes, '固定标注' if pin else '解除固定标注')

    def showPinnedLabels(self, show):
        self.mShowPinned = show
        self.highlightPinnedLabels()

    def updatePinnedLabels(self):
        if self.mShowPinned: self.highlightPinnedLabels()

    def removePinnedHighlights(self):
        for band in self.mHighlights:
            if not sip.isdeleted(band): sip.delete(band)
        self.mHighlights.clear()

    def highlightPinnedLabels(self):
        self.removePinnedHighlights()
        if not self.mShowPinned: return
        results = self.canvas().labelingResults(False)
        if not results: return
        seen = set()
        for pos in results.labelsWithinRect(self.canvas().extent()):
            details = self.details(pos)
            # The renderer also knows positions fixed by expressions and the
            # placement engine. Do not infer every pin solely from fields.
            if not details or not (pos.isPinned or self.isPinned(details)): continue
            key = (pos.layerID, pos.providerID, pos.featureId, pos.isDiagram)
            if key in seen and not pos.groupedLabelId: continue
            seen.add(key)
            color = QColor(54, 129, 0 if details.layer.isEditable() else 255, 63)
            self.mHighlights.append(self.labelBand(pos, color))
        for callout in results.calloutsWithinRectangle(self.canvas().extent()):
            for pinned, point in [(callout.originIsPinned(), callout.origin()), (callout.destinationIsPinned(), callout.destination())]:
                if not pinned: continue
                band = QgsRubberBand(self.canvas(), Qgis.GeometryType.Point)
                band.setColor(QColor(54, 129, 255, 160))
                band.setIcon(QgsRubberBand.ICON_X)
                band.setIconSize(self.canvas().fontMetrics().xHeight())
                band.addPoint(QgsPointXY(point))
                self.mHighlights.append(band)
