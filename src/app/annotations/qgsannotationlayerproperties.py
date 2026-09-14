"""Port of src/app/annotations/qgsannotationlayerproperties.cpp (QGIS 3.34).

The C++ QgsLayerPropertiesDialog has SIP_SKIP pure virtual apply/syncToLayer
methods. Use its public options-dialog ancestor and implement the layer glue
here; the original UI and all rendering controls remain native QGIS widgets.
"""
from pathlib import Path
from qgis.PyQt import uic, sip
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import QDialogButtonBox, QPushButton, QMenu, QFileDialog, QMessageBox
from qgis.core import QgsApplication, QgsProject, QgsMapLayerStyle, QgsSettings, QgsProjectUtils
from qgis.gui import QgsOptionsDialogBase, QgsHelp


class QgsAnnotationLayerProperties(QgsOptionsDialogBase):
    def __init__(self, layer, canvas, messageBar=None, parent=None, flags=Qt.WindowFlags()):
        super().__init__('AnnotationLayerProperties', parent, flags)
        self.mLayer, self.mCanvas = layer, canvas
        self.mConfigWidgets = []
        self.mConfigFactories = []
        self.mMessageBar = messageBar
        self.mPaintEffect = None
        self.mBackupCrs = layer.crs()
        self.mOldStyle = QgsMapLayerStyle()
        self.mOldStyle.readFromLayer(layer)
        uic.loadUi(str(Path(__file__).resolve().parents[2] / 'ui/annotations/qgsannotationlayerpropertiesbase.ui'), self)
        self.initOptionsBase(False)
        self.accepted.connect(self.apply)
        self.rejected.connect(self.rollback)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.apply)
        self.buttonBox.helpRequested.connect(self.showHelp)
        self.mCrsSelector.crsChanged.connect(self.crsChanged)
        self.mInformationTextBrowser.setOpenLinks(False)
        self.mInformationTextBrowser.anchorClicked.connect(QDesktopServices.openUrl)
        self.mOptsPage_Information.setContentsMargins(0, 0, 0, 0)
        self.mBtnStyle = QPushButton(self.tr('Style'), self)
        self.mStyleMenu = QMenu(self.mBtnStyle)
        self.mStyleGroup = None
        self.mStyleMenu.aboutToShow.connect(self.aboutToShowStyleMenu)
        self.mBtnStyle.setMenu(self.mStyleMenu)
        self.buttonBox.addButton(self.mBtnStyle, QDialogButtonBox.ResetRole)
        self.syncToLayer()
        iface = getattr(parent, 'mQgisInterface', None)
        for factory in list(getattr(iface, 'mLayerConfigFactories', [])):
            self.addPropertiesPageFactory(factory)
        self.backupStyleManager()
        self.restoreOptionsBaseUi(self.tr('Layer Properties — ') + layer.name())

    def syncToLayer(self):
        layer = self.mLayer
        self.mLayerOrigNameLineEdit.setText(layer.name())
        self.mInformationTextBrowser.document().setDefaultStyleSheet(QgsApplication.reportStyleSheet() + 'body { margin: 10px; }')
        self.mInformationTextBrowser.setHtml(layer.htmlMetadata())
        blocked = self.mCrsSelector.blockSignals(True)
        self.mCrsSelector.setCrs(layer.crs())
        self.mCrsSelector.blockSignals(blocked)
        self.mScaleRangeWidget.setMapCanvas(self.mCanvas)
        self.mScaleRangeWidget.setScaleRange(layer.minimumScale(), layer.maximumScale())
        self.mScaleVisibilityGroupBox.setChecked(layer.hasScaleBasedVisibility())
        self.mBlendModeComboBox.setShowClippingModes(QgsProjectUtils.layerIsContainedInGroupLayer(QgsProject.instance(), layer))
        self.mBlendModeComboBox.setBlendMode(layer.blendMode())
        self.mOpacityWidget.setOpacity(layer.opacity())
        # Keep the old effect alive until the native widget releases its pointer.
        previous = self.mPaintEffect
        self.mPaintEffect = layer.paintEffect().clone() if layer.paintEffect() else None
        self.mEffectWidget.setPaintEffect(self.mPaintEffect)
        for widget in self.mConfigWidgets: widget.syncToLayer(layer)

    def addPropertiesPageFactory(self, factory):
        if factory in self.mConfigFactories or not factory.supportsLayer(self.mLayer) or not factory.supportLayerPropertiesDialog(): return
        page = factory.createWidget(self.mLayer, self.mCanvas, False, self)
        if page is None: return
        self.mConfigFactories.append(factory)
        self.mConfigWidgets.append(page)
        if not page.objectName(): page.setObjectName(type(page).__name__)
        before = factory.layerPropertiesPagePositionHint()
        if before: self.insertPage(factory.title(), factory.title(), factory.icon(), page, before)
        else: self.addPage(factory.title(), factory.title(), factory.icon(), page)
        page.syncToLayer(self.mLayer)

    def backupStyleManager(self):
        from qgis.PyQt.QtXml import QDomDocument
        self.mStyleManagerDocument = QDomDocument('styles')
        element = self.mStyleManagerDocument.createElement('map-layer-style-manager')
        self.mStyleManagerDocument.appendChild(element)
        self.mLayer.styleManager().writeXml(element)
        self.mBackupStyleName = self.mLayer.styleManager().currentStyle()

    def aboutToShowStyleMenu(self):
        from src.gui.qgsmaplayerstyleguiutils import QgsMapLayerStyleGuiUtils
        self.mStyleMenu.clear()
        if self.mStyleGroup is not None: sip.delete(self.mStyleGroup)
        self.mStyleMenu.addAction(self.tr('Load Style…'), self.loadStyleFromFile)
        self.mStyleMenu.addAction(self.tr('Save Style…'), self.saveStyleToFile)
        self.mStyleMenu.addSeparator()
        self.mStyleMenu.addAction(self.tr('Save as Default'), self.saveStyleAsDefault)
        self.mStyleMenu.addAction(self.tr('Restore Default'), self.loadDefaultStyle)
        self.mStyleMenu.addSeparator()
        self.mStyleGroup = QgsMapLayerStyleGuiUtils.instance().addStyleManagerActions(self.mStyleMenu, self.mLayer, self.syncToLayer)

    def apply(self):
        layer = self.mLayer
        layer.setName(self.mLayerOrigNameLineEdit.text())
        layer.setScaleBasedVisibility(self.mScaleVisibilityGroupBox.isChecked())
        layer.setMinimumScale(self.mScaleRangeWidget.minimumScale())
        layer.setMaximumScale(self.mScaleRangeWidget.maximumScale())
        layer.setBlendMode(self.mBlendModeComboBox.blendMode())
        layer.setOpacity(self.mOpacityWidget.opacity())
        if self.mPaintEffect:
            layer.setPaintEffect(self.mPaintEffect.clone())
        for widget in self.mConfigWidgets: widget.apply()
        self.mBackupCrs = layer.crs()
        self.mOldStyle.readFromLayer(layer)
        self.backupStyleManager()
        layer.triggerRepaint()
        QgsProject.instance().setDirty(True)

    def rollback(self):
        self.mLayer.styleManager().readXml(self.mStyleManagerDocument.documentElement())
        self.mLayer.styleManager().setCurrentStyle(self.mBackupStyleName)
        self.mOldStyle.writeToLayer(self.mLayer)
        self.mLayer.setCrs(self.mBackupCrs)
        self.mLayer.triggerRepaint()

    def crsChanged(self, crs):
        # QgsDatumTransformDialog is not exported in 3.34. The layer still uses
        # the project's native transform context; operation selection is deferred.
        self.mLayer.setCrs(crs)

    def loadStyleFromFile(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr('Load Style'), QgsSettings().value('style/lastStyleDir', ''), 'QGIS Layer Style (*.qml)')
        if path:
            self.loadStyle(path)

    def loadStyle(self, path):
        message, ok = self.mLayer.loadNamedStyle(path)
        if ok:
            self.syncToLayer()
            self.mLayer.triggerRepaint()
            QgsSettings().setValue('style/lastStyleDir', str(Path(path).parent))
        else:
            QMessageBox.warning(self, self.tr('Load Style'), message)
        return ok

    def saveStyleToFile(self):
        path, _ = QFileDialog.getSaveFileName(self, self.tr('Save Style'), QgsSettings().value('style/lastStyleDir', ''), 'QGIS Layer Style (*.qml)')
        if path:
            self.saveStyle(path if path.lower().endswith('.qml') else path + '.qml')

    def saveStyle(self, path):
        self.apply()
        message, ok = self.mLayer.saveNamedStyle(path)
        if ok:
            QgsSettings().setValue('style/lastStyleDir', str(Path(path).parent))
        else:
            QMessageBox.warning(self, self.tr('Save Style'), message)
        return ok

    def saveStyleAsDefault(self):
        self.apply()
        message, ok = self.mLayer.saveDefaultStyle()
        if not ok:
            QMessageBox.warning(self, self.tr('Default Style'), message)

    def loadDefaultStyle(self):
        message, ok = self.mLayer.loadDefaultStyle()
        if ok:
            self.syncToLayer()
            self.mLayer.triggerRepaint()
        else:
            QMessageBox.warning(self, self.tr('Default Style'), message)

    def showHelp(self):
        page = self.mOptionsStackedWidget.currentWidget().property('helpPage')
        QgsHelp.openHelp(page or 'map_views/map_view.html')
