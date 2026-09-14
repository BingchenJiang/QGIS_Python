"""QgsTextAnnotationDialog with original UI and rich text formatting."""
from qgis.PyQt import uic
from qgis.PyQt.QtGui import QFont, QTextDocument, QPalette
from .qgsannotationwidget import _QgsAnnotationDialog, UI_ROOT


class QgsTextAnnotationDialog(_QgsAnnotationDialog):
    def __init__(self, item, parent=None):
        super().__init__(parent)
        uic.loadUi(str(UI_ROOT / 'qgstextannotationdialogbase.ui'), self)
        self.setupAnnotationWidget(item)
        document = item.annotation().document()
        self.mTextDocument = document.clone(self) if document else QTextDocument(self)
        self.mTextEdit.setDocument(self.mTextDocument)
        self.mFontColorButton.setAllowOpacity(True)
        self.setCurrentFontPropertiesToGui()
        for signal in [self.mFontComboBox.currentFontChanged, self.mFontSizeSpinBox.valueChanged,
                       self.mBoldPushButton.toggled, self.mItalicsPushButton.toggled, self.mFontColorButton.colorChanged]:
            signal.connect(self.changeCurrentFormat)
        self.mTextEdit.cursorPositionChanged.connect(self.setCurrentFontPropertiesToGui)
        self.mTextEdit.textChanged.connect(self.onSettingsChanged)
        self.mEmbeddedWidget.backgroundColorChanged.connect(self.backgroundColorChanged)
        self.backgroundColorChanged(self.mEmbeddedWidget.backgroundColor())
        self.setupLiveUpdate()

    def backgroundColorChanged(self, color):
        palette = self.mTextEdit.viewport().palette()
        palette.setColor(QPalette.Base, color)
        self.mTextEdit.viewport().setPalette(palette)

    def setCurrentFontPropertiesToGui(self):
        widgets = [self.mFontComboBox, self.mFontSizeSpinBox, self.mBoldPushButton, self.mItalicsPushButton, self.mFontColorButton]
        for widget in widgets: widget.blockSignals(True)
        font = self.mTextEdit.currentFont()
        self.mFontComboBox.setCurrentFont(font)
        self.mFontSizeSpinBox.setValue(max(1, font.pointSize()))
        self.mBoldPushButton.setChecked(font.bold())
        self.mItalicsPushButton.setChecked(font.italic())
        self.mFontColorButton.setColor(self.mTextEdit.textColor())
        for widget in widgets: widget.blockSignals(False)

    def changeCurrentFormat(self, *args):
        font = QFont(self.mFontComboBox.currentFont())
        font.setPointSize(max(1, self.mFontSizeSpinBox.value()))
        font.setBold(self.mBoldPushButton.isChecked())
        font.setItalic(self.mItalicsPushButton.isChecked())
        self.mTextEdit.setCurrentFont(font)
        self.mTextEdit.setTextColor(self.mFontColorButton.color())
        self.onSettingsChanged()

    def applyTextToItem(self):
        annotation = self.annotation()
        if not annotation: return
        self.mEmbeddedWidget.apply()
        annotation.setDocument(self.mTextDocument)
        self.mItem.update()

    def applySettingsToItem(self): self.applyTextToItem()
