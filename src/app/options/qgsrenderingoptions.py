"""Counterpart of options/qgsrenderingoptions.cpp, using its original form."""
from pathlib import Path
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QThread
from qgis.core import QgsApplication, QgsSettings
from qgis.gui import QgsOptionsPageWidget


class QgsRenderingOptionsWidget(QgsOptionsPageWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(str(Path(__file__).resolve().parents[2] / 'ui/qgsrenderingoptionsbase.ui'), self)
        self.setObjectName('mOptionsPageRendering')
        settings = QgsSettings()
        self.chkAddedVisibility.setChecked(settings.value('qgis/new_layers_visible', True, type=bool))
        self.chkAntiAliasing.setChecked(settings.value('qgis/enable_anti_aliasing', True, type=bool))
        self.spinMaxThreads.setRange(1, max(1, QThread.idealThreadCount()))
        self.spinMaxThreads.setClearValue(1, f'全部可用线程 ({QThread.idealThreadCount()})')
        self.spinMaxThreads.setValue(max(1, QgsApplication.maxThreads()))
        self.spinMapUpdateInterval.setValue(settings.value('qgis/map_update_interval', 250, type=int))
        self.spinMapUpdateInterval.setClearValue(250)
        self.doubleSpinBoxMagnifierDefault.setRange(10, 1600)
        self.doubleSpinBoxMagnifierDefault.setSingleStep(50)
        self.doubleSpinBoxMagnifierDefault.setSuffix('%')
        self.doubleSpinBoxMagnifierDefault.setClearValue(100)
        self.doubleSpinBoxMagnifierDefault.setValue(100 * settings.value('qgis/magnifier_factor_default', 1.0, type=float))

    def apply(self):
        settings = QgsSettings()
        threads = -1 if self.spinMaxThreads.value() == 1 else self.spinMaxThreads.value()
        QgsApplication.setMaxThreads(threads)
        for key, value in [('new_layers_visible', self.chkAddedVisibility.isChecked()), ('enable_anti_aliasing', self.chkAntiAliasing.isChecked()), ('max_threads', threads), ('map_update_interval', self.spinMapUpdateInterval.value()), ('magnifier_factor_default', self.doubleSpinBoxMagnifierDefault.value() / 100)]:
            settings.setValue('qgis/' + key, value)
