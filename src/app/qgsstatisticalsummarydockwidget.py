"""QGIS statistical summary dock and background value gatherer counterparts."""
from pathlib import Path
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QTimer, QVariant, QDate, QDateTime, QTime
from qgis.PyQt.QtWidgets import QApplication, QTableWidgetItem, QMenu, QAction
from qgis.core import (
    Qgis, QgsApplication, QgsProject, QgsTask, QgsVectorLayer,
    QgsVectorLayerFeatureSource, QgsFeatureRequest, QgsExpression,
    QgsExpressionContextUtils, QgsStatisticalSummary,
    QgsStringStatisticalSummary, QgsDateTimeStatisticalSummary, QgsVariantUtils,
)
from qgis.gui import QgsDockWidget


STATISTICS = {
    'numeric': (QgsStatisticalSummary, 'Count CountMissing Sum Mean Median StDev StDevSample Min Max Range Minority Majority Variety FirstQuartile ThirdQuartile InterQuartileRange First Last'.split()),
    'string': (QgsStringStatisticalSummary, 'Count CountDistinct CountMissing Min Max MinimumLength MaximumLength MeanLength Minority Majority'.split()),
    'datetime': (QgsDateTimeStatisticalSummary, 'Count CountDistinct CountMissing Min Max Range'.split()),
}


class QgsStatisticsValueGatherer(QgsTask):
    def __init__(self, layer, expression, selectedOnly, canvas):
        super().__init__('获取统计值', QgsTask.CanCancel)
        # Snapshot on the GUI thread: run() never accesses layer or widgets.
        self.mSource = QgsVectorLayerFeatureSource(layer)
        self.mContext = layer.createExpressionContext()
        self.mContext.appendScope(QgsExpressionContextUtils.mapSettingsScope(canvas.mapSettings()))
        self.mExpression = QgsExpression(expression)
        self.mFieldIndex = layer.fields().lookupField(expression)
        self.mKind = None
        if self.mFieldIndex >= 0:
            fieldType = layer.fields()[self.mFieldIndex].type()
            self.mKind = ('string' if fieldType == QVariant.String else
                          'datetime' if fieldType in (QVariant.Date, QVariant.DateTime, QVariant.Time) else 'numeric')
        self.mRequest = QgsFeatureRequest()
        if selectedOnly: self.mRequest.setFilterFids(layer.selectedFeatureIds())
        self.mCount = layer.selectedFeatureCount() if selectedOnly else layer.featureCount()
        self.mRows, self.mError = [], ''

    def run(self):
        try:
            if self.mFieldIndex < 0 and not self.mExpression.prepare(self.mContext):
                raise ValueError(self.mExpression.parserErrorString() or self.mExpression.evalErrorString())
            summary, missing = None, 0
            for index, feature in enumerate(self.mSource.getFeatures(self.mRequest)):
                if self.isCanceled(): return False
                if self.mFieldIndex >= 0: value = feature[self.mFieldIndex]
                else:
                    self.mContext.setFeature(feature)
                    value = self.mExpression.evaluate(self.mContext)
                    if self.mExpression.hasEvalError(): raise ValueError(self.mExpression.evalErrorString())
                if summary is None:
                    if self.mKind is None:
                        if QgsVariantUtils.isNull(value):
                            missing += 1
                            continue
                        self.mKind = ('string' if isinstance(value, str) else
                                      'datetime' if isinstance(value, (QDate, QDateTime, QTime)) else 'numeric')
                    summary = STATISTICS[self.mKind][0]()
                    add = summary.addVariant if self.mKind == 'numeric' else summary.addValue
                    for _ in range(missing): add(None)
                add(value)
                if index % 500 == 0: self.setProgress(100 * index / max(1, self.mCount))
            if summary is None:
                self.mKind = self.mKind or 'numeric'
                summary = STATISTICS[self.mKind][0]()
                add = summary.addVariant if self.mKind == 'numeric' else summary.addValue
                for _ in range(missing): add(None)
            summary.finalize()
            cls, names = STATISTICS[self.mKind]
            self.mRows = [(name, cls.displayName(getattr(cls, name)), summary.statistic(getattr(cls, name))) for name in names]
            self.setProgress(100)
            return True
        except Exception as error:
            self.mError = str(error)
            return False


class QgsStatisticalSummaryDockWidget(QgsDockWidget):
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        uic.loadUi(str(Path(__file__).resolve().parents[1] / 'ui/qgsstatisticalsummarybase.ui'), self)
        self.setObjectName('StatisticalSummary')
        self.setWindowTitle('统计摘要')
        self.mContents.setMinimumHeight(280)
        self.mStatisticsTable.horizontalHeader().setStretchLastSection(True)
        self.mCanvas, self.mLayer, self.mGatherer = canvas, None, None
        self.mGeneration, self.mTasks, self.mLastExpression = 0, set(), {}
        self.mRows, self.mHiddenStats = [], set()
        self.mTimer = QTimer(self)
        self.mTimer.setSingleShot(True)
        self.mTimer.setInterval(180)
        self.mTimer.timeout.connect(self.refreshStatistics)
        self.mLayerComboBox.setFilters(Qgis.LayerFilter.VectorLayer)
        self.mLayerComboBox.layerChanged.connect(self.layerChanged)
        self.mFieldExpressionWidget.fieldChanged.connect(self.scheduleRefresh)
        self.mSelectedOnlyCheckBox.toggled.connect(self.scheduleRefresh)
        self.mButtonRefresh.clicked.connect(self.refreshStatistics)
        self.mButtonCopy.clicked.connect(self.copyStatistics)
        self.mCancelButton.clicked.connect(self.cancel)
        self.mCalculatingProgressBar.hide()
        self.mCancelButton.hide()
        self.mStatisticsMenu = QMenu(self)
        self.mOptionsToolButton.setMenu(self.mStatisticsMenu)
        self.mSyncAction = QAction('跟随当前图层', self)
        self.mSyncAction.setCheckable(True)
        self.mSyncAction.setChecked(True)
        self.mSyncAction.toggled.connect(lambda checked: self.setLayer(canvas.currentLayer()) if checked else None)
        QgsProject.instance().layersWillBeRemoved.connect(self.layersRemoved)
        self.visibilityChanged.connect(lambda visible: self.scheduleRefresh() if visible else None)
        self.layerChanged(self.mLayerComboBox.currentLayer())

    def setLayer(self, layer):
        if self.mSyncAction.isChecked():
            self.mLayerComboBox.setLayer(layer if isinstance(layer, QgsVectorLayer) else None)

    def layerChanged(self, layer):
        if self.mLayer:
            self.mLastExpression[self.mLayer.id()] = self.currentField()
            for signal in (self.mLayer.selectionChanged, self.mLayer.attributeValueChanged, self.mLayer.featureAdded, self.mLayer.featureDeleted, self.mLayer.geometryChanged):
                signal.disconnect(self.scheduleRefresh)
        self.cancel()
        self.mLayer = layer if isinstance(layer, QgsVectorLayer) else None
        self.mFieldExpressionWidget.setLayer(self.mLayer)
        if self.mLayer:
            for signal in (self.mLayer.selectionChanged, self.mLayer.attributeValueChanged, self.mLayer.featureAdded, self.mLayer.featureDeleted, self.mLayer.geometryChanged):
                signal.connect(self.scheduleRefresh)
            fields = self.mLayer.fields()
            expression = self.mLastExpression.get(self.mLayer.id(), fields[0].name() if len(fields) else '')
            self.mFieldExpressionWidget.setField(expression)
        self.scheduleRefresh()

    def currentField(self):
        # SIP returns (field, isExpression, isValid), unlike the C++ QString.
        value = self.mFieldExpressionWidget.currentField()
        return value[0] if isinstance(value, tuple) else value

    def scheduleRefresh(self, *args):
        # Invalidate old results immediately, including while waiting for debounce.
        self.cancel()
        if self.isVisible(): self.mTimer.start()

    def cancel(self):
        self.mGeneration += 1
        self.mTimer.stop()
        if self.mGatherer:
            self.mGatherer.cancel()
            self.mGatherer = None
        self.mCalculatingProgressBar.hide()
        self.mCancelButton.hide()

    def refreshStatistics(self):
        self.cancel()
        self.mStatisticsTable.setRowCount(0)
        self.mRows = []
        expression = self.currentField()
        if not self.mLayer or not expression: return
        generation = self.mGeneration
        task = QgsStatisticsValueGatherer(self.mLayer, expression, self.mSelectedOnlyCheckBox.isChecked(), self.mCanvas)
        self.mGatherer = task
        self.mTasks.add(task)
        self.mCalculatingProgressBar.setValue(0)
        self.mCalculatingProgressBar.show()
        self.mCancelButton.show()
        task.progressChanged.connect(lambda value: self.mCalculatingProgressBar.setValue(int(value)) if generation == self.mGeneration else None)
        task.taskCompleted.connect(lambda: self.gathererFinished(task, generation))
        task.taskTerminated.connect(lambda: self.gathererFinished(task, generation))
        QgsApplication.taskManager().addTask(task)

    def gathererFinished(self, task, generation):
        self.mTasks.discard(task)
        if generation != self.mGeneration: return
        self.mGatherer = None
        self.mCalculatingProgressBar.hide()
        self.mCancelButton.hide()
        if task.mError:
            self.mRows = [('error', '错误', task.mError)]
        else: self.mRows = task.mRows
        self.mStatisticsMenu.clear()
        self.mStatisticsMenu.addAction(self.mSyncAction)
        self.mStatisticsMenu.addSeparator()
        for name, label, _ in self.mRows:
            action = self.mStatisticsMenu.addAction(label)
            action.setCheckable(True)
            action.setChecked(name not in self.mHiddenStats)
            action.toggled.connect(lambda checked, key=name: self.statActionTriggered(key, checked))
        self.displayRows()

    def statActionTriggered(self, name, checked):
        if checked: self.mHiddenStats.discard(name)
        else: self.mHiddenStats.add(name)
        self.displayRows()

    @staticmethod
    def formatValue(value):
        if QgsVariantUtils.isNull(value): return 'NULL'
        if isinstance(value, (QDate, QDateTime, QTime)): return value.toString(Qt.ISODate)
        if hasattr(value, 'seconds'): return f'{value.seconds():g} 秒'
        return format(value, '.12g') if isinstance(value, float) else str(value)

    def displayRows(self):
        rows = [row for row in self.mRows if row[0] not in self.mHiddenStats]
        self.mStatisticsTable.setRowCount(len(rows))
        self.mStatisticsTable.setColumnCount(2)
        self.mStatisticsTable.setHorizontalHeaderLabels(['统计量', '值'])
        for row, (_, label, value) in enumerate(rows):
            for column, text in enumerate((label, self.formatValue(value))):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.mStatisticsTable.setItem(row, column, item)

    def copyStatistics(self):
        QApplication.clipboard().setText('\n'.join(f'{label}\t{self.formatValue(value)}' for name, label, value in self.mRows if name not in self.mHiddenStats))

    def layersRemoved(self, ids):
        if self.mLayer and self.mLayer.id() in ids: self.layerChanged(None)

    def shutdown(self):
        self.cancel()
        for task in list(self.mTasks):
            task.cancel()
            task.waitForFinished()
        # Deliver queued task signals while the dock still exists.
        QgsApplication.processEvents()
