from qgis.gui import QgsSvgSelectorDialog
from .qgsdecorationimagedialog import QgsDecorationImageDialog


class QgsDecorationNorthArrowDialog(QgsDecorationImageDialog):
    uiName = 'qgsdecorationnortharrowdialog.ui'
    helpAnchor = 'northarrow-decoration'

    def initPath(self):
        self.mSvgPathLineEdit.setText(self.mDeco.mSvgPath)
        self.spinAngle.setValue(int(self.mDeco.mRotationInt) % 360)
        self.sliderRotation.setValue(self.spinAngle.value())
        self.cboxAutomatic.setChecked(self.mDeco.mAutomatic)
        self.spinAngle.valueChanged.connect(self.sliderRotation.setValue)
        self.sliderRotation.valueChanged.connect(self.spinAngle.setValue)
        self.spinAngle.valueChanged.connect(self.drawImage)
        self.mSvgPathLineEdit.textChanged.connect(self.drawImage)
        self.mSvgSelectorBtn.clicked.connect(self.selectSvg)
        self.cboxAutomatic.toggled.connect(self.automaticChanged)
        self.automaticChanged(self.mDeco.mAutomatic)

    def automaticChanged(self, enabled):
        self.spinAngle.setEnabled(not enabled)
        self.sliderRotation.setEnabled(not enabled)
        self.drawImage()

    def selectSvg(self):
        dialog = QgsSvgSelectorDialog(self)
        dialog.svgSelector().setSvgPath(self.mPreview.svgPath())
        if dialog.exec_(): self.mSvgPathLineEdit.setText(dialog.svgSelector().currentSvgPath())
        dialog.deleteLater()

    def copyGraphicSettings(self, target):
        target.mSize = self.spinSize.value()
        target.mColor = self.pbnChangeColor.color()
        target.mOutlineColor = self.pbnChangeOutlineColor.color()
        target.mSvgPath = self.mSvgPathLineEdit.text().strip()
        target.mRotationInt = self.spinAngle.value()
        target.mAutomatic = self.cboxAutomatic.isChecked()

    def previewPath(self): return self.mPreview.svgPath()
