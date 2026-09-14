"""Attribute merge dialog; never merges or deletes feature geometries."""
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QComboBox, QDialogButtonBox
from qgis.core import QgsFieldConstraints


class QgsMergeAttributesDialog(QDialog):
    def __init__(self, features, layer, parent=None):
        super().__init__(parent)
        self.mFeatures, self.mLayer = features, layer
        self.setWindowTitle('合并选中要素的属性')
        layout = QVBoxLayout(self)
        self.mTableWidget = QTableWidget(len(layer.fields()), 2)
        self.mTableWidget.setHorizontalHeaderLabels(['字段', '取值方式'])
        self.mCombos = []
        for row, field in enumerate(layer.fields()):
            self.mTableWidget.setItem(row, 0, QTableWidgetItem(field.displayName()))
            combo = QComboBox()
            combo.addItem('不修改', ('skip', None))
            for feature in features: combo.addItem(f'要素 {feature.id()}: {feature[row]}', ('feature', feature.id()))
            if field.isNumeric():
                for label, mode in [('总和', 'sum'), ('最小值', 'min'), ('最大值', 'max')]: combo.addItem(label, (mode, None))
            if not field.constraints().constraints() & QgsFieldConstraints.ConstraintUnique: combo.setCurrentIndex(1)
            self.mTableWidget.setCellWidget(row, 1, combo)
            self.mCombos.append(combo)
        layout.addWidget(self.mTableWidget)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(680, 400)
    def mergedAttributes(self):
        from qgis.core import QgsVariantUtils
        values = {}
        for index, combo in enumerate(self.mCombos):
            mode, fid = combo.currentData()
            if mode == 'skip': continue
            if mode == 'feature': values[index] = next(f[index] for f in self.mFeatures if f.id() == fid)
            else:
                items = [f[index] for f in self.mFeatures if not QgsVariantUtils.isNull(f[index])]
                if items: values[index] = {'sum': sum, 'min': min, 'max': max}[mode](items)
        return values
