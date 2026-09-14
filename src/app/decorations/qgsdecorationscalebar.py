"""Scale bar decoration using the native QGIS scale bar renderers."""
from math import floor, log10, isfinite
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtXml import QDomDocument
from qgis.core import (Qgis, QgsScaleBarSettings, QgsScaleBarRenderer,
    QgsTicksScaleBarRenderer, QgsSingleBoxScaleBarRenderer, QgsFillSymbol,
    QgsLineSymbol, QgsTextFormat, QgsReadWriteContext, QgsSymbolLayerUtils,
    QgsMapSettings, QgsDistanceArea, QgsPointXY, QgsUnitTypes, QgsFontUtils,
    QgsCsException)
from .qgsdecorationitem import QgsDecorationItem


class QgsDecorationScaleBar(QgsDecorationItem):
    configurationName = 'ScaleBar'
    defaultPlacement = QgsDecorationItem.TopLeft

    def __init__(self, app):
        self.mStyleLabels = ['向下刻度', '向上刻度', '条形', '方框']
        super().__init__(app)

    def readWriteContext(self):
        context = QgsReadWriteContext()
        context.setPathResolver(self.mApp.mProject.pathResolver())
        return context

    def projectRead(self):
        super().projectRead()
        self.mPreferredSize = max(1, self.read('PreferredSize', 30))
        self.mStyleIndex = max(0, min(3, self.read('Style', 0)))
        self.mSnapping = self.read('Snapping', True)
        self.mColor = QgsSymbolLayerUtils.decodeColor(self.read('Color', '#000000'))
        self.mOutlineColor = QgsSymbolLayerUtils.decodeColor(self.read('OutlineColor', '#FFFFFF'))
        self.mTextFormat = QgsTextFormat()
        document = QDomDocument()
        xml = self.read('TextFormat', '')
        if xml and document.setContent(xml)[0]:
            self.mTextFormat.readXml(document.documentElement(), self.readWriteContext())
        elif not xml:
            legacy = self.read('Font', '')
            if legacy and document.setContent(legacy)[0]:
                font = QFont()
                QgsFontUtils.setFromXmlElement(font, document.documentElement())
                self.mTextFormat = QgsTextFormat.fromQFont(font)
                self.mTextFormat.setColor(self.mColor)
        self.setupScaleBar()

    def saveToProject(self):
        super().saveToProject()
        for key, value in [('PreferredSize', self.mPreferredSize), ('Style', self.mStyleIndex),
                           ('Snapping', self.mSnapping), ('Color', QgsSymbolLayerUtils.encodeColor(self.mColor)),
                           ('OutlineColor', QgsSymbolLayerUtils.encodeColor(self.mOutlineColor))]:
            self.write(key, value)
        document = QDomDocument()
        document.appendChild(self.mTextFormat.writeXml(document, self.readWriteContext()))
        self.write('TextFormat', document.toString())

    def setupScaleBar(self):
        self.mSettings = QgsScaleBarSettings()
        self.mSettings.setTextFormat(self.mTextFormat)
        self.mSettings.setNumberOfSegments(1)
        self.mSettings.setNumberOfSegmentsLeft(0)
        self.mSettings.setLabelBarSpace(1.8)
        fill = QgsFillSymbol.createSimple({'color': QgsSymbolLayerUtils.encodeColor(self.mColor), 'outline_style': 'no'})
        self.mSettings.setFillSymbol(fill)
        if self.mStyleIndex in (0, 1):
            self.mStyle = QgsTicksScaleBarRenderer()
            self.mStyle.setTickPosition(QgsTicksScaleBarRenderer.TicksDown if self.mStyleIndex == 0 else QgsTicksScaleBarRenderer.TicksUp)
            self.mSettings.setHeight(2.2)
            line = QgsLineSymbol()
            line.setColor(self.mColor)
            line.setWidth(.3)
            line.setOutputUnit(Qgis.RenderUnit.Millimeters)
            self.mSettings.setDivisionLineSymbol(line.clone())
            self.mSettings.setLineSymbol(line)
        else:
            self.mStyle = QgsSingleBoxScaleBarRenderer()
            self.mSettings.setHeight(1. if self.mStyleIndex == 2 else 3.)
            alternate = QgsFillSymbol.createSimple({'color': '255,255,255,0', 'outline_style': 'no'})
            self.mSettings.setAlternateFillSymbol(alternate)
            line = QgsLineSymbol()
            line.setColor(self.mOutlineColor)
            line.setWidth(.2 if self.mStyleIndex == 2 else .3)
            line.setOutputUnit(Qgis.RenderUnit.Millimeters)
            self.mSettings.setLineSymbol(line)

    def mapWidth(self, settings):
        unrotated = QgsMapSettings(settings)
        unrotated.setRotation(0)
        extent = unrotated.visibleExtent()
        if self.mSettings.units() == Qgis.DistanceUnit.Unknown: return extent.width()
        distance = QgsDistanceArea()
        distance.setSourceCrs(settings.destinationCrs(), settings.transformContext())
        distance.setEllipsoid(self.mApp.mProject.ellipsoid())
        y = (extent.yMinimum() + extent.yMaximum()) / 2
        length = distance.measureLine(QgsPointXY(extent.xMinimum(), y), QgsPointXY(extent.xMaximum(), y))
        return distance.convertLengthMeasurement(length, self.mSettings.units())

    @staticmethod
    def displayDistance(value, unit):
        if unit == Qgis.DistanceUnit.Meters:
            if value > 1000: return value / 1000, 'km'
            if value < .01: return value * 1000, 'mm'
            if value < .1: return value * 100, 'cm'
            return value, 'm'
        if unit == Qgis.DistanceUnit.Feet:
            # Use native conversion factors so the displayed distance remains
            # correct when changing between feet, miles and inches.
            if value >= 5280:
                return value * QgsUnitTypes.fromUnitToUnitFactor(unit, Qgis.DistanceUnit.Miles), 'mi'
            if value < 1:
                return value * QgsUnitTypes.fromUnitToUnitFactor(unit, Qgis.DistanceUnit.Inches), 'in'
            return value, 'ft'
        return value, QgsUnitTypes.toAbbreviatedString(unit)

    def render(self, mapSettings, context):
        if not self.enabled() or not mapSettings.layers(): return
        deviceWidth, _ = self.deviceSize(context)
        if deviceWidth <= 0 or mapSettings.outputSize().width() <= 0: return
        unit = self.mApp.mProject.distanceUnits()
        self.mSettings.setUnits(unit)
        try: unitsPerPixel = self.mapWidth(mapSettings) / mapSettings.outputSize().width()
        except QgsCsException: return
        if not isfinite(unitsPerPixel) or unitsPerPixel <= 0: return
        width = self.mPreferredSize / unitsPerPixel
        if width < 30: width = deviceWidth / 4
        while width > deviceWidth / 3: width /= 3
        unitsPerSegment = width * unitsPerPixel
        if unitsPerSegment <= 0: return
        if self.mSnapping:
            scaler = 10 ** floor(log10(unitsPerSegment))
            unitsPerSegment = floor(unitsPerSegment / scaler + .5) * scaler
            width = unitsPerSegment / unitsPerPixel
        mm = context.convertToPainterUnits(1, Qgis.RenderUnit.Millimeters)
        if mm <= 0: return
        value, label = self.displayDistance(unitsPerSegment, unit)
        segments = 2 if self.mStyleIndex == 3 else 1
        self.mSettings.setNumberOfSegments(segments)
        self.mSettings.setUnitsPerSegment(value / segments)
        self.mSettings.setUnitLabel(label)
        centered = self.mPlacement in (self.TopCenter, self.BottomCenter)
        self.mSettings.setLabelHorizontalPlacement(QgsScaleBarSettings.LabelCenteredSegment if centered else QgsScaleBarSettings.LabelCenteredEdge)
        scaleContext = QgsScaleBarRenderer.ScaleBarContext()
        scaleContext.segmentWidth = width / mm / segments
        scaleContext.scale = mapSettings.scale()
        size = self.mStyle.calculateBoxSize(context, self.mSettings, scaleContext)
        x, y = self.origin(context, size.width() * mm, size.height() * mm)
        painter = context.painter()
        painter.save()
        try:
            painter.translate(x, y)
            self.mStyle.draw(context, self.mSettings, scaleContext)
        finally: painter.restore()

    def margins(self, context, width, height, image=False):
        if self.mMarginUnit == Qgis.RenderUnit.Pixels:
            return self.mMarginHorizontal - 5, self.mMarginVertical - 5
        if self.mMarginUnit == Qgis.RenderUnit.Percentage:
            dw, dh = self.deviceSize(context)
            return (dw - width) * self.mMarginHorizontal / 100, dh * self.mMarginVertical / 100
        return super().margins(context, width, height)

    def createDialog(self):
        from .qgsdecorationscalebardialog import QgsDecorationScaleBarDialog
        return QgsDecorationScaleBarDialog(self, self.mApp)

    def run(self):
        dialog = self.createDialog()
        try: return dialog.exec_()
        finally: dialog.deleteLater()
