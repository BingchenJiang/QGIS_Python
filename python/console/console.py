"""Original console contents with a Python implementation of its dock host."""
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout
from qgis.core import QgsApplication, QgsSettings
from console.console import PythonConsoleWidget
from src.gui.qgsdockablewidgethelper import QgsDockableWidgetHelper


class PythonConsole(QWidget):
    visibilityChanged = pyqtSignal(bool)

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName('PythonConsole')
        self.mDockableWidgetHelper = QgsDockableWidgetHelper(
            QgsSettings().value('PythonConsoleWindow/docked', True, type=bool),
            'Python 控制台', self, parent, windowGeometrySettingsKey='PythonConsoleWindow')
        self.mDockToggleButton = self.mDockableWidgetHelper.createDockUndockToolButton()
        self.console = PythonConsoleWidget(self)
        from qgis.gui import QgsGui
        QgsGui.instance().optionsChanged.connect(self.console.updateSettings)
        import console.console as upstream
        upstream._console = self
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.console)
        self.mDockableWidgetHelper.visibilityChanged.connect(self.visibilityChanged)
        self.visibilityChanged.connect(parent.mActionShowPythonDialog.setChecked)
        QgsApplication.instance().aboutToQuit.connect(self.console.saveSettingsConsole)

    def dockToggleButton(self): return self.mDockToggleButton
    def isUserVisible(self): return self.mDockableWidgetHelper.isUserVisible()
    def setUserVisible(self, visible): self.mDockableWidgetHelper.setUserVisible(visible)
    def activate(self):
        self.setUserVisible(True)
        self.console.shell.setFocus()
    def hide(self): self.setUserVisible(False)
    def closeEvent(self, event):
        self.console.saveSettingsConsole()
        self.setUserVisible(False)
        event.ignore()
