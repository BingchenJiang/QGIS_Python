"""QgsMapToolRotateLabel: two-click rotation, Ctrl 15°, Delete/reset, Escape."""
import math
from qgis.PyQt.QtCore import Qt
from qgis.core import Qgis, QgsPalLayerSettings, QgsUnitTypes, QgsPointXY, QgsGeometry
from .qgsmaptoollabel import QgsMapToolLabel


class QgsMapToolRotateLabel(QgsMapToolLabel):
    @staticmethod
    def roundTo15Degrees(value): return math.floor(value/15 + .5)*15

    def canvasPressEvent(self, event):
        if self.mCurrentLabel:
            if event.button() == Qt.RightButton: self.cancel(); return
            if event.button() == Qt.LeftButton:
                self.canvasMoveEvent(event)
                self.applyRotation(self.mDisplayRotation)
                self.cancel()
            return
        if event.button() != Qt.LeftButton: return
        pos = self.labelAtPosition(event)
        if not pos or pos.isDiagram: return
        self.mCurrentLabel = self.details(pos)
        if not self.createAuxiliaryFields(self.mCurrentLabel, [QgsPalLayerSettings.LabelRotation]): self.cancel(); return
        self.clearHoveredLabel()
        self.mRotationPoint = self.currentLabelRotationPoint()
        self.mStartMouseAngle = self.mouseAngle(self.toMapCoordinates(event.pos()))
        factor = QgsUnitTypes.fromUnitToUnitFactor(self.mCurrentLabel.settings.rotationUnit(), Qgis.AngleUnit.Degrees)
        self.mStartRotation = float(self.value(self.mCurrentLabel, QgsPalLayerSettings.LabelRotation, 0))*factor
        self.mDisplayRotation = self.mStartRotation
        self.createRubberBands()

    def mouseAngle(self, point):
        return math.degrees(math.atan2(point.y()-self.mRotationPoint.y(), point.x()-self.mRotationPoint.x()))

    def canvasMoveEvent(self, event):
        if not self.mCurrentLabel: self.updateHoveredLabel(event); return
        angle = (self.mStartRotation+self.mStartMouseAngle-self.mouseAngle(self.toMapCoordinates(event.pos()))) % 360
        self.mDisplayRotation = self.roundTo15Degrees(angle) if event.modifiers() & Qt.ControlModifier else angle
        points = [self.rotatePointClockwise(p, self.mRotationPoint, self.mDisplayRotation-self.mStartRotation) for p in self.mCurrentLabel.pos.cornerPoints]
        if points: self.mLabelRubberBand.setToGeometry(QgsGeometry.fromPolygonXY([points+[points[0]]]), None)
        self.canvas().setToolTip('旋转：%.2f°（Ctrl：15°；Delete：清除；Esc：取消）' % self.mDisplayRotation)

    @staticmethod
    def rotatePointClockwise(point, center, degrees):
        angle = math.radians(-degrees)
        x, y = point.x()-center.x(), point.y()-center.y()
        return QgsPointXY(center.x()+x*math.cos(angle)-y*math.sin(angle), center.y()+x*math.sin(angle)+y*math.cos(angle))

    def applyRotation(self, degrees):
        details = self.mCurrentLabel
        if not details: return False
        index = self.dataDefinedColumnIndex(QgsPalLayerSettings.LabelRotation, details)
        factor = QgsUnitTypes.fromUnitToUnitFactor(Qgis.AngleUnit.Degrees, details.settings.rotationUnit())
        return self.writeChanges(details, {index: degrees*factor if degrees is not None else None}, '旋转标注' if degrees is not None else '删除标注旋转覆盖')

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Delete and self.mCurrentLabel:
            self.applyRotation(None)
            self.cancel()
        else: super().keyReleaseEvent(event)

    def cancel(self):
        super().cancel()
        self.canvas().setToolTip('')
