from qgis.PyQt.QtCore import Qt

from qgis.core import QgsPointXY, QgsRectangle, QgsApplication
from qgis.PyQt.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QToolButton, QLabel, QSizePolicy

class QgsStatusBarCoordinatesWidget(QWidget):
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.mMapCanvas = canvas
        box = QHBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)
        self.mLastCoordinate = None
        self.mLabel = QLabel('坐标', self)
        self.mLabel.setObjectName('mCoordsLabel')
        self.mLabel.setMargin(3)
        self.mLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)  # 新增
        self.mToggleExtentsViewButton = QToolButton()
        self.mToggleExtentsViewButton.setCheckable(True)
        self.mToggleExtentsViewButton.setIcon(QgsApplication.getThemeIcon('/tracking.svg'))
        self.mToggleExtentsViewButton.setAutoRaise(True)
        self.mToggleExtentsViewButton.setToolTip('切换坐标/范围；输入坐标后按回车定位')
        self.mLineEdit = QLineEdit()
        self.mLineEdit.setAlignment(Qt.AlignCenter)
        self.mLineEdit.setMinimumWidth(155)
        self.mLineEdit.setMaximumWidth(230)
        box.addWidget(self.mLabel)
        box.addWidget(self.mLineEdit)
        box.addWidget(self.mToggleExtentsViewButton)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)  # 新增
        self.mToggleExtentsViewButton.toggled.connect(self.extentsViewToggled)
        canvas.extentsChanged.connect(self.showExtent)
        canvas.xyCoordinates.connect(self.showCoordinates)
        self.mLineEdit.returnPressed.connect(self.validateCoordinates)

    def showCoordinates(self, point):
        self.mLastCoordinate = point
        if not self.mToggleExtentsViewButton.isChecked() and not self.mLineEdit.hasFocus():
            self.mLineEdit.setText(f'{point.x():.5f}, {point.y():.5f}')
    def showExtent(self, *args):
        if self.mToggleExtentsViewButton.isChecked():
            extent = self.mMapCanvas.extent()
            self.mLineEdit.setText(', '.join(f'{n:.4f}' for n in [extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()]))
    def extentsViewToggled(self, checked):
        self.mLabel.setText('范围' if checked else '坐标')
        self.mToggleExtentsViewButton.setIcon(QgsApplication.getThemeIcon('/extents.svg' if checked else '/tracking.svg'))
        self.mLineEdit.setReadOnly(checked)
        if checked: self.showExtent()
        elif self.mLastCoordinate is not None: self.showCoordinates(self.mLastCoordinate)
        else: self.mLineEdit.clear()

    def validateCoordinates(self):
        if self.mLineEdit.isReadOnly(): return
        try:
            values = [float(v) for v in self.mLineEdit.text().replace(',', ' ').split()]
            if len(values) == 2: self.mMapCanvas.setCenter(QgsPointXY(*values))
            elif len(values) == 4: self.mMapCanvas.setExtent(QgsRectangle(*values))
            else: return
            self.mMapCanvas.refresh()
        except ValueError: self.mLineEdit.setToolTip('请输入 x,y 或 xmin,ymin,xmax,ymax')
