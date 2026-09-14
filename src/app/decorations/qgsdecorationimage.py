"""SVG/raster decoration, with native image caches and original project keys."""
import base64
import binascii
from urllib.parse import unquote_to_bytes
from qgis.PyQt.QtCore import QRectF, QSize, QFileInfo, QFile, QIODevice, QUrl, QByteArray, pyqtSignal
from qgis.PyQt.QtGui import QImage
from qgis.PyQt.QtNetwork import QNetworkReply
from qgis.PyQt.QtSvg import QSvgRenderer
from qgis.core import QgsApplication, QgsSymbolLayerUtils, QgsNetworkContentFetcher
from .qgsdecorationitem import QgsDecorationItem


class QgsDecorationImage(QgsDecorationItem):
    configurationName = 'Image'
    defaultPlacement = QgsDecorationItem.BottomLeft
    FormatUnknown, FormatSVG, FormatRaster = range(3)
    imageChanged = pyqtSignal()

    def __init__(self, app):
        self.mFetcher = None
        self.mImagePath = None
        self.mResolvedImagePath = ''
        self.mImageData = b''
        self.mImageError = ''
        self.mLoading = False
        super().__init__(app)

    def projectRead(self):
        super().projectRead()
        self.mColor = QgsSymbolLayerUtils.decodeColor(self.read('Color', '#000000'))
        self.mOutlineColor = QgsSymbolLayerUtils.decodeColor(self.read('OutlineColor', '#FFFFFF'))
        self.mSize = self.read('Size', 16.0)
        self.setImagePath(self.read('ImagePath', ''), force=True)

    def saveToProject(self):
        super().saveToProject()
        self.write('Color', QgsSymbolLayerUtils.encodeColor(self.mColor))
        self.write('OutlineColor', QgsSymbolLayerUtils.encodeColor(self.mOutlineColor))
        self.write('Size', self.mSize)
        path = self.mImagePath
        self.write('ImagePath', path if self.isExternalPath(path) else self.mApp.mProject.pathResolver().writePath(path))

    @staticmethod
    def isExternalPath(path):
        return path.lower().startswith(('http://', 'https://', 'base64:', 'data:'))

    def setImagePath(self, path, force=False):
        path = path.strip()
        if not force and path == self.mImagePath: return
        self.shutdown()
        self.mImagePath = path
        self.mImageData, self.mImageError = b'', ''
        self.mResolvedImagePath = ''
        self.mImageFormat = self.FormatUnknown
        if path.lower().startswith(('http://', 'https://')):
            self.mLoading = True
            self.mFetcher = QgsNetworkContentFetcher()
            self.mFetcher.setParent(self)
            self.mFetcher.finished.connect(self.imageFetched)
            self.mFetcher.fetchContent(QUrl(path))
            return
        if path.lower().startswith(('base64:', 'data:')):
            try:
                if path.lower().startswith('base64:'):
                    data = base64.b64decode(''.join(path[7:].split()), validate=True)
                else:
                    header, encoded = path.split(',', 1)
                    data = base64.b64decode(unquote_to_bytes(encoded), validate=True) if ';base64' in header.lower() else unquote_to_bytes(encoded)
                self.setImageData(data)
            except (ValueError, binascii.Error): self.mImageError = '内嵌图片数据无法解码'
            return
        resolved = QgsSymbolLayerUtils.svgSymbolNameToPath(path, self.mApp.mProject.pathResolver()) if path else ''
        if path and QFileInfo(resolved).exists():
            self.mResolvedImagePath = resolved
            self.mImageFormat = self.FormatSVG if resolved.lower().endswith('.svg') else self.FormatRaster
        elif path: self.mImageError = '找不到图片文件'

    def setImageData(self, data):
        self.mImageData = bytes(data)
        if b'<svg' in self.mImageData.lower() and QSvgRenderer(QByteArray(data)).isValid():
            self.mImageFormat = self.FormatSVG
        elif not QImage.fromData(QByteArray(data)).isNull():
            self.mImageFormat = self.FormatRaster
        else:
            self.mImageFormat = self.FormatUnknown
            self.mImageError = '内容不是有效的 SVG 或栅格图片'
            return
        self.mResolvedImagePath = 'base64:' + base64.b64encode(data).decode('ascii')

    def imageFetched(self):
        fetcher = self.mFetcher
        if fetcher is None: return
        self.mFetcher = None
        self.mLoading = False
        reply = fetcher.reply()
        if reply is not None and reply.error() == QNetworkReply.NoError:
            self.setImageData(bytes(reply.readAll()))
        else:
            self.mImageError = reply.errorString() if reply is not None else '图片下载失败'
        fetcher.deleteLater()
        self.imageChanged.emit()

    def embeddedImagePath(self):
        if self.mImageData:
            return 'base64:' + base64.b64encode(self.mImageData).decode('ascii')
        file = QFile(self.renderPath())
        if not file.open(QIODevice.ReadOnly): return ''
        try: return 'base64:' + bytes(file.readAll().toBase64()).decode('ascii')
        finally: file.close()

    def shutdown(self):
        fetcher, self.mFetcher = self.mFetcher, None
        self.mLoading = False
        if fetcher is not None:
            fetcher.cancel()
            fetcher.deleteLater()

    def imagePath(self):
        if self.isExternalPath(self.mImagePath): return self.mImagePath
        return self.mResolvedImagePath

    def renderPath(self): return self.mResolvedImagePath

    def graphic(self, size):
        path = self.renderPath()
        if self.mImageFormat == self.FormatSVG:
            svg = QSvgRenderer(QgsApplication.svgCache().svgContent(path, size, self.mColor, self.mOutlineColor, 1., 1.))
            return svg, svg.viewBoxF().size() if svg.isValid() else None
        if self.mImageFormat == self.FormatRaster:
            original = QgsApplication.imageCache().originalSize(path)
            if original.isValid():
                dimensions = original.scaled(QSize(max(1, round(size)), max(1, round(size))), 1)
                image, _ = QgsApplication.imageCache().pathAsImage(path, dimensions, True, 1.)
                return image, original
        return None, None

    def render(self, mapSettings, context):
        if not self.mEnabled: return
        length = self.mSize * mapSettings.outputDpi() / 25.4
        graphic, dimensions = self.graphic(length)
        if dimensions is None or dimensions.isEmpty(): return
        scale = length / max(dimensions.width(), dimensions.height())
        width, height = dimensions.width() * scale, dimensions.height() * scale
        x, y = self.origin(context, width, height, image=True)
        painter = context.painter()
        painter.save()
        try:
            painter.translate(x, y)
            rect = QRectF(0, 0, width, height)
            if isinstance(graphic, QSvgRenderer): graphic.render(painter, rect)
            else: painter.drawImage(rect, graphic)
        finally: painter.restore()

    def createDialog(self):
        from .qgsdecorationimagedialog import QgsDecorationImageDialog
        return QgsDecorationImageDialog(self, self.mApp)

    def run(self):
        dialog = self.createDialog()
        try: return dialog.exec_()
        finally: dialog.deleteLater()
