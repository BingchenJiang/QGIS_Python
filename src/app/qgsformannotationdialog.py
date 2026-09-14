"""QgsFormAnnotationDialog; shared original form for Form/SVG/HTML dialogs."""
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QFileDialog
from .qgsannotationwidget import _QgsAnnotationDialog, UI_ROOT


class QgsFormAnnotationDialog(_QgsAnnotationDialog):
    title = '表单注记'
    fileFilter = 'Qt Designer (*.ui)'
    sourceMode = False

    def __init__(self, item, parent=None):
        super().__init__(parent)
        uic.loadUi(str(UI_ROOT / 'qgsformannotationdialogbase.ui'), self)
        self.setWindowTitle(self.title)
        self.setupAnnotationWidget(item)
        self.mFileLineEdit.setText(self.sourceFile(item.annotation()))
        if self.sourceMode:
            self.mHtmlSourceTextEdit.setText(item.annotation().htmlSource())
            self.mFileRadioButton.setChecked(bool(self.mFileLineEdit.text()))
            self.mSourceRadioButton.setChecked(not self.mFileLineEdit.text())
        else:
            self.mFileRadioButton.setChecked(True)
            self.mFileRadioButton.hide()
            self.mSourceRadioButton.hide()
            self.mHtmlSourceTextEdit.hide()
        self.updateSourceControls()
        self.mBrowseToolButton.clicked.connect(self.mBrowseToolButton_clicked)
        self.mFileLineEdit.textChanged.connect(self.onSettingsChanged)
        self.mHtmlSourceTextEdit.textChanged.connect(self.onSettingsChanged)
        self.mFileRadioButton.toggled.connect(self.updateSourceControls)
        self.mSourceRadioButton.toggled.connect(self.onSettingsChanged)
        self.setupLiveUpdate()

    def sourceFile(self, annotation): return annotation.designerForm()
    def applySource(self, annotation): annotation.setDesignerForm(self.mFileLineEdit.text())

    def updateSourceControls(self, *args):
        enabled = self.mFileRadioButton.isChecked()
        self.mFileLineEdit.setEnabled(enabled)
        self.mBrowseToolButton.setEnabled(enabled)
        self.mHtmlSourceTextEdit.setEnabled(not enabled)
        self.onSettingsChanged()

    def mBrowseToolButton_clicked(self):
        path, _ = QFileDialog.getOpenFileName(self, self.title, self.mFileLineEdit.text(), self.fileFilter)
        if path: self.mFileLineEdit.setText(path)

    def applySettingsToItem(self):
        annotation = self.annotation()
        if not annotation: return
        self.mEmbeddedWidget.apply()
        self.applySource(annotation)
        self.mItem.update()
