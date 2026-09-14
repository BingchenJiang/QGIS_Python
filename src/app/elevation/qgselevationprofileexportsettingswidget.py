"""Original profile axis/range export form and its C++ signal glue."""
from pathlib import Path
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWidget

UI_ROOT = Path(__file__).resolve().parents[2] / 'ui'


class QgsElevationProfileExportSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(str(UI_ROOT / 'qgselevationprofileexportsettingswidgetbase.ui'), self)

    def setPlotSettings(self, plot):
        values = {'MinDistance': plot.xMinimum(), 'MaxDistance': plot.xMaximum(),
                  'MinElevation': plot.yMinimum(), 'MaxElevation': plot.yMaximum()}
        for suffix, axis in [('X', plot.xAxis()), ('Y', plot.yAxis())]:
            values.update({'LabelInterval' + suffix: axis.labelInterval(),
                           'MinorInterval' + suffix: axis.gridIntervalMinor(),
                           'MajorInterval' + suffix: axis.gridIntervalMajor()})
        for name, value in values.items():
            spin = getattr(self, 'mSpin' + name)
            spin.setValue(value)
            spin.setClearValue(value)
            spin.setShowClearButton(True)

    def validationError(self):
        if self.mSpinMinDistance.value() >= self.mSpinMaxDistance.value(): return '最大距离必须大于最小距离'
        if self.mSpinMinElevation.value() >= self.mSpinMaxElevation.value(): return '最高高程必须大于最低高程'
        return ''

    def updatePlotSettings(self, plot):
        plot.setXMinimum(self.mSpinMinDistance.value())
        plot.setXMaximum(self.mSpinMaxDistance.value())
        plot.setYMinimum(self.mSpinMinElevation.value())
        plot.setYMaximum(self.mSpinMaxElevation.value())
        for suffix, axis in [('X', plot.xAxis()), ('Y', plot.yAxis())]:
            axis.setLabelInterval(getattr(self, 'mSpinLabelInterval' + suffix).value())
            axis.setGridIntervalMinor(getattr(self, 'mSpinMinorInterval' + suffix).value())
            axis.setGridIntervalMajor(getattr(self, 'mSpinMajorInterval' + suffix).value())
