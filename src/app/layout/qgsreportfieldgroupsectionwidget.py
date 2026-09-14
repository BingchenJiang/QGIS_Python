"""Native field-group controls, report contexts and inclusion policies."""
from qgis.core import QgsMapLayerProxyModel, QgsReportSectionFieldGroup
from .qgsreportsectionwidget import QgsReportSectionWidget


class QgsReportSectionFieldGroupWidget(QgsReportSectionWidget):
    uiName = 'qgsreportwidgetfieldgroupsectionbase.ui'

    def __init__(self, parent, designer, section):
        super().__init__(parent, designer, section)
        self.mLayerComboBox.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.mLayerComboBox.setAllowEmptyLayer(True)
        self.mLayerComboBox.setLayer(section.layer())
        self.mFieldComboBox.setAllowEmptyFieldName(True)
        self.mFieldComboBox.setLayer(section.layer())
        self.mFieldComboBox.setField(section.field())
        self.mSortAscendingCheckBox.setChecked(section.sortAscending())
        self.mCheckHeaderAlwaysVisible.setChecked(section.headerVisibility() == QgsReportSectionFieldGroup.AlwaysInclude)
        self.mCheckFooterAlwaysVisible.setChecked(section.footerVisibility() == QgsReportSectionFieldGroup.AlwaysInclude)
        self.mCheckHeaderAlwaysVisible.setEnabled(section.headerEnabled())
        self.mCheckFooterAlwaysVisible.setEnabled(section.footerEnabled())
        self.mLayerComboBox.layerChanged.connect(self.setLayer)
        self.mFieldComboBox.fieldChanged.connect(self.setField)
        self.mSortAscendingCheckBox.toggled.connect(self.sortAscendingToggled)
        self.mCheckHeaderAlwaysVisible.toggled.connect(self.toggleHeaderAlwaysVisible)
        self.mCheckFooterAlwaysVisible.toggled.connect(self.toggleFooterAlwaysVisible)

    def toggleHeader(self, enabled):
        super().toggleHeader(enabled)
        self.mCheckHeaderAlwaysVisible.setEnabled(enabled)

    def toggleFooter(self, enabled):
        super().toggleFooter(enabled)
        self.mCheckFooterAlwaysVisible.setEnabled(enabled)

    def toggleHeaderAlwaysVisible(self, enabled):
        self.mSection.setHeaderVisibility(QgsReportSectionFieldGroup.AlwaysInclude if enabled else QgsReportSectionFieldGroup.IncludeWhenFeaturesFound)
        self.changed()

    def toggleFooterAlwaysVisible(self, enabled):
        self.mSection.setFooterVisibility(QgsReportSectionFieldGroup.AlwaysInclude if enabled else QgsReportSectionFieldGroup.IncludeWhenFeaturesFound)
        self.changed()

    def sortAscendingToggled(self, checked):
        self.mSection.setSortAscending(checked)
        self.changed()

    def setLayer(self, layer):
        self.mSection.setLayer(layer)
        previousField = self.mSection.field()
        self.mFieldComboBox.blockSignals(True)
        self.mFieldComboBox.setLayer(layer)
        self.mFieldComboBox.setField(previousField if layer and layer.fields().lookupField(previousField) >= 0 else '')
        self.mFieldComboBox.blockSignals(False)
        self.mSection.setField(self.mFieldComboBox.currentField())
        for layout in (self.mSection.header(), self.mSection.body(), self.mSection.footer()):
            if layout is not None: layout.reportContext().setLayer(layer)
        self.changed()

    def setField(self, field):
        self.mSection.setField(field)
        self.changed()
