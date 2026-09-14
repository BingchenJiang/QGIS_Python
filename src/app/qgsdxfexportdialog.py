"""QGIS 3.34 qgsdxfexportdialog.cpp: original form and native DXF exporter."""
from pathlib import Path
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QModelIndex, QSaveFile, QIODevice
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QItemDelegate, QAbstractItemView, QMessageBox, QApplication
from qgis.core import (Qgis, QgsProject, QgsSettings, QgsVectorLayer, QgsLayerTreeLayer,
                       QgsLayerTreeModel, QgsDxfExport, QgsMapSettings,
                       QgsCoordinateReferenceSystem, QgsCoordinateTransform)
from qgis.gui import QgsGui, QgsFileWidget, QgsFieldComboBox, QgsHelp


class FieldSelectorDelegate(QItemDelegate):
    def createEditor(self, parent, option, index):
        layer = index.model().vectorLayer(index)
        if index.column() != 1 or not layer: return None
        editor = QgsFieldComboBox(parent)
        editor.setAllowEmptyFieldName(True)
        editor.setLayer(layer)
        return editor

    def setEditorData(self, editor, index):
        layer = index.model().vectorLayer(index)
        attribute = index.model().attributeIndex(layer)
        editor.setField(layer.fields().at(attribute).name() if attribute >= 0 else '')

    def setModelData(self, editor, model, index):
        model.setData(index, model.vectorLayer(index).fields().lookupField(editor.currentField()), Qt.EditRole)


class QgsVectorLayerAndAttributeModel(QgsLayerTreeModel):
    def __init__(self, rootNode, parent=None):
        super().__init__(rootNode, parent)
        self.mAttributeIdx = {}
        self.setFlags(QgsLayerTreeModel.AllowNodeChangeVisibility)

    def columnCount(self, parent=QModelIndex()): return 2

    def vectorLayer(self, index):
        node = self.index2node(index.sibling(index.row(), 0))
        return node.layer() if isinstance(node, QgsLayerTreeLayer) else None

    def attributeIndex(self, layer): return self.mAttributeIdx.get(layer.id(), -1)

    def flags(self, index):
        if not index.isValid(): return Qt.NoItemFlags
        if index.column() == 0: return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable
        return Qt.ItemIsEnabled | (Qt.ItemIsEditable if self.vectorLayer(index) else Qt.NoItemFlags)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return ('图层', '输出图层名称字段')[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if index.column() == 0: return super().data(index, role)
        layer = self.vectorLayer(index)
        if not layer: return None
        field = self.attributeIndex(layer)
        if role == Qt.EditRole: return field
        if role == Qt.DisplayRole: return layer.fields().at(field).name() if field >= 0 else layer.name()
        if role == Qt.ToolTipRole: return '双击选择字段，将要素按字段值分配到 DXF 图层；留空使用图层名称。'
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if index.column() == 1 and role == Qt.EditRole:
            layer = self.vectorLayer(index)
            if not layer: return False
            self.mAttributeIdx[layer.id()] = int(value)
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True
        return super().setData(index, value, role)

    def layers(self):
        selected = {node.layerId() for node in self.rootGroup().findLayers() if node.isVisible()}
        return [QgsDxfExport.DxfLayer(layer, self.attributeIndex(layer))
                for layer in reversed(QgsProject.instance().layerTreeRoot().layerOrder())
                if layer.id() in selected and isinstance(layer, QgsVectorLayer)]

    def applyVisibilityPreset(self, name, canvas):
        ids = set(QgsProject.instance().mapThemeCollection().mapThemeVisibleLayerIds(name)) if name else {layer.id() for layer in canvas.layers()}
        self.rootGroup().setItemVisibilityCheckedRecursive(True)
        for node in self.rootGroup().findLayers(): node.setItemVisibilityChecked(node.layerId() in ids)

    def selectAll(self): self.rootGroup().setItemVisibilityCheckedRecursive(True)
    def deSelectAll(self): self.rootGroup().setItemVisibilityCheckedRecursive(False)


class QgsDxfExportDialog(QDialog):
    def __init__(self, parent=None, canvas=None):
        super().__init__(parent)
        uic.loadUi(str(Path(__file__).resolve().parents[1] / 'ui/qgsdxfexportdialogbase.ui'), self)
        QgsGui.enableAutoGeometryRestore(self)
        self.mCanvas = canvas or parent.mMapCanvas
        self.mLayerTreeGroup = QgsProject.instance().layerTreeRoot().clone()
        self.cleanGroup(self.mLayerTreeGroup)
        self.mModel = QgsVectorLayerAndAttributeModel(self.mLayerTreeGroup, self)
        self.mTreeView.setModel(self.mModel)
        self.mFieldSelectorDelegate = FieldSelectorDelegate(self)
        self.mTreeView.setItemDelegateForColumn(1, self.mFieldSelectorDelegate)
        self.mTreeView.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.mTreeView.header().show()
        self.mTreeView.expandAll()
        self.mTreeView.resizeColumnToContents(0)
        self.mModel.dataChanged.connect(self.setOkEnabled)
        self.mFileName.setStorageMode(QgsFileWidget.SaveFile)
        self.mFileName.setFilter('DXF (*.dxf *.DXF)')
        self.mFileName.setDefaultRoot(QgsSettings().value('qgis/lastDxfDir', str(Path.home())))
        self.mFileName.fileChanged.connect(self.setOkEnabled)
        self.mSelectAllButton.clicked.connect(self.mModel.selectAll)
        self.mDeselectAllButton.clicked.connect(self.mModel.deSelectAll)
        for title, mode in [('无符号', Qgis.FeatureSymbologyExport.NoSymbology), ('要素符号', Qgis.FeatureSymbologyExport.PerFeature), ('符号层', Qgis.FeatureSymbologyExport.PerSymbolLayer)]:
            self.mSymbologyModeComboBox.addItem(title, mode)
        self.mSymbologyModeComboBox.setCurrentIndex(int(self.setting('lastDxfSymbologyMode', '2')))
        self.mScaleWidget.setMapCanvas(self.mCanvas)
        oldScale = self.setting('lastSymbologyExportScale', '0.00002')
        try: self.mScaleWidget.setScale(1 / float(oldScale))
        except (ValueError, ZeroDivisionError): self.mScaleWidget.setScale(50000)
        for widget, key, default in self.booleanSettings():
            widget.setChecked(self.setting(key, default).lower() in ('true', '1'))
        crs = QgsCoordinateReferenceSystem.fromSrsId(int(self.setting('lastDxfCrs', str(QgsProject.instance().crs().srsid()))))
        self.mCrsSelector.setCrs(crs)
        self.mCrsSelector.setShowAccuracyWarnings(True)
        self.mCrsSelector.crsChanged.connect(self.setOkEnabled)
        self.mEncoding.addItems(QgsDxfExport.encodings())
        self.mEncoding.setCurrentText(self.setting('lastDxfEncoding', 'CP1252'))
        self.mVisibilityPresets.addItems([''] + QgsProject.instance().mapThemeCollection().mapThemes())
        self.mVisibilityPresets.setCurrentText(self.setting('lastVisibilityPreset', ''))
        self.mVisibilityPresets.currentTextChanged.connect(self.applyVisibilityPreset)
        self.applyVisibilityPreset(self.mapTheme())
        self.buttonBox.helpRequested.connect(lambda: QgsHelp.openHelp('managing_data_source/create_layers.html#create-dxf-files'))
        self.setOkEnabled()

    def setting(self, name, default):
        value = QgsSettings().value('qgis/' + name, default)
        return QgsProject.instance().readEntry('dxf', '/' + name, str(value))[0]

    def booleanSettings(self):
        return [(self.mLayerTitleAsName, 'lastDxfLayerTitleAsName', 'false'),
                (self.mMapExtentCheckBox, 'lastDxfMapRectangle', 'false'),
                (self.mMTextCheckBox, 'lastDxfUseMText', 'true'), (self.mForce2d, 'lastDxfForce2d', 'false')]

    def cleanGroup(self, group):
        for child in list(group.children()):
            if isinstance(child, QgsLayerTreeLayer):
                layer = child.layer()
                if not isinstance(layer, QgsVectorLayer) or not layer.isSpatial(): group.removeChildNode(child)
            else:
                self.cleanGroup(child)
                if not child.children(): group.removeChildNode(child)

    def applyVisibilityPreset(self, name):
        self.mModel.applyVisibilityPreset(name, self.mCanvas)
        self.setOkEnabled()

    def layers(self): return self.mModel.layers()
    def symbologyScale(self): return self.mScaleWidget.scale() or 1.0
    def symbologyMode(self): return self.mSymbologyModeComboBox.currentData()
    def crs(self): return self.mCrsSelector.crs()
    def mapTheme(self): return self.mVisibilityPresets.currentText()
    def encoding(self): return self.mEncoding.currentText()
    def exportMapExtent(self): return self.mMapExtentCheckBox.isChecked()
    def layerTitleAsName(self): return self.mLayerTitleAsName.isChecked()
    def force2d(self): return self.mForce2d.isChecked()
    def useMText(self): return self.mMTextCheckBox.isChecked()
    def saveFile(self):
        path = self.mFileName.filePath()
        return path if not path or path.lower().endswith('.dxf') else path + '.dxf'

    def setOkEnabled(self, *args):
        path = self.saveFile()
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(bool(path and Path(path).parent.is_dir() and self.crs().isValid() and self.layers()))

    def saveSettings(self):
        values = {'lastDxfSymbologyMode': self.mSymbologyModeComboBox.currentIndex(),
                  'lastSymbologyExportScale': 1 / self.symbologyScale(), 'lastDxfEncoding': self.encoding(),
                  'lastDxfCrs': self.crs().srsid(), 'lastVisibilityPreset': self.mapTheme()}
        values.update({key: widget.isChecked() for widget, key, _ in self.booleanSettings()})
        for key, value in values.items():
            QgsSettings().setValue('qgis/' + key, value)
            QgsProject.instance().writeEntry('dxf', '/' + key, str(value).lower() if isinstance(value, bool) else str(value))
        QgsSettings().setValue('qgis/lastDxfDir', str(Path(self.saveFile()).parent))

    def exportToFile(self):
        exporter = QgsDxfExport()
        settings = QgsMapSettings(self.mCanvas.mapSettings())
        settings.setLayerStyleOverrides(QgsProject.instance().mapThemeCollection().mapThemeStyleOverrides(self.mapTheme()))
        exporter.setMapSettings(settings)
        exporter.addLayers(self.layers())
        exporter.setSymbologyScale(self.symbologyScale())
        exporter.setSymbologyExport(self.symbologyMode())
        exporter.setLayerTitleAsName(self.layerTitleAsName())
        exporter.setDestinationCrs(self.crs())
        exporter.setForce2d(self.force2d())
        if not self.useMText(): exporter.setFlags(QgsDxfExport.FlagNoMText)
        if self.exportMapExtent():
            transform = QgsCoordinateTransform(settings.destinationCrs(), self.crs(), QgsProject.instance())
            transform.setBallparkTransformsAreAppropriate(True)
            exporter.setExtent(transform.transformBoundingBox(self.mCanvas.extent()))
        device = QSaveFile(self.saveFile())
        if not device.open(QIODevice.WriteOnly): raise OSError(device.errorString())
        result = exporter.writeToFile(device, self.encoding())
        if result != QgsDxfExport.ExportResult.Success:
            device.cancelWriting()
            raise RuntimeError('DXF 导出失败：' + str(result))
        if not device.commit(): raise OSError(device.errorString())
        self.saveSettings()
        return self.saveFile()

    def accept(self):
        if not self.buttonBox.button(QDialogButtonBox.Ok).isEnabled(): return
        if Path(self.saveFile()).exists() and QMessageBox.question(self, '覆盖 DXF', self.saveFile(), QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes: return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.exportToFile()
        except Exception as error:
            QMessageBox.warning(self, 'DXF 导出失败', str(error))
            return
        finally:
            QApplication.restoreOverrideCursor()
        super().accept()
