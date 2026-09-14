"""Port of qgsnewmeshlayerdialog.cpp: MDAL mesh-frame creation and copying."""
from pathlib import Path
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QMessageBox
from qgis.core import (Qgis, QgsProject, QgsProviderRegistry, QgsMeshDriverMetadata, QgsMesh, QgsMeshLayer,
                       QgsApplication)
from qgis.gui import QgsGui, QgsFileWidget, QgsHelp


class QgsNewMeshLayerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(str(Path(__file__).resolve().parents[2] / 'ui/mesh/qgsnewmeshlayerdialogbase.ui'), self)
        QgsGui.enableAutoGeometryRestore(self)
        self.mNewLayer, self.mSourceMeshFromFile = None, None
        self.mSourceMeshFrameReady = False
        self.mDriverSuffixes = {}
        self.mMetadata = QgsProviderRegistry.instance().providerMetadata('mdal')
        if self.mMetadata:
            for driver in self.mMetadata.meshDriversMetadata():
                if driver.capabilities() & QgsMeshDriverMetadata.CanWriteMeshData:
                    self.mFormatComboBox.addItem(driver.description(), driver.name())
                    self.mDriverSuffixes[driver.name()] = driver.writeMeshFrameOnFileSuffix()
        self.mFileWidget.setStorageMode(QgsFileWidget.SaveFile)
        self.mMeshFromFileWidget.setFilter(QgsProviderRegistry.instance().fileMeshFilters())
        self.mMeshProjectComboBox.setFilters(Qgis.LayerFilter.MeshLayer)
        self.mProjectionSelectionWidget.setCrs(QgsProject.instance().crs())
        self.mFormatComboBox.currentIndexChanged.connect(self.onFormatChanged)
        self.mFileWidget.fileChanged.connect(self.onFilePathChanged)
        self.mInitializeMeshGroupBox.toggled.connect(self.updateDialog)
        self.mMeshFileRadioButton.toggled.connect(self.updateDialog)
        self.mMeshFromFileWidget.fileChanged.connect(self.updateDialog)
        self.mMeshProjectComboBox.layerChanged.connect(self.updateDialog)
        self.buttonBox.helpRequested.connect(lambda: QgsHelp.openHelp('managing_data_source/create_layers.html#creating-a-new-mesh-layer'))
        self.onFormatChanged()

    def setCrs(self, crs): self.mProjectionSelectionWidget.setCrs(crs)
    def setSourceMeshLayer(self, layer, fromExistingAsDefault=False):
        self.mMeshProjectComboBox.setLayer(layer)
        self.mMeshProjectRadioButton.setChecked(True)
        self.mInitializeMeshGroupBox.setChecked(fromExistingAsDefault)
        self.updateDialog()

    def sourceMeshLayer(self):
        if not self.mInitializeMeshGroupBox.isChecked(): return None
        return self.mMeshProjectComboBox.currentLayer() if self.mMeshProjectRadioButton.isChecked() else self.mSourceMeshFromFile

    def updateDialog(self, *args):
        initialize = self.mInitializeMeshGroupBox.isChecked()
        fromFile = self.mMeshFileRadioButton.isChecked()
        self.mMeshProjectComboBox.setEnabled(initialize and not fromFile)
        self.mMeshFromFileWidget.setEnabled(initialize and fromFile)
        self.mProjectionSelectionWidget.setEnabled(not initialize)
        if initialize and fromFile:
            path = self.mMeshFromFileWidget.filePath()
            if not self.mSourceMeshFromFile or self.mSourceMeshFromFile.source() != path:
                self.mSourceMeshFromFile = QgsMeshLayer(path, '', 'mdal') if path else None
        source = self.sourceMeshLayer()
        self.mSourceMeshFrameReady = not initialize or bool(source and source.isValid())
        self.mInformationTextBrowser.document().setDefaultStyleSheet(QgsApplication.reportStyleSheet())
        self.mInformationTextBrowser.setHtml(source.htmlMetadata() if source and source.isValid() else '')
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(bool(self.mFileWidget.filePath() and self.mFormatComboBox.currentIndex() >= 0 and self.mSourceMeshFrameReady))

    def onFormatChanged(self, *args):
        suffix = self.mDriverSuffixes.get(self.mFormatComboBox.currentData(), '')
        self.mFileWidget.setFilter(self.mFormatComboBox.currentText() + ' (*.' + suffix + ')')
        path = self.mFileWidget.filePath()
        if path and suffix: self.mFileWidget.setFilePath(str(Path(path).with_suffix('.' + suffix)))
        self.updateDialog()

    def onFilePathChanged(self, path):
        suffix = Path(path).suffix.lower().lstrip('.')
        for driver, extension in self.mDriverSuffixes.items():
            if suffix == extension.lower():
                blocked = self.mFormatComboBox.blockSignals(True)
                self.mFormatComboBox.setCurrentIndex(self.mFormatComboBox.findData(driver))
                self.mFormatComboBox.blockSignals(blocked)
                break
        self.updateDialog()

    def outputFile(self):
        path = self.mFileWidget.filePath()
        suffix = self.mDriverSuffixes.get(self.mFormatComboBox.currentData(), '')
        return str(Path(path).with_suffix('.' + suffix)) if path and suffix else path

    def createLayer(self):
        self.updateDialog()
        if not self.buttonBox.button(QDialogButtonBox.Ok).isEnabled(): raise ValueError('请检查输出文件、格式和源网格')
        source, mesh = self.sourceMeshLayer(), QgsMesh()
        crs = source.crs() if source else self.mProjectionSelectionWidget.crs()
        if source:
            sourcePath = QgsProviderRegistry.instance().decodeUri(source.providerType(), source.source()).get('path', source.source())
            if Path(sourcePath).resolve() == Path(self.outputFile()).resolve(): raise ValueError('输出文件不能覆盖源网格')
            source.dataProvider().populateMesh(mesh)
        if not self.mMetadata.createMeshData(mesh, self.outputFile(), self.mFormatComboBox.currentData(), crs):
            raise RuntimeError('MDAL 无法创建此格式的网格')
        layer = QgsMeshLayer(self.outputFile(), self.mLayerNameLineEdit.text().strip() or Path(self.outputFile()).stem, 'mdal')
        if not layer.isValid(): raise RuntimeError('网格文件已写出，但无法加载')
        layer.setCrs(crs)
        self.mNewLayer = layer
        return layer

    def apply(self):
        try: layer = self.createLayer()
        except Exception as error:
            QMessageBox.warning(self, '创建网格失败', str(error))
            return False
        QgsProject.instance().addMapLayer(layer)
        return True

    def newLayer(self): return self.mNewLayer
    def accept(self):
        if Path(self.outputFile()).is_file() and QMessageBox.question(self, '覆盖网格文件', self.outputFile(), QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes: return
        if self.apply(): super().accept()
