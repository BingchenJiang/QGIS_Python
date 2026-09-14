"""QgsHtmlAnnotationDialog: source file or native HTML code editor."""
from .qgsformannotationdialog import QgsFormAnnotationDialog


class QgsHtmlAnnotationDialog(QgsFormAnnotationDialog):
    title = 'HTML 注记'
    fileFilter = 'HTML (*.html *.htm);;所有文件 (*)'
    sourceMode = True
    def sourceFile(self, annotation): return annotation.sourceFile()
    def applySource(self, annotation):
        if self.mFileRadioButton.isChecked(): annotation.setSourceFile(self.mFileLineEdit.text())
        else: annotation.setHtmlSource(self.mHtmlSourceTextEdit.text())
