"""QgsMapToolChangeLabelProperties and native-form per-feature overrides."""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog
from qgis.core import QgsPalLayerSettings
from .qgsmaptoollabel import QgsMapToolLabel
from .qgslabelpropertydialog import QgsLabelPropertyDialog


class QgsMapToolChangeLabelProperties(QgsMapToolLabel):
    def canvasPressEvent(self, event):
        self.cancel()
        if event.button() != Qt.LeftButton: return
        pos = self.labelAtPosition(event)
        if not pos or pos.isDiagram: return
        self.mCurrentLabel = self.details(pos)
        self.createRubberBands()

    def canvasReleaseEvent(self, event):
        if not self.mCurrentLabel or event.button() != Qt.LeftButton: return
        self.showDialog(self.mCurrentLabel)
        self.cancel()

    def showDialog(self, details):
        properties = list(QgsLabelPropertyDialog.CONTROLS) + [QgsPalLayerSettings.ScaleVisibility]
        if not self.createAuxiliaryFields(details, properties): return False
        self.mCurrentLabel = details
        dialog = QgsLabelPropertyDialog(details, self)
        def apply():
            if self.applyChanges(dialog.changedProperties()): dialog.clearChanges()
        dialog.applied.connect(apply)
        accepted = dialog.exec_() == QDialog.Accepted
        if accepted: apply()
        dialog.deleteLater()
        return accepted

    def applyChanges(self, changes):
        return self.writeChanges(self.mCurrentLabel, changes, '修改标注属性') if self.mCurrentLabel else False
