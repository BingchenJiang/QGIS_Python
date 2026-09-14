"""QgsMapToolAnnotation: native canvas annotation selection, drag, resize and editing."""
from qgis.PyQt import sip
from qgis.PyQt.QtCore import Qt, QPointF, QSizeF
from qgis.core import QgsProject, QgsCoordinateTransform, QgsTextAnnotation, QgsSvgAnnotation, QgsHtmlAnnotation
from qgis.gui import QgsMapTool, QgsMapCanvasAnnotationItem, QgsFormAnnotation


class QgsMapToolAnnotation(QgsMapTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.setCursor(Qt.CrossCursor)
        self.mCurrentMoveAction = QgsMapCanvasAnnotationItem.NoAction
        self.mLastMousePosition = None
        self.mMoveSnapshot = None

    def flags(self): return QgsMapTool.ShowContextMenu

    def itemAtPos(self, pos):
        for item in self.canvas().items(pos):
            if isinstance(item, QgsMapCanvasAnnotationItem) and item.annotation().isVisible() and item.moveActionForPosition(QPointF(pos)) != item.NoAction: return item
        return None

    def selectedItem(self):
        return next((i for i in self.canvas().scene().selectedItems() if isinstance(i, QgsMapCanvasAnnotationItem)), None)

    def canvasPressEvent(self, event):
        if event.button() != Qt.LeftButton: return
        self.mLastMousePosition = event.pos()
        item = self.itemAtPos(event.pos())
        self.canvas().scene().clearSelection()
        if item:
            item.setSelected(True)
            self.mCurrentMoveAction = item.moveActionForPosition(QPointF(event.pos()))
            a = item.annotation()
            self.mMoveSnapshot = (a, a.mapPosition(), a.relativePosition(), a.frameOffsetFromReferencePointMm(), a.frameSizeMm())
            return
        annotation = self.createItem()
        if not annotation: return
        annotation.setMapPositionCrs(self.canvas().mapSettings().destinationCrs())
        annotation.setMapPosition(event.mapPoint())
        annotation.setRelativePosition(QPointF(event.pos().x()/self.canvas().width(), event.pos().y()/self.canvas().height()))
        annotation.setFrameSizeMm(QSizeF(50, 25))
        QgsProject.instance().annotationManager().addAnnotation(annotation)
        for item in self.canvas().annotationItems():
            if item.annotation() == annotation: item.setSelected(True)
        QgsProject.instance().setDirty(True)

    def transformCanvasToAnnotation(self, point, annotation):
        return QgsCoordinateTransform(self.canvas().mapSettings().destinationCrs(), annotation.mapPositionCrs(), QgsProject.instance()).transform(point)

    def canvasMoveEvent(self, event):
        item = self.selectedItem()
        if not item or not event.buttons() & Qt.LeftButton or self.mLastMousePosition is None:
            hover = self.itemAtPos(event.pos())
            self.canvas().setCursor(hover.cursorShapeForAction(hover.moveActionForPosition(QPointF(event.pos()))) if hover else Qt.CrossCursor)
            return
        annotation = item.annotation()
        action = self.mCurrentMoveAction
        kind = QgsMapCanvasAnnotationItem
        dx, dy = event.pos().x()-self.mLastMousePosition.x(), event.pos().y()-self.mLastMousePosition.y()
        mm = 25.4/self.canvas().logicalDpiX()
        if action == kind.MoveMapPosition:
            annotation.setMapPosition(self.transformCanvasToAnnotation(event.snapPoint(), annotation))
            annotation.setRelativePosition(QPointF(event.pos().x()/self.canvas().width(), event.pos().y()/self.canvas().height()))
        elif action == kind.MoveFramePosition:
            if annotation.hasFixedMapPosition():
                annotation.setFrameOffsetFromReferencePointMm(annotation.frameOffsetFromReferencePointMm()+QPointF(dx*mm, dy*mm))
            else:
                canvasPoint = item.pos()+QPointF(dx, dy)
                annotation.setMapPosition(self.transformCanvasToAnnotation(self.toMapCoordinates(canvasPoint.toPoint()), annotation))
            annotation.setRelativePosition(annotation.relativePosition()+QPointF(dx/self.canvas().width(), dy/self.canvas().height()))
        elif action != kind.NoAction:
            offset, size = annotation.frameOffsetFromReferencePointMm(), annotation.frameSizeMm()
            left, top, right, bottom = offset.x(), offset.y(), offset.x()+size.width(), offset.y()+size.height()
            relative = annotation.relativePosition()
            if action in (kind.ResizeFrameLeft, kind.ResizeFrameLeftUp, kind.ResizeFrameLeftDown):
                left += dx*mm
                relative.setX(relative.x()+dx/self.canvas().width())
            if action in (kind.ResizeFrameRight, kind.ResizeFrameRightUp, kind.ResizeFrameRightDown): right += dx*mm
            if action in (kind.ResizeFrameUp, kind.ResizeFrameLeftUp, kind.ResizeFrameRightUp):
                top += dy*mm
                relative.setY(relative.y()+dy/self.canvas().height())
            if action in (kind.ResizeFrameDown, kind.ResizeFrameLeftDown, kind.ResizeFrameRightDown): bottom += dy*mm
            annotation.setFrameOffsetFromReferencePointMm(QPointF(min(left, right), min(top, bottom)))
            annotation.setFrameSizeMm(QSizeF(abs(right-left), abs(bottom-top)))
            annotation.setRelativePosition(relative)
        if action != kind.NoAction: QgsProject.instance().setDirty(True)
        self.mLastMousePosition = event.pos()

    def canvasReleaseEvent(self, event):
        self.mCurrentMoveAction = QgsMapCanvasAnnotationItem.NoAction
        self.mMoveSnapshot = None

    def createItemEditor(self, item):
        from .qgstextannotationdialog import QgsTextAnnotationDialog
        from .qgssvgannotationdialog import QgsSvgAnnotationDialog
        from .qgshtmlannotationdialog import QgsHtmlAnnotationDialog
        from .qgsformannotationdialog import QgsFormAnnotationDialog
        for kind, dialog in [(QgsTextAnnotation, QgsTextAnnotationDialog), (QgsSvgAnnotation, QgsSvgAnnotationDialog),
                             (QgsHtmlAnnotation, QgsHtmlAnnotationDialog), (QgsFormAnnotation, QgsFormAnnotationDialog)]:
            if isinstance(item.annotation(), kind): return dialog(item, self.canvas())
        return None

    def editItem(self, item):
        if not item or sip.isdeleted(item): return
        dialog = self.createItemEditor(item)
        if dialog: dialog.exec_(); dialog.deleteLater()

    def canvasDoubleClickEvent(self, event): self.editItem(self.itemAtPos(event.pos()))

    def populateContextMenuWithEvent(self, menu, event):
        item = self.itemAtPos(event.pos())
        if item:
            menu.addSeparator()
            menu.addAction('编辑注记…', lambda: self.editItem(item))
            menu.addAction('删除注记', lambda: self.deleteItem(item))
        return True

    def deleteItem(self, item):
        if item and not sip.isdeleted(item): QgsProject.instance().annotationManager().removeAnnotation(item.annotation())

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.deleteItem(self.selectedItem())
            event.ignore()
        elif event.key() == Qt.Key_Escape: self.cancel()
        else: super().keyPressEvent(event)

    def cancel(self):
        if self.mMoveSnapshot:
            annotation, point, relative, offset, size = self.mMoveSnapshot
            if not sip.isdeleted(annotation):
                annotation.setMapPosition(point)
                annotation.setRelativePosition(relative)
                annotation.setFrameOffsetFromReferencePointMm(offset)
                annotation.setFrameSizeMm(size)
        self.mMoveSnapshot = None
        self.mCurrentMoveAction = QgsMapCanvasAnnotationItem.NoAction
        self.mLastMousePosition = None

    def deactivate(self): self.cancel(); super().deactivate()
