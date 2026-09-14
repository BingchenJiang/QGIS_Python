"""Title label: native text renderer, expression context and project XML."""
from qgis.PyQt.QtCore import QPointF, QRectF, Qt
from qgis.PyQt.QtXml import QDomDocument
from qgis.core import Qgis, QgsTextFormat, QgsTextRenderer, QgsExpression, QgsReadWriteContext, QgsSymbolLayerUtils
from .qgsdecorationitem import QgsDecorationItem


class QgsDecorationTitle(QgsDecorationItem):
    configurationName = 'TitleLabel'
    defaultPlacement = QgsDecorationItem.TopCenter
    hasBackground = True

    def projectRead(self):
        super().projectRead()
        self.mLabelText = self.read('Label', '')
        self.mBackgroundColor = QgsSymbolLayerUtils.decodeColor(self.read('BackgroundColor', '0,0,0,99'))
        self.mTextFormat = QgsTextFormat()
        xml = self.read('Font', '')
        if xml:
            doc = QDomDocument()
            if doc.setContent(xml)[0]: self.mTextFormat.readXml(doc.documentElement(), self.readWriteContext())
        oldColor = QgsSymbolLayerUtils.decodeColor(self.read('Color', ''))
        if oldColor.isValid(): self.mTextFormat.setColor(oldColor)

    def readWriteContext(self):
        context = QgsReadWriteContext()
        context.setPathResolver(self.mApp.mProject.pathResolver())
        return context

    def saveToProject(self):
        super().saveToProject()
        self.write('Label', self.mLabelText)
        doc = QDomDocument()
        doc.appendChild(self.mTextFormat.writeXml(doc, self.readWriteContext()))
        self.write('Font', doc.toString())
        self.mApp.mProject.removeEntry(self.mConfigurationName, '/Color')
        if self.hasBackground: self.write('BackgroundColor', QgsSymbolLayerUtils.encodeColor(self.mBackgroundColor))

    def createDialog(self):
        from .qgsdecorationtitledialog import QgsDecorationTitleDialog
        return QgsDecorationTitleDialog(self, self.mApp)

    def run(self):
        dialog = self.createDialog()
        try: return dialog.exec_()
        finally: dialog.deleteLater()

    def render(self, mapSettings, context):
        if not self.mEnabled: return
        text = QgsExpression.replaceExpressionText(self.mLabelText, context.expressionContext())
        lines = text.split('\n')
        width = QgsTextRenderer.textWidth(context, self.mTextFormat, lines)
        height = QgsTextRenderer.textHeight(context, self.mTextFormat, lines, Qgis.TextLayoutMode.Point)
        descent = QgsTextRenderer.fontMetrics(context, self.mTextFormat).descent()
        x, y = self.origin(context, width, height)
        painter = context.painter()
        painter.save()
        try:
            if self.hasBackground:
                dw, dh = self.deviceSize(context)
                _, my = self.margins(context, width, height)
                bandHeight = height + 2 * my
                top = self.mPlacement in (self.TopLeft, self.TopCenter, self.TopRight)
                painter.setPen(Qt.NoPen)
                painter.setBrush(self.mBackgroundColor)
                painter.drawRect(QRectF(0, 0 if top else dh - bandHeight, dw, bandHeight))
            alignment = Qgis.TextHorizontalAlignment.Left
            if self.mPlacement in (self.TopCenter, self.BottomCenter):
                x += width / 2
                alignment = Qgis.TextHorizontalAlignment.Center
            elif self.mPlacement in (self.TopRight, self.BottomRight):
                x += width
                alignment = Qgis.TextHorizontalAlignment.Right
            QgsTextRenderer.drawText(QPointF(x, y + height - descent), 0, alignment, lines, context, self.mTextFormat)
        finally: painter.restore()
