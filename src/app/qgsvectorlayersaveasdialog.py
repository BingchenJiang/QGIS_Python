"""Application export adapter; all dialog controls use native QgsVectorLayerSaveAsDialog."""
from qgis.core import QgsVectorFileWriter, QgsCoordinateTransform, QgsField, QgsApplication
from qgis.PyQt.QtCore import QVariant


class QgisAppFieldValueConverter(QgsVectorFileWriter.FieldValueConverter):
    def __init__(self, layer, indices, exportNames=()):
        super().__init__()
        self.mLayer, self.mIndices, self.mCaches = layer, set(indices), {}
        self.mAttributesExportNames = list(exportNames)
        for index in self.mIndices:
            setup = layer.editorWidgetSetup(index)
            formatter = QgsApplication.fieldFormatterRegistry().fieldFormatter(setup.type())
            self.mCaches[index] = formatter, setup.config(), formatter.createCache(layer, index, setup.config())
    def clone(self): return QgisAppFieldValueConverter(self.mLayer, self.mIndices, self.mAttributesExportNames)
    def fieldDefinition(self, field):
        index = self.mLayer.fields().lookupField(field.name())
        if index < 0 and field.name() in self.mAttributesExportNames: index = self.mAttributesExportNames.index(field.name())
        if index in self.mIndices:
            field = QgsField(field)
            field.setType(QVariant.String)
            field.setTypeName('String')
        return field
    def convert(self, index, value):
        if index not in self.mIndices: return value
        formatter, config, cache = self.mCaches[index]
        return formatter.representValue(self.mLayer, index, config, cache, value)


def saveOptionsFromDialog(dialog, layer, project):
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName, options.fileEncoding, options.layerName = dialog.format(), dialog.encoding(), dialog.layerName()
    options.actionOnExistingFile = dialog.creationActionOnExistingFile()
    options.onlySelectedFeatures = dialog.onlySelected()
    options.attributes = dialog.selectedAttributes()
    options.skipAttributeCreation = not bool(options.attributes)
    options.attributesExportNames = dialog.attributesExportNames()
    options.datasourceOptions, options.layerOptions = dialog.datasourceOptions(), dialog.layerOptions()
    if dialog.crs().isValid() and layer.crs().isValid(): options.ct = QgsCoordinateTransform(layer.crs(), dialog.crs(), project)
    if dialog.hasFilterExtent(): options.filterExtent = dialog.filterExtent()
    options.symbologyExport, options.symbologyScale = dialog.symbologyExport(), dialog.scale()
    if not dialog.automaticGeometryType(): options.overrideGeometryType = dialog.geometryType()
    options.forceMulti, options.includeZ = dialog.forceMulti(), dialog.includeZ()
    options.saveMetadata = dialog.persistMetadata()
    options.layerMetadata = layer.metadata()
    converter = QgisAppFieldValueConverter(layer, dialog.attributesAsDisplayedValues(), dialog.attributesExportNames())
    options.fieldValueConverter = converter
    return options, converter
