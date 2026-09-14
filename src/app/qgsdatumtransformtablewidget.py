"""Default coordinate operations with the native PROJ operation chooser."""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QDialog, QFormLayout, QDialogButtonBox
from qgis.core import QgsCoordinateTransformContext, QgsCoordinateReferenceSystem
from qgis.gui import QgsProjectionSelectionWidget, QgsCoordinateOperationWidget


class QgsDatumTransformTableWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mContext = QgsCoordinateTransformContext()
        self.mContext.readSettings()
        layout = QVBoxLayout(self)
        self.mTableView = QTableWidget(0, 4, self)
        self.mTableView.setHorizontalHeaderLabels(['源 CRS', '目标 CRS', '坐标操作', '允许回退'])
        self.mTableView.setSelectionBehavior(QTableWidget.SelectRows)
        self.mTableView.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.mTableView)
        buttons = QHBoxLayout()
        for name, label, slot in [('mAddButton', '添加', self.addDatumTransform), ('mEditButton', '编辑', self.editDatumTransform), ('mRemoveButton', '移除', self.removeDatumTransform)]:
            button = QPushButton(label, self)
            button.clicked.connect(slot)
            setattr(self, name, button)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.mTableView.itemSelectionChanged.connect(self.selectionChanged)
        self.reload()
    def transformContext(self): return QgsCoordinateTransformContext(self.mContext)
    def setTransformContext(self, context):
        self.mContext = QgsCoordinateTransformContext(context)
        self.reload()
    def reload(self):
        operations = self.mContext.coordinateOperations()
        self.mKeys = list(operations)
        self.mTableView.setRowCount(len(operations))
        for row, (source, destination) in enumerate(self.mKeys):
            fallback = self.mContext.allowFallbackTransform(QgsCoordinateReferenceSystem(source), QgsCoordinateReferenceSystem(destination))
            for col, value in enumerate((source, destination, operations[(source, destination)], '是' if fallback else '否')):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.mTableView.setItem(row, col, item)
        self.selectionChanged()
    def selectionChanged(self):
        selected = bool(self.mTableView.selectedItems())
        self.mEditButton.setEnabled(selected)
        self.mRemoveButton.setEnabled(selected)
    def removeDatumTransform(self):
        row = self.mTableView.currentRow()
        if row >= 0:
            self.mContext.removeCoordinateOperation(*[QgsCoordinateReferenceSystem(value) for value in self.mKeys[row]])
            self.reload()
    def addDatumTransform(self): self.editOperation()
    def editDatumTransform(self):
        row = self.mTableView.currentRow()
        if row >= 0: self.editOperation(self.mKeys[row])
    def editOperation(self, key=None):
        dialog = QDialog(self)
        dialog.setWindowTitle('选择坐标操作')
        dialog.resize(800, 550)
        layout = QFormLayout(dialog)
        source, destination = QgsProjectionSelectionWidget(dialog), QgsProjectionSelectionWidget(dialog)
        chooser = QgsCoordinateOperationWidget(dialog)
        chooser.setShowFallbackOption(True)
        source.crsChanged.connect(chooser.setSourceCrs)
        destination.crsChanged.connect(chooser.setDestinationCrs)
        if key:
            source.setCrs(QgsCoordinateReferenceSystem(key[0]))
            destination.setCrs(QgsCoordinateReferenceSystem(key[1]))
            chooser.setSelectedOperationUsingContext(self.mContext)
        layout.addRow('源 CRS', source)
        layout.addRow('目标 CRS', destination)
        layout.addRow(chooser)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        buttons.button(QDialogButtonBox.Ok).setEnabled(chooser.hasSelection())
        chooser.operationChanged.connect(lambda: buttons.button(QDialogButtonBox.Ok).setEnabled(chooser.hasSelection()))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec_():
            operation = chooser.selectedOperation()
            context = QgsCoordinateTransformContext(self.mContext)
            if key: context.removeCoordinateOperation(*[QgsCoordinateReferenceSystem(value) for value in key])
            context.addCoordinateOperation(source.crs(), destination.crs(), operation.proj, operation.allowFallback)
            self.setTransformContext(context)
