"""Canvas grid decoration, rendered with the native map-grid engine."""
from math import floor, log10, isfinite
from qgis.PyQt import sip
from qgis.core import (Qgis, QgsLineSymbol, QgsMarkerSymbol, QgsPrintLayout,
                       QgsLayoutItemMap, QgsLayoutItemMapGrid, QgsLayoutSize,
                       QgsRectangle, QgsRasterLayer)
from .qgsdecorationitem import QgsDecorationItem


class QgsDecorationGrid(QgsDecorationItem):
    configurationName = 'Grid'
    Line, Marker = range(2)
    Horizontal, Vertical, HorizontalAndVertical, BoundaryDirection = range(4)

    def __init__(self, app):
        self.mLayout = self.mMap = self.mGrid = None
        super().__init__(app)
        app.mMapCanvas.destinationCrsChanged.connect(self.checkMapUnitsChanged)

    def projectRead(self):
        super().projectRead()
        self.mMapUnits = self.read('MapUnits', int(Qgis.DistanceUnit.Unknown))
        self.mGridStyle = self.read('Style', self.Line)
        for field, default in [('IntervalX', 10.), ('IntervalY', 10.), ('OffsetX', 0.), ('OffsetY', 0.)]:
            setattr(self, 'mGrid' + field, self.read(field, default))
        self.mShowGridAnnotation = self.read('ShowAnnotation', False)
        self.mGridAnnotationDirection = self.read('AnnotationDirection', self.Horizontal)
        self.mAnnotationFrameDistance = self.read('AnnotationFrameDistance', 0.)
        self.mGridAnnotationPrecision = self.read('AnnotationPrecision', 0)
        self.mTextFormat = self.readTextFormat()
        self.mLineSymbol = self.readSymbol('LineSymbol', QgsLineSymbol.createSimple({}))
        self.mMarkerSymbol = self.readSymbol('MarkerSymbol', QgsMarkerSymbol.createSimple({'name': 'cross', 'size': '3'}))

    def saveToProject(self):
        super().saveToProject()
        for key, value in [('MapUnits', int(self.mMapUnits)), ('Style', self.mGridStyle),
                           ('ShowAnnotation', self.mShowGridAnnotation), ('AnnotationDirection', self.mGridAnnotationDirection),
                           ('AnnotationFrameDistance', self.mAnnotationFrameDistance), ('AnnotationPrecision', self.mGridAnnotationPrecision)]:
            self.write(key, value)
        for key in ('IntervalX', 'IntervalY', 'OffsetX', 'OffsetY'): self.write(key, float(getattr(self, 'mGrid' + key)))
        self.writeTextFormat(self.mTextFormat)
        self.writeSymbol('LineSymbol', self.mLineSymbol)
        self.writeSymbol('MarkerSymbol', self.mMarkerSymbol)

    def isDirty(self):
        return (self.mMapUnits != int(self.mApp.mMapCanvas.mapSettings().mapUnits()) or
                self.mGridIntervalX <= 0 or self.mGridIntervalY <= 0)

    def setDirty(self, dirty):
        self.mMapUnits = int(Qgis.DistanceUnit.Unknown if dirty else self.mApp.mMapCanvas.mapSettings().mapUnits())

    def checkMapUnitsChanged(self):
        if self.enabled() and self.mMapUnits != int(self.mApp.mMapCanvas.mapSettings().mapUnits()):
            self.setEnabled(False)
            self.setDirty(True)
            if not self.mApp.mMapCanvas.isFrozen(): self.update()

    def getIntervalFromExtent(self, useXAxis=True):
        extent = self.mApp.mMapCanvas.extent()
        interval = (extent.width() if useXAxis else extent.height()) / 5
        if not isfinite(interval) or interval <= 0: return None
        factor = 10 ** floor(log10(interval))
        interval = floor(interval / factor + .5) * factor
        return interval, interval, 0., 0.

    def getIntervalFromCurrentLayer(self):
        layer = self.mApp.mMapCanvas.currentLayer()
        if not isinstance(layer, QgsRasterLayer) or not layer.isValid() or not layer.width() or not layer.height():
            raise ValueError('请选择有效的栅格图层。')
        if layer.crs() != self.mApp.mMapCanvas.mapSettings().destinationCrs():
            raise ValueError('栅格图层与地图画布的坐标参考系必须相同。')
        extent = layer.extent()
        x, y = abs(extent.width()) / layer.width(), abs(extent.height()) / layer.height()
        if x <= 0 or y <= 0: raise ValueError('栅格像元尺寸无效。')
        return x, y, extent.xMinimum() % x, extent.yMinimum() % y

    def createDialog(self):
        from .qgsdecorationgriddialog import QgsDecorationGridDialog
        return QgsDecorationGridDialog(self, self.mApp)

    def run(self):
        dialog = self.createDialog()
        try: return dialog.exec_()
        finally: dialog.deleteLater()

    def render(self, mapSettings, context):
        if not self.enabled() or self.mGridIntervalX <= 0 or self.mGridIntervalY <= 0: return
        if self.mLayout is None:
            self.mLayout = QgsPrintLayout(self.mApp.mProject)
            self.mMap = QgsLayoutItemMap(self.mLayout)
            self.mLayout.addLayoutItem(self.mMap)
            self.mGrid = QgsLayoutItemMapGrid('Canvas Grid', self.mMap)
            self.mMap.grids().addGrid(self.mGrid)
        width, height = self.deviceSize(context)
        dpi = mapSettings.outputDpi()
        if width <= 0 or height <= 0 or dpi <= 0: return
        self.mLayout.renderContext().setDpi(dpi)
        self.mMap.attemptResize(QgsLayoutSize(width * 25.4 / dpi, height * 25.4 / dpi))
        self.mMap.setCrs(mapSettings.destinationCrs())
        center = mapSettings.visibleExtent().center()
        halfWidth = mapSettings.mapUnitsPerPixel() * mapSettings.outputSize().width() / 2
        halfHeight = mapSettings.mapUnitsPerPixel() * mapSettings.outputSize().height() / 2
        self.mMap.setExtent(QgsRectangle(center.x() - halfWidth, center.y() - halfHeight, center.x() + halfWidth, center.y() + halfHeight))
        self.mMap.setMapRotation(mapSettings.rotation())
        grid = self.mGrid
        grid.setEnabled(True)
        grid.setStyle(grid.Solid if self.mGridStyle == self.Line else grid.Markers)
        grid.setIntervalX(self.mGridIntervalX)
        grid.setIntervalY(self.mGridIntervalY)
        grid.setOffsetX(self.mGridOffsetX)
        grid.setOffsetY(self.mGridOffsetY)
        grid.setLineSymbol(self.mLineSymbol.clone())
        grid.setMarkerSymbol(self.mMarkerSymbol.clone())
        grid.setFrameStyle(grid.NoFrame)
        grid.setAnnotationEnabled(self.mShowGridAnnotation)
        grid.setAnnotationFormat(grid.Decimal)
        grid.setAnnotationPrecision(self.mGridAnnotationPrecision)
        grid.setAnnotationTextFormat(self.mTextFormat)
        grid.setAnnotationFrameDistance(self.mAnnotationFrameDistance)
        for side in (grid.Left, grid.Right, grid.Top, grid.Bottom):
            grid.setAnnotationPosition(grid.InsideMapFrame, side)
            direction = grid.Horizontal
            if self.mGridAnnotationDirection == self.Vertical: direction = grid.Vertical
            elif self.mGridAnnotationDirection == self.BoundaryDirection: direction = grid.BoundaryDirection
            elif self.mGridAnnotationDirection == self.HorizontalAndVertical:
                direction = grid.Horizontal if side in (grid.Left, grid.Right) else grid.Vertical
            grid.setAnnotationDirection(direction, side)
        painter = context.painter()
        painter.save()
        try:
            painter.scale(dpi / 25.4, dpi / 25.4)
            grid.draw(painter)
        finally: painter.restore()

    def shutdown(self):
        self.mApp.mMapCanvas.destinationCrsChanged.disconnect(self.checkMapUnitsChanged)
        if self.mLayout is not None: sip.delete(self.mLayout)
        self.mLayout = self.mMap = self.mGrid = None
