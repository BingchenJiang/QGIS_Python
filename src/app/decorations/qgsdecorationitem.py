"""Shared project settings and placement of the upstream decoration items."""
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.core import Qgis, QgsUnitTypes


class QgsDecorationItem(QObject):
    BottomLeft, TopLeft, TopRight, BottomRight, TopCenter, BottomCenter = range(6)
    toggled = pyqtSignal(bool)
    configurationName = ''
    defaultPlacement = TopLeft

    def __init__(self, app):
        super().__init__(app)
        self.mApp = app
        self.mConfigurationName = self.configurationName
        self.projectRead()

    def enabled(self): return self.mEnabled
    def setEnabled(self, enabled):
        changed = self.mEnabled != enabled
        self.mEnabled = enabled
        if changed: self.toggled.emit(enabled)
    def placement(self): return self.mPlacement
    def setPlacement(self, placement): self.mPlacement = placement

    def read(self, key, default):
        project = self.mApp.mProject
        reader = project.readBoolEntry if isinstance(default, bool) else project.readNumEntry if isinstance(default, int) else project.readDoubleEntry if isinstance(default, float) else project.readEntry
        return reader(self.mConfigurationName, '/' + key, default)[0]

    def write(self, key, value):
        project = self.mApp.mProject
        writer = project.writeEntryBool if isinstance(value, bool) else project.writeEntryDouble if isinstance(value, float) else project.writeEntry
        writer(self.mConfigurationName, '/' + key, value)

    def readWriteContext(self):
        from qgis.core import QgsReadWriteContext
        context = QgsReadWriteContext()
        context.setPathResolver(self.mApp.mProject.pathResolver())
        return context

    def readSymbol(self, key, fallback):
        from qgis.PyQt.QtXml import QDomDocument
        from qgis.core import QgsSymbolLayerUtils
        document = QDomDocument()
        xml = self.read(key, '')
        if xml and document.setContent(xml)[0]:
            symbol = QgsSymbolLayerUtils.loadSymbol(document.documentElement(), self.readWriteContext())
            if isinstance(symbol, type(fallback)): return symbol
        return fallback

    def writeSymbol(self, key, symbol):
        from qgis.PyQt.QtXml import QDomDocument
        from qgis.core import QgsSymbolLayerUtils
        document = QDomDocument()
        document.appendChild(QgsSymbolLayerUtils.saveSymbol(key, symbol, document, self.readWriteContext()))
        self.write(key, document.toString())

    def readTextFormat(self):
        from qgis.PyQt.QtXml import QDomDocument
        from qgis.core import QgsTextFormat
        result, document = QgsTextFormat(), QDomDocument()
        xml = self.read('Font', '')
        if xml and document.setContent(xml)[0]: result.readXml(document.documentElement(), self.readWriteContext())
        return result

    def writeTextFormat(self, textFormat):
        from qgis.PyQt.QtXml import QDomDocument
        document = QDomDocument()
        document.appendChild(textFormat.writeXml(document, self.readWriteContext()))
        self.write('Font', document.toString())

    def projectRead(self):
        self.mEnabled = self.read('Enabled', False)
        self.mPlacement = self.read('Placement', self.defaultPlacement)
        unit, ok = QgsUnitTypes.decodeRenderUnit(self.read('MarginUnit', 'MM'))
        self.mMarginUnit = unit if ok else Qgis.RenderUnit.Millimeters
        self.mMarginHorizontal = self.read('MarginH', 0)
        self.mMarginVertical = self.read('MarginV', 0)

    def saveToProject(self):
        for key, value in [('Enabled', self.mEnabled), ('Placement', self.mPlacement),
                           ('MarginUnit', QgsUnitTypes.encodeUnit(self.mMarginUnit)),
                           ('MarginH', self.mMarginHorizontal), ('MarginV', self.mMarginVertical)]:
            self.write(key, value)

    def update(self):
        self.saveToProject()
        self.mApp.mProject.setDirty(True)
        self.mApp.mMapCanvas.refresh()
        self.mApp.mDecorationOverlay.update()
        for canvas in self.mApp.mAdditionalCanvases:
            canvas.refresh()
            canvas._decorationOverlay.update()

    def deviceSize(self, context):
        device = context.painter().device()
        return device.width() / context.devicePixelRatio(), device.height() / context.devicePixelRatio()

    def margins(self, context, width, height, image=False):
        device = context.painter().device()
        if self.mMarginUnit == Qgis.RenderUnit.Millimeters:
            return device.logicalDpiX() * self.mMarginHorizontal / 25.4, device.logicalDpiY() * self.mMarginVertical / 25.4
        if self.mMarginUnit == Qgis.RenderUnit.Percentage:
            dw, dh = self.deviceSize(context)
            # The image and north arrow C++ implementations use width here.
            return (dw - width) * self.mMarginHorizontal / 100, (dh - (width if image else height)) * self.mMarginVertical / 100
        return self.mMarginHorizontal - (5 if image else 0), self.mMarginVertical - (5 if image else 0)

    def origin(self, context, width, height, image=False):
        dw, dh = self.deviceSize(context)
        mx, my = self.margins(context, width, height, image)
        if self.mPlacement in (self.TopCenter, self.BottomCenter): x = (dw - width) / 2 + mx
        elif self.mPlacement in (self.TopRight, self.BottomRight): x = dw - width - mx
        else: x = mx
        y = my if self.mPlacement in (self.TopLeft, self.TopCenter, self.TopRight) else dh - height - my
        return x, y
