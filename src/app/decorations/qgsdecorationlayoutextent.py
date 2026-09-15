"""Draw the visible map extents from open layout designers on the canvas."""
from math import radians
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QEvent, QTimer, Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import (Qgis, QgsLayout, QgsLayoutItemMap, QgsFillSymbol,
                       QgsSimpleLineSymbolLayer, QgsGeometry,
                       QgsCoordinateTransform, QgsCsException, QgsTextRenderer)
from .qgsdecorationitem import QgsDecorationItem


class QgsDecorationLayoutExtent(QgsDecorationItem):
    configurationName = 'LayoutExtent'
    defaultPlacement = QgsDecorationItem.BottomRight

    def __init__(self, app):
        self.mWatchedLayouts = []
        self.mWatchedMaps = []
        super().__init__(app)

    def projectRead(self):
        super().projectRead()
        symbol = QgsFillSymbol()
        symbol.changeSymbolLayer(0, QgsSimpleLineSymbolLayer(QColor(0, 0, 0, 100), 0, Qt.DashLine))
        self.mSymbol = self.readSymbol('Symbol', symbol)
        self.mTextFormat = self.readTextFormat()
        self.mLabelExtents = self.read('Labels', True)

    def saveToProject(self):
        super().saveToProject()
        self.writeSymbol('Symbol', self.mSymbol)
        self.writeTextFormat(self.mTextFormat)
        self.write('Labels', self.mLabelExtents)

    def symbol(self): return self.mSymbol
    def setSymbol(self, symbol): self.mSymbol = symbol
    def labelExtents(self): return self.mLabelExtents
    def setLabelExtents(self, enabled): self.mLabelExtents = enabled

    def watchDesigner(self, designer):
        layout = getattr(designer, 'mLayout', None)
        if not isinstance(layout, QgsLayout): return
        designer.installEventFilter(self)
        self.mWatchedLayouts = [item for item in self.mWatchedLayouts if not sip.isdeleted(item)]
        if layout not in self.mWatchedLayouts:
            layout.changed.connect(self.layoutChanged)
            layout.itemAdded.connect(self.watchMap)
            self.mWatchedLayouts.append(layout)
        for item in layout.items(): self.watchMap(item)

    def watchMap(self, item):
        if not isinstance(item, QgsLayoutItemMap): return
        self.mWatchedMaps = [entry for entry in self.mWatchedMaps if not sip.isdeleted(entry)]
        if item in self.mWatchedMaps: return
        for signal in (item.extentChanged, item.mapRotationChanged, item.crsChanged, item.changed):
            signal.connect(self.layoutChanged)
        self.mWatchedMaps.append(item)
        self.layoutChanged()

    def layoutChanged(self, *args):
        if self.enabled(): self.mApp.refreshDecorationOverlays()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Show, QEvent.Hide, QEvent.Close):
            # Hide/close is delivered before the widget visibility changes.
            QTimer.singleShot(0, self.layoutChanged)
        return super().eventFilter(watched, event)

    def createDialog(self):
        from .qgsdecorationlayoutextentdialog import QgsDecorationLayoutExtentDialog
        return QgsDecorationLayoutExtentDialog(self, self.mApp)

    def run(self):
        dialog = self.createDialog()
        try: return dialog.exec_()
        finally: dialog.deleteLater()

    def render(self, mapSettings, context):
        if not self.enabled() or self.mSymbol is None: return
        painter = context.painter()
        painter.save()
        self.mSymbol.startRender(context)
        try:
            transform = mapSettings.mapToPixel().transform()
            for designer in self.mApp.mLayoutDesigners:
                if sip.isdeleted(designer) or not designer.isVisible(): continue
                layout = getattr(designer, 'mLayout', None)
                if not isinstance(layout, QgsLayout) or sip.isdeleted(layout): continue
                name = layout.name() if hasattr(layout, 'name') else designer.windowTitle()
                for item in layout.items():
                    if not isinstance(item, QgsLayoutItemMap): continue
                    extent = item.visibleExtentPolygon()
                    if len(extent) < 3: continue
                    labelPoint = extent[1]
                    geometry = QgsGeometry.fromQPolygonF(extent)
                    if item.crs() != mapSettings.destinationCrs():
                        ct = QgsCoordinateTransform(item.crs(), mapSettings.destinationCrs(), self.mApp.mProject)
                        geometry = geometry.densifyByCount(20)
                        try:
                            geometry.transform(ct)
                            labelPoint = ct.transform(labelPoint.x(), labelPoint.y()).toQPointF()
                        except QgsCsException:
                            continue
                    geometry.transform(transform)
                    self.mSymbol.renderPolygon(geometry.asQPolygonF(), [], None, context)
                    if self.mLabelExtents:
                        QgsTextRenderer.drawText(transform.map(labelPoint), radians(item.mapRotation() - mapSettings.rotation()),
                                                 Qgis.TextHorizontalAlignment.Right,
                                                 [f'{name}: {item.displayName()}'], context, self.mTextFormat)
        finally:
            self.mSymbol.stopRender(context)
            painter.restore()

    def shutdown(self):
        for layout in self.mWatchedLayouts:
            if not sip.isdeleted(layout):
                layout.changed.disconnect(self.layoutChanged)
                layout.itemAdded.disconnect(self.watchMap)
        for item in self.mWatchedMaps:
            if not sip.isdeleted(item):
                for signal in (item.extentChanged, item.mapRotationChanged, item.crsChanged, item.changed):
                    signal.disconnect(self.layoutChanged)
        self.mWatchedLayouts.clear()
        self.mWatchedMaps.clear()
