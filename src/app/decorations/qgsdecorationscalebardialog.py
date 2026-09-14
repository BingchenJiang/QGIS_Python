"""Original scale bar Designer form and its application-side connections."""
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog
from qgis.core import QgsTextFormat, QgsUnitTypes
from qgis.gui import QgsGui, QgsFontButton
from .qgsdecorationtitledialog import QgsDecorationTitleDialog, UI_ROOT


class QgsDecorationScaleBarDialog(QgsDecorationTitleDialog):
    uiName = 'qgsdecorationscalebardialog.ui'
    helpAnchor = 'scalebar-decoration'

    def __init__(self, decoration, parent):
        QDialog.__init__(self, parent)
        self.mDeco = decoration
        uic.loadUi(str(UI_ROOT / self.uiName), self)
        QgsGui.enableAutoGeometryRestore(self)
        self.initPlacement()
        self.spnSize.setShowClearButton(False)
        self.spnSize.setSuffix(' ' + QgsUnitTypes.toAbbreviatedString(parent.mProject.distanceUnits()))
        self.spnSize.setValue(decoration.mPreferredSize)
        self.chkSnapping.setChecked(decoration.mSnapping)
        self.cboStyle.clear()
        self.cboStyle.addItems(decoration.mStyleLabels)
        self.cboStyle.setCurrentIndex(decoration.mStyleIndex)
        for button, color, title in ((self.pbnChangeColor, decoration.mColor, '比例尺填充颜色'),
                                     (self.pbnChangeOutlineColor, decoration.mOutlineColor, '比例尺轮廓颜色')):
            button.setAllowOpacity(True)
            button.setColor(color)
            button.setContext('gui')
            button.setColorDialogTitle(title)
        self.mButtonFontStyle.setMode(QgsFontButton.ModeTextRenderer)
        self.mButtonFontStyle.setMapCanvas(parent.mMapCanvas)
        self.mButtonFontStyle.setTextFormat(decoration.mTextFormat)
        self.connectButtons()

    def apply(self):
        self.applyPlacement()
        self.mDeco.mPreferredSize = self.spnSize.value()
        self.mDeco.mSnapping = self.chkSnapping.isChecked()
        self.mDeco.mStyleIndex = self.cboStyle.currentIndex()
        self.mDeco.mColor = self.pbnChangeColor.color()
        self.mDeco.mOutlineColor = self.pbnChangeOutlineColor.color()
        self.mDeco.mTextFormat = QgsTextFormat(self.mButtonFontStyle.textFormat())
        self.mDeco.setupScaleBar()
        self.mDeco.update()
        return True
