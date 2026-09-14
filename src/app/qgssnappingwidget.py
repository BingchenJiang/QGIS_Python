"""Port of dynamically-created QgsSnappingWidget; synchronized with QgsProject."""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QToolButton, QComboBox, QDoubleSpinBox, QCheckBox, QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QDialogButtonBox, QAction, QMenu, QWidgetAction, QLabel
from qgis.core import Qgis, QgsApplication, QgsSnappingConfig, QgsVectorLayer


class QgsSnappingWidget(QWidget):
    def __init__(self, project, canvas, parent=None):
        super().__init__(parent)
        self.mProject, self.mCanvas = project, canvas
        self.setObjectName('QgsSnappingWidget')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.mEnabledAction = self.button(layout, '启用捕捉', '/mIconSnapping.svg', True)
        self.mModeButton = QComboBox()
        for text, value in [('当前图层', Qgis.SnappingMode.ActiveLayer), ('所有图层', Qgis.SnappingMode.AllLayers), ('高级配置', Qgis.SnappingMode.AdvancedConfiguration)]:
            self.mModeButton.addItem(text, value)
        layout.addWidget(self.mModeButton)
        self.mTypeButton = QComboBox()
        for text, value in [('顶点', Qgis.SnappingType.Vertex), ('线段', Qgis.SnappingType.Segment), ('顶点和线段', Qgis.SnappingType.Vertex | Qgis.SnappingType.Segment)]:
            self.mTypeButton.addItem(text, value)
        layout.addWidget(self.mTypeButton)
        self.mToleranceSpinBox = QDoubleSpinBox()
        self.mToleranceSpinBox.setRange(0, 1e8)
        self.mToleranceSpinBox.setMaximumWidth(100)
        layout.addWidget(self.mToleranceSpinBox)
        self.mUnitsComboBox = QComboBox()
        for text, value in [('像素', Qgis.MapToolUnit.Pixels), ('地图单位', Qgis.MapToolUnit.Project), ('图层单位', Qgis.MapToolUnit.Layer)]:
            self.mUnitsComboBox.addItem(text, value)
        layout.addWidget(self.mUnitsComboBox)
        self.mTopologicalEditingAction = self.button(layout, '拓扑编辑', '/mIconTopologicalEditing.svg', True)
        self.mIntersectionSnappingAction = self.button(layout, '交点捕捉', '/mIconSnappingIntersection.svg', True)
        self.mSelfSnappingAction = self.button(layout, '自身捕捉', '/mIconSnappingSelf.svg', True)
        self.mEnableTracingAction = self.button(layout, '启用追踪', '/mActionTracing.svg', True)
        self.mEnableTracingAction.setShortcut('T')
        self.addAction(self.mEnableTracingAction)
        self.mTracingOffsetSpinBox = QDoubleSpinBox()
        self.mTracingOffsetSpinBox.setRange(-1e6, 1e6)
        self.mTracingOffsetSpinBox.setDecimals(6)
        menu = QMenu(self)
        container = QWidget()
        offsetLayout = QVBoxLayout(container)
        offsetLayout.addWidget(QLabel('追踪偏移（地图单位）'))
        offsetLayout.addWidget(self.mTracingOffsetSpinBox)
        widgetAction = QWidgetAction(menu)
        widgetAction.setDefaultWidget(container)
        menu.addAction(widgetAction)
        self.mEnableTracingAction.setMenu(menu)
        from qgis.gui import QgsMapCanvasTracer
        self.mTracer = QgsMapCanvasTracer(canvas)
        self.mTracer.setActionEnableSnapping(self.mEnabledAction)
        self.mTracer.setActionEnableTracing(self.mEnableTracingAction)
        self.mTracingOffsetSpinBox.valueChanged.connect(self.mTracer.setOffset)
        advanced = self.button(layout, '逐图层设置', '/mActionOptions.svg')
        advanced.clicked.connect(self.editAdvancedConfig)
        for widget in [self.mEnabledAction, self.mTopologicalEditingAction, self.mIntersectionSnappingAction, self.mSelfSnappingAction]: widget.toggled.connect(self.saveConfig)
        for widget in [self.mModeButton, self.mTypeButton, self.mUnitsComboBox]: widget.currentIndexChanged.connect(self.saveConfig)
        self.mToleranceSpinBox.valueChanged.connect(self.saveConfig)
        project.snappingConfigChanged.connect(self.projectSnapSettingsChanged)
        project.topologicalEditingChanged.connect(self.projectSnapSettingsChanged)
        self.projectSnapSettingsChanged()

    def button(self, layout, text, icon, checkable=False):
        button = QToolButton(self)
        button.setText(text)
        button.setToolTip(text)
        button.setIcon(QgsApplication.getThemeIcon(icon))
        button.setCheckable(checkable)
        layout.addWidget(button)
        if checkable:
            action = QAction(button.icon(), text, self)
            action.setCheckable(True)
            button.setDefaultAction(action)
            button.setPopupMode(QToolButton.MenuButtonPopup)
            return action
        return button
    def config(self): return self.mProject.snappingConfig()
    def setConfig(self, config): self.mProject.setSnappingConfig(config)
    def enableSnappingAction(self): return self.mEnabledAction

    @staticmethod
    def selectData(combo, value):
        # Qgis.SnappingTypes is a SIP flag wrapper; QVariant.findData does not
        # reliably compare its value to the individual enum members.
        for index in range(combo.count()):
            if int(combo.itemData(index)) == int(value):
                combo.setCurrentIndex(index)
                return
        combo.addItem(QgsSnappingConfig.snappingTypesToString(value) if hasattr(QgsSnappingConfig, 'snappingTypesToString') else '自定义类型', value)
        combo.setCurrentIndex(combo.count() - 1)

    def projectSnapSettingsChanged(self, *args):
        config = self.config()
        widgets = [self.mEnabledAction, self.mModeButton, self.mTypeButton, self.mToleranceSpinBox,
                   self.mUnitsComboBox, self.mTopologicalEditingAction, self.mIntersectionSnappingAction, self.mSelfSnappingAction]
        for widget in widgets: widget.blockSignals(True)
        self.mEnabledAction.setChecked(config.enabled())
        self.selectData(self.mModeButton, config.mode())
        self.selectData(self.mTypeButton, config.typeFlag())
        self.mToleranceSpinBox.setValue(config.tolerance())
        self.selectData(self.mUnitsComboBox, config.units())
        self.mTopologicalEditingAction.setChecked(self.mProject.topologicalEditing())
        self.mIntersectionSnappingAction.setChecked(config.intersectionSnapping())
        self.mSelfSnappingAction.setChecked(config.selfSnapping())
        for widget in widgets: widget.blockSignals(False)

    def saveConfig(self, *args):
        config = self.config()
        config.setEnabled(self.mEnabledAction.isChecked())
        config.setMode(self.mModeButton.currentData())
        config.setTypeFlag(self.mTypeButton.currentData())
        config.setTolerance(self.mToleranceSpinBox.value())
        config.setUnits(self.mUnitsComboBox.currentData())
        config.setIntersectionSnapping(self.mIntersectionSnappingAction.isChecked())
        config.setSelfSnapping(self.mSelfSnappingAction.isChecked())
        self.mProject.setSnappingConfig(config)
        self.mProject.setTopologicalEditing(self.mTopologicalEditingAction.isChecked())

    def editAdvancedConfig(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('逐图层捕捉配置')
        dialog.resize(650, 450)
        layout = QVBoxLayout(dialog)
        layers = [l for l in self.mProject.mapLayers().values() if isinstance(l, QgsVectorLayer)]
        table = QTableWidget(len(layers), 7)
        table.setHorizontalHeaderLabels(['图层', '启用', '类型', '容差', '单位', '最小比例尺', '最大比例尺'])
        editors = []
        for row, layer in enumerate(layers):
            config = self.config().individualLayerSettings(layer)
            table.setItem(row, 0, QTableWidgetItem(layer.name()))
            enabled = QCheckBox()
            enabled.setChecked(config.enabled())
            kind = QComboBox()
            for i in range(self.mTypeButton.count()): kind.addItem(self.mTypeButton.itemText(i), self.mTypeButton.itemData(i))
            self.selectData(kind, config.typeFlag())
            tolerance = QDoubleSpinBox()
            tolerance.setRange(0, 1e6)
            tolerance.setValue(config.tolerance() if config.valid() else 12)
            units = QComboBox()
            for i in range(self.mUnitsComboBox.count()): units.addItem(self.mUnitsComboBox.itemText(i), self.mUnitsComboBox.itemData(i))
            units.setCurrentIndex(max(0, units.findData(config.units())))
            scales = []
            for value in (config.minimumScale(), config.maximumScale()):
                spin = QDoubleSpinBox()
                spin.setRange(0, 1e12)
                spin.setValue(value)
                scales.append(spin)
            for col, widget in enumerate([enabled, kind, tolerance, units] + scales, 1): table.setCellWidget(row, col, widget)
            editors.append((layer, enabled, kind, tolerance, units, *scales))
        layout.addWidget(table)
        scaleMode = QComboBox()
        for text, mode in [('不限制捕捉比例尺', QgsSnappingConfig.Disabled), ('逐图层比例尺', QgsSnappingConfig.PerLayer)]: scaleMode.addItem(text, mode)
        if self.config().scaleDependencyMode() == QgsSnappingConfig.PerLayer: scaleMode.setCurrentIndex(1)
        # Preserve an existing global mode unless the user explicitly changes it.
        originalMode = self.config().scaleDependencyMode()
        scaleMode.activated.connect(lambda _: setattr(dialog, 'scaleModeChanged', True))
        layout.addWidget(scaleMode)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec_():
            config = self.config()
            config.setMode(Qgis.SnappingMode.AdvancedConfiguration)
            config.setScaleDependencyMode(scaleMode.currentData() if getattr(dialog, 'scaleModeChanged', False) else originalMode)
            for layer, enabled, kind, tolerance, units, minimum, maximum in editors:
                config.setIndividualLayerSettings(layer, QgsSnappingConfig.IndividualLayerSettings(enabled.isChecked(), kind.currentData(), tolerance.value(), units.currentData(), minimum.value(), maximum.value()))
            self.mProject.setSnappingConfig(config)
