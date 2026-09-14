"""North arrow rotation and anchoring from qgsdecorationnortharrow.cpp."""
from math import sin, cos, radians
from qgis.PyQt.QtCore import QFileInfo, QRectF
from qgis.PyQt.QtSvg import QSvgRenderer
from qgis.core import QgsApplication, QgsSymbolLayerUtils, QgsBearingUtils, QgsCsException
from .qgsdecorationimage import QgsDecorationImage
from .qgsdecorationitem import QgsDecorationItem


class QgsDecorationNorthArrow(QgsDecorationImage):
    configurationName = 'NorthArrow'

    def projectRead(self):
        super().projectRead()
        self.mSvgPath = self.read('SvgPath', '')
        self.mRotationInt = self.read('Rotation', 0)
        self.mAutomatic = self.read('Automatic', True)

    def saveToProject(self):
        QgsDecorationItem.saveToProject(self)
        self.write('Color', QgsSymbolLayerUtils.encodeColor(self.mColor))
        self.write('OutlineColor', QgsSymbolLayerUtils.encodeColor(self.mOutlineColor))
        self.write('Size', self.mSize)
        self.write('SvgPath', self.mApp.mProject.pathResolver().writePath(self.mSvgPath))
        self.write('Rotation', int(self.mRotationInt))
        self.write('Automatic', self.mAutomatic)

    def svgPath(self):
        if self.mSvgPath.lower().startswith('base64:'): return self.mSvgPath
        if self.mSvgPath:
            path = QgsSymbolLayerUtils.svgSymbolNameToPath(self.mSvgPath, self.mApp.mProject.pathResolver())
            if QFileInfo(path).exists(): return path
        return ':/images/north_arrows/default.svg'

    def graphic(self, size):
        svg = QSvgRenderer(QgsApplication.svgCache().svgContent(self.svgPath(), size, self.mColor, self.mOutlineColor, 1., 1.))
        return svg, svg.viewBoxF().size() if svg.isValid() else None

    def rotation(self, mapSettings):
        if not self.mAutomatic: return self.mRotationInt
        try:
            angle = QgsBearingUtils.bearingTrueNorth(mapSettings.destinationCrs(), mapSettings.transformContext(), mapSettings.extent().center())
        except QgsCsException:
            angle = 0.
        return angle + mapSettings.rotation()

    def render(self, mapSettings, context):
        if not self.mEnabled: return
        length = self.mSize * mapSettings.outputDpi() / 25.4
        svg, dimensions = self.graphic(length)
        if dimensions is None or dimensions.isEmpty(): return
        scale = length / max(dimensions.width(), dimensions.height())
        width, height = int(dimensions.width() * scale), int(dimensions.height() * scale)
        x, y = self.origin(context, width, height, image=True)
        if self.mPlacement in (self.TopRight, self.BottomRight): x -= (length - width) / 2
        if self.mPlacement in (self.BottomLeft, self.BottomRight): y -= (length - height) / 2
        angle = self.rotation(mapSettings)
        a, cx, cy = radians(angle), width / 2, height / 2
        shiftX = int(cx * cos(a) + cy * sin(a) - cx)
        shiftY = int(-cx * sin(a) + cy * cos(a) - cy)
        painter = context.painter()
        painter.save()
        try:
            painter.translate(x, y)
            painter.rotate(angle)
            painter.translate(shiftX, shiftY)
            svg.render(painter, QRectF(0, 0, width, height))
        finally: painter.restore()

    def createDialog(self):
        from .qgsdecorationnortharrowdialog import QgsDecorationNorthArrowDialog
        return QgsDecorationNorthArrowDialog(self, self.mApp)
