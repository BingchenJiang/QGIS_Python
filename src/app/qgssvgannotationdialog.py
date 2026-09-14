"""QgsSvgAnnotationDialog, corresponding to the original SVG dialog controller."""
from .qgsformannotationdialog import QgsFormAnnotationDialog


class QgsSvgAnnotationDialog(QgsFormAnnotationDialog):
    title = 'SVG 注记'
    fileFilter = 'SVG (*.svg)'
    def sourceFile(self, annotation): return annotation.filePath()
    def applySource(self, annotation): annotation.setFilePath(self.mFileLineEdit.text())
