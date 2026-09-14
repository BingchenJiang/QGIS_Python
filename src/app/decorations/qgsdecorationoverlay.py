"""Viewport overlay matching the fixed-screen decorations in QGIS 3.34."""
from qgis.PyQt.QtCore import Qt, QEvent
from qgis.PyQt.QtGui import QPainter
from qgis.PyQt.QtWidgets import QWidget


class QgsDecorationOverlay(QWidget):
    def __init__(self, canvas, app):
        super().__init__(canvas.viewport())
        self.mCanvas, self.mApp = canvas, app
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        canvas.viewport().installEventFilter(self)
        canvas.renderComplete.connect(lambda *_: self.update())
        canvas.rotationChanged.connect(lambda *_: self.update())
        self.resize(canvas.viewport().size())
        self.show()

    def paintEvent(self, event):
        if self.mApp.mShutdown: return
        painter = QPainter(self)
        try: self.mApp.renderDecorationItems(painter, self.mCanvas, devicePixelRatio=1)
        finally: painter.end()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize: self.resize(self.parentWidget().size())
        return super().eventFilter(obj, event)
