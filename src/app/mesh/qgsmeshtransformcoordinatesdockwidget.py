from pathlib import Path
from qgis.PyQt import uic
from qgis.PyQt.QtGui import QColor
from qgis.core import Qgis, QgsMesh, QgsExpressionContext, QgsExpressionContextUtils, QgsExpressionContextGenerator, QgsGeometry, QgsPointXY, QgsMeshTransformVerticesByExpression
from qgis.gui import QgsDockWidget, QgsRubberBand


class _MeshExpressionContextGenerator(QgsExpressionContextGenerator):
    def createExpressionContext(self):
        return QgsExpressionContext([QgsExpressionContextUtils.meshExpressionScope(QgsMesh.Vertex)])


class QgsMeshTransformCoordinatesDockWidget(QgsDockWidget):
    def __init__(self, tool, parent=None):
        super().__init__(parent)
        self.mTool = tool
        uic.loadUi(str(Path(__file__).resolve().parents[2] / 'ui/mesh/qgsmeshtransformcoordinatesdockwidgetbase.ui'), self)
        self.setObjectName('QgsMeshTransformCoordinatesDockWidget')
        self.setWindowTitle('变换网孔顶点坐标')
        self.mPreview = QgsRubberBand(tool.canvas(), Qgis.GeometryType.Point)
        self.mPreview.setColor(QColor('magenta'))
        self.mPreview.setIconSize(8)
        self.mExpressionContextGenerator = _MeshExpressionContextGenerator()
        for axis in 'XYZ':
            edit = getattr(self, 'mExpressionEdit' + axis)
            check = getattr(self, 'mCheckBox' + axis)
            edit.setExpression('$vertex_' + axis.lower())
            edit.registerExpressionContextGenerator(self.mExpressionContextGenerator)
            edit.setEnabled(False)
            check.toggled.connect(edit.setEnabled)
        self.mButtonImport.setCheckable(False)
        self.mButtonImport.clicked.connect(self.importCoordinates)
        self.mButtonPreview.clicked.connect(self.preview)
        self.mButtonApply.clicked.connect(self.apply)
        self.visibilityChanged.connect(lambda visible: self.clearPreview() if not visible else self.updateSelection())
        self.updateSelection()

    def clearPreview(self): self.mPreview.reset(Qgis.GeometryType.Point)

    def updateSelection(self):
        self.clearPreview()
        count = len(self.mTool.mSelectedVertices)
        self.mLabelInformation.setText(f'已选择 {count} 个顶点；表达式在网孔图层坐标系中计算')
        for button in (self.mButtonPreview, self.mButtonApply): button.setEnabled(count > 0 and self.mTool.editor() is not None)
        self.mButtonImport.setEnabled(count == 1)

    def transformation(self):
        layer = self.mTool.layer()
        if not self.mTool.editor() or not self.mTool.mSelectedVertices: return None
        expressions = [getattr(self, 'mExpressionEdit'+axis).expression() if getattr(self, 'mCheckBox'+axis).isChecked() else '' for axis in 'XYZ']
        if not any(expressions):
            self.mTool.warning('请勾选要变换的坐标')
            return None
        transform = QgsMeshTransformVerticesByExpression()
        transform.setInputVertices(sorted(self.mTool.mSelectedVertices))
        transform.setExpressions(*expressions)
        if not transform.calculate(layer):
            self.mTool.warning(transform.message() or '表达式错误，或变换会破坏网孔拓扑/几何')
            return None
        return transform

    def preview(self):
        self.clearPreview()
        transform = self.transformation()
        if transform is None: return
        points = [self.mTool.toMapCoordinates(self.mTool.layer(), QgsPointXY(transform.transformedVertex(self.mTool.layer(), i))) for i in sorted(self.mTool.mSelectedVertices)]
        self.mPreview.setToGeometry(QgsGeometry.fromMultiPointXY(points), None)
        self.mPreview.show()

    def apply(self):
        transform = self.transformation()
        if transform is None: return False
        self.mTool.editor().advancedEdit(transform)
        self.mTool.onEdit()
        return True

    def importCoordinates(self):
        vertices = self.mTool.vertices()
        if len(self.mTool.mSelectedVertices) != 1: return
        point = vertices.get(next(iter(self.mTool.mSelectedVertices)))
        if point is None: return
        for axis, value in zip('XYZ', (point.x(), point.y(), point.z())):
            getattr(self, 'mExpressionEdit'+axis).setExpression(repr(value))

    def dispose(self):
        from qgis.PyQt import sip
        self.mTool.canvas().scene().removeItem(self.mPreview)
        sip.delete(self.mPreview)
