from pathlib import Path
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
from qgis.core import Qgis
from qgis.gui import QgsGui, QgsHelp


class QgsDecorationLayoutExtentDialog(QDialog):
    def __init__(self, deco, parent=None):
        super().__init__(parent)
        self.mDeco = deco
        uic.loadUi(str(Path(__file__).resolve().parents[2] / 'ui/qgsdecorationlayoutextentdialog.ui'), self)
        QgsGui.enableAutoGeometryRestore(self)
        self.grpEnable.setChecked(deco.enabled())
        self.mCheckBoxLabelExtents.setChecked(deco.labelExtents())
        self.mSymbolButton.setSymbolType(Qgis.SymbolType.Fill)
        self.mSymbolButton.setSymbol(deco.symbol().clone())
        self.mSymbolButton.setMapCanvas(deco.mApp.mMapCanvas)
        self.mSymbolButton.setMessageBar(deco.mApp.mMessageBar)
        self.mButtonFontStyle.setMapCanvas(deco.mApp.mMapCanvas)
        self.mButtonFontStyle.setTextFormat(deco.mTextFormat)
        self.mButtonFontStyle.setEnabled(deco.labelExtents())
        self.mCheckBoxLabelExtents.toggled.connect(self.mButtonFontStyle.setEnabled)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.apply)
        self.buttonBox.helpRequested.connect(lambda: QgsHelp.openHelp('map_views/map_view.html#layoutextents-decoration'))

    def apply(self):
        self.mDeco.setEnabled(self.grpEnable.isChecked())
        self.mDeco.setSymbol(self.mSymbolButton.symbol().clone())
        self.mDeco.setLabelExtents(self.mCheckBoxLabelExtents.isChecked())
        self.mDeco.mTextFormat = self.mButtonFontStyle.textFormat()
        self.mDeco.update()

    def accept(self):
        self.apply()
        super().accept()
