"""QGIS 3.34 mesh calculator: original UI, native persistent/virtual calculation."""
from pathlib import Path
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFontDatabase
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QMessageBox, QProgressDialog
from qgis.core import (Qgis, QgsProject, QgsApplication, QgsSettings, QgsMeshCalculator,
                       QgsMeshDriverMetadata, QgsMeshDatasetGroup, QgsMeshDatasetIndex,
                       QgsMeshDatasetGroupMetadata, QgsProviderRegistry, QgsRectangle,
                       QgsGeometry, QgsCoordinateTransform, QgsFeedback)
from qgis.gui import QgsGui, QgsFileWidget, QgsHelp
from src.gui.mesh.qgsmeshdatasetgrouptreeview import QgsMeshDatasetGroupListModel


class QgsMeshCalculatorDialog(QDialog):
    def __init__(self, meshLayer, parent=None):
        super().__init__(parent)
        self.mLayer = meshLayer
        uic.loadUi(str(Path(__file__).resolve().parents[2] / 'ui/mesh/qgsmeshcalculatordialogbase.ui'), self)
        QgsGui.enableAutoGeometryRestore(self)
        self.mModel = QgsMeshDatasetGroupListModel(self)
        self.mModel.syncToLayer(meshLayer)
        self.mModel.setDisplayProviderName(True)
        self.mDatasetsListWidget.setModel(self.mModel)
        self.mVariableNames = self.mModel.variableNames()
        self.mMeshDrivers = {}
        metadata = QgsProviderRegistry.instance().providerMetadata('mdal')
        if metadata:
            for driver in metadata.meshDriversMetadata():
                if driver.capabilities() & (QgsMeshDriverMetadata.CanWriteFaceDatasets | QgsMeshDriverMetadata.CanWriteVertexDatasets | QgsMeshDriverMetadata.CanWriteEdgeDatasets):
                    self.mMeshDrivers[driver.name()] = driver
                    self.mOutputFormatComboBox.addItem(driver.description(), driver.name())
        self.cboLayerMask.setFilters(Qgis.LayerFilter.PolygonLayer)
        self.cboLayerMask.layerChanged.connect(self.updateInfoMessage)
        self.mOutputDatasetFileWidget.setStorageMode(QgsFileWidget.SaveFile)
        self.mOutputDatasetFileWidget.setDefaultRoot(QgsSettings().value('MeshCalculator/lastOutputDir', str(Path.home())))
        self.mDatasetsListWidget.doubleClicked.connect(self.datasetGroupEntry)
        self.mCurrentLayerExtentButton.clicked.connect(self.useFullLayerExtent)
        self.mAllTimesButton.clicked.connect(self.useAllTimesFromLayer)
        self.mExpressionTextEdit.setCurrentFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.mExpressionTextEdit.textChanged.connect(self.updateInfoMessage)
        self.mOutputGroupNameLineEdit.textChanged.connect(self.updateInfoMessage)
        self.mOutputDatasetFileWidget.fileChanged.connect(self.updateInfoMessage)
        self.mOutputFormatComboBox.currentIndexChanged.connect(self.onOutputFormatChange)
        self.mUseVirtualProviderCheckBox.toggled.connect(self.onVirtualCheckboxChange)
        self.useMaskCb.toggled.connect(self.toggleExtendMask)
        tokens = {'PlusPushButton': '+', 'MinusPushButton': '-', 'MultiplyPushButton': '*', 'DividePushButton': '/',
                  'OpenBracketPushButton': '(', 'CloseBracketPushButton': ')', 'LessButton': '<', 'GreaterButton': '>',
                  'EqualButton': '=', 'LesserEqualButton': '<=', 'GreaterEqualButton': '>=', 'NotEqualButton': '!=',
                  'MinButton': 'min( A , B )', 'MaxButton': 'max( A , B )', 'AbsButton': 'abs(', 'PowButton': '^',
                  'IfButton': 'if( 1 = 1 , NODATA , NODATA )', 'AndButton': 'and', 'OrButton': 'or', 'NotButton': 'not',
                  'SumAggrButton': 'sum_aggr(', 'MaxAggrButton': 'max_aggr(', 'MinAggrButton': 'min_aggr(',
                  'AverageAggrButton': 'average_aggr(', 'NoDataButton': 'NODATA'}
        for name, token in tokens.items():
            getattr(self, 'm' + name).clicked.connect(lambda checked=False, token=token: self.mExpressionTextEdit.insertPlainText(' ' + token + ' '))
        for widget in (self.mXMinSpinBox, self.mYMinSpinBox, self.mXMaxSpinBox, self.mYMaxSpinBox):
            widget.setShowClearButton(False)
            widget.valueChanged.connect(self.updateInfoMessage)
        self.useFullLayerExtent()
        self.repopulateTimeCombos()
        self.mStartTimeComboBox.currentIndexChanged.connect(self.updateInfoMessage)
        self.mEndTimeComboBox.currentIndexChanged.connect(self.updateInfoMessage)
        self.mButtonBox.helpRequested.connect(lambda: QgsHelp.openHelp('working_with_mesh/mesh_properties.html#mesh-calculator'))
        self.onOutputFormatChange()
        self.onVirtualCheckboxChange()
        self.toggleExtendMask()

    def formulaString(self): return self.mExpressionTextEdit.toPlainText()
    def meshLayer(self): return self.mLayer
    def driver(self): return self.mOutputFormatComboBox.currentData()
    def groupName(self): return self.mOutputGroupNameLineEdit.text().strip()
    def startTime(self): return float(self.mStartTimeComboBox.currentData() or 0)
    def endTime(self): return float(self.mEndTimeComboBox.currentData() or 0)
    def outputExtent(self): return QgsRectangle(self.mXMinSpinBox.value(), self.mYMinSpinBox.value(), self.mXMaxSpinBox.value(), self.mYMaxSpinBox.value())
    def currentOutputSuffix(self):
        driver = self.mMeshDrivers.get(self.driver())
        return driver.writeDatasetOnFileSuffix() if driver else ''
    def outputFile(self):
        path, suffix = self.mOutputDatasetFileWidget.filePath(), self.currentOutputSuffix()
        return str(Path(path).with_suffix('.' + suffix)) if path and suffix else path

    def datasetGroupEntry(self, index):
        self.mExpressionTextEdit.insertPlainText(' "' + index.data().replace('"', '\\"') + '" ')

    def useFullLayerExtent(self):
        extent = self.mLayer.extent()
        for widget, value in [(self.mXMinSpinBox, extent.xMinimum()), (self.mYMinSpinBox, extent.yMinimum()),
                              (self.mXMaxSpinBox, extent.xMaximum()), (self.mYMaxSpinBox, extent.yMaximum())]: widget.setValue(value)

    def repopulateTimeCombos(self):
        times = set()
        for group in self.mLayer.datasetGroupsIndexes():
            for dataset in range(self.mLayer.datasetCount(QgsMeshDatasetIndex(group, 0))):
                times.add(self.mLayer.datasetMetadata(QgsMeshDatasetIndex(group, dataset)).time())
        for combo in (self.mStartTimeComboBox, self.mEndTimeComboBox):
            combo.clear()
            for time in sorted(times): combo.addItem(self.mLayer.formatTime(time), time)
        self.mEndTimeComboBox.setCurrentIndex(self.mEndTimeComboBox.count() - 1)

    def useAllTimesFromLayer(self):
        index = self.mDatasetsListWidget.currentIndex()
        if not index.isValid(): return
        group = index.data(Qt.UserRole)
        times = [self.mLayer.datasetMetadata(QgsMeshDatasetIndex(group, dataset)).time()
                 for dataset in range(self.mLayer.datasetCount(QgsMeshDatasetIndex(group, 0)))]
        if times:
            self.mStartTimeComboBox.setCurrentIndex(self.mStartTimeComboBox.findData(min(times)))
            self.mEndTimeComboBox.setCurrentIndex(self.mEndTimeComboBox.findData(max(times)))

    def toggleExtendMask(self, *args):
        self.maskBox.setVisible(self.useMaskCb.isChecked())
        self.extendBox.setVisible(not self.useMaskCb.isChecked())
        self.updateInfoMessage()

    def onVirtualCheckboxChange(self, *args):
        for widget in (self.mOutputDatasetFileWidget, self.mOutputDatasetFileLabel, self.mOutputFormatComboBox, self.mOutputFormatLabel):
            widget.setVisible(not self.mUseVirtualProviderCheckBox.isChecked())
        self.updateInfoMessage()

    def onOutputFormatChange(self, *args):
        suffix = self.currentOutputSuffix()
        self.mOutputDatasetFileWidget.setFilter(self.mOutputFormatComboBox.currentText() + ' (*.' + suffix + ')' if suffix else 'All files (*)')
        path = self.outputFile()
        if path: self.mOutputDatasetFileWidget.setFilePath(path)
        self.updateInfoMessage()

    def expressionState(self):
        # PyQGIS returns the C++ reference output as the second tuple member.
        return QgsMeshCalculator.expressionIsValid(self.formulaString(), self.mLayer)

    def updateInfoMessage(self, *args):
        result, capability = self.expressionState()
        error = ''
        if result != QgsMeshCalculator.Success: error = '表达式无效'
        elif not self.groupName() or self.groupName() in self.mVariableNames: error = '结果组名称为空或已存在'
        elif self.startTime() > self.endTime(): error = '开始时间不能晚于结束时间'
        elif self.useMaskCb.isChecked() and not self.cboLayerMask.currentLayer(): error = '请选择多边形掩膜图层'
        elif not self.useMaskCb.isChecked() and (self.mXMinSpinBox.value() >= self.mXMaxSpinBox.value() or self.mYMinSpinBox.value() >= self.mYMaxSpinBox.value()): error = '输出范围无效'
        elif not self.mUseVirtualProviderCheckBox.isChecked():
            driver = self.mMeshDrivers.get(self.driver())
            if not driver or not driver.capabilities() & capability: error = '所选格式不支持结果的数据位置（面或顶点）'
            elif not self.outputFile() or not Path(self.outputFile()).parent.is_dir(): error = '输出路径无效'
        self.mExpressionValidLabel.setText(error or '表达式有效')
        self.mButtonBox.button(QDialogButtonBox.Ok).setEnabled(not error)

    def maskGeometry(self):
        layer = self.cboLayerMask.currentLayer()
        if not layer: raise ValueError('请选择掩膜图层')
        transform = QgsCoordinateTransform(layer.crs(), self.mLayer.crs(), QgsProject.instance())
        geometries = []
        for feature in layer.getFeatures():
            geometry = feature.geometry()
            if geometry.isEmpty(): continue
            geometry.transform(transform)
            geometries.append(geometry)
        mask = QgsGeometry.unaryUnion(geometries)
        if mask.isEmpty() or mask.isNull(): raise ValueError('掩膜没有可用的多边形')
        return mask

    def calculator(self):
        mask = self.maskGeometry() if self.useMaskCb.isChecked() else self.outputExtent()
        if self.mUseVirtualProviderCheckBox.isChecked():
            return QgsMeshCalculator(self.formulaString(), self.groupName(), mask, QgsMeshDatasetGroup.Virtual, self.mLayer, self.startTime(), self.endTime())
        return QgsMeshCalculator(self.formulaString(), self.driver(), self.groupName(), self.outputFile(), mask, self.startTime(), self.endTime(), self.mLayer)

    def calculate(self, feedback=None):
        self.updateInfoMessage()
        if not self.mButtonBox.button(QDialogButtonBox.Ok).isEnabled(): raise ValueError(self.mExpressionValidLabel.text())
        # Native spatial filtering dereferences the triangular mesh. A freshly
        # loaded/hidden layer may never have been rendered; build it explicitly.
        self.mLayer.updateTriangularMesh()
        result = self.calculator().processCalculation(feedback)
        if result == QgsMeshCalculator.Success:
            QgsProject.instance().setDirty(True)
            self.mLayer.triggerRepaint()
            self.mModel.syncToLayer(self.mLayer)
            self.mVariableNames = self.mModel.variableNames()
            if not self.mUseVirtualProviderCheckBox.isChecked(): QgsSettings().setValue('MeshCalculator/lastOutputDir', str(Path(self.outputFile()).parent))
        return result

    def accept(self):
        self.updateInfoMessage()
        if not self.mButtonBox.button(QDialogButtonBox.Ok).isEnabled(): return
        if not self.mUseVirtualProviderCheckBox.isChecked() and Path(self.outputFile()).exists():
            QMessageBox.warning(self, '输出文件已存在', '请选择新文件名，以免覆盖网格已经引用的数据集。')
            return
        progress = QProgressDialog('正在计算网格表达式…', '取消', 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        feedback = QgsFeedback()
        progress.canceled.connect(feedback.cancel)
        feedback.progressChanged.connect(lambda value: (progress.setValue(int(value)), QgsApplication.processEvents()))
        progress.show()
        try:
            result = self.calculate(feedback)
            if result == QgsMeshCalculator.Canceled: return
            if result != QgsMeshCalculator.Success:
                errors = {QgsMeshCalculator.CreateOutputError: '无法创建输出', QgsMeshCalculator.InputLayerError: '输入图层无效',
                          QgsMeshCalculator.InvalidDatasets: '数据集无效或不兼容', QgsMeshCalculator.ParserError: '表达式解析失败',
                          QgsMeshCalculator.EvaluateError: '表达式计算失败', QgsMeshCalculator.MemoryError: '内存不足'}
                raise RuntimeError(errors.get(result, str(result)))
        except Exception as error:
            QMessageBox.warning(self, '网格计算失败', str(error))
            return
        finally:
            progress.close()
        super().accept()
