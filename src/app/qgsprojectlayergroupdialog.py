"""QgsProjectLayerGroupDialog using the original form and a native layer tree.

QGIS 3.34 exposes createEmbeddedGroup, but not createEmbeddedLayer to Python.
Individual layers remain visible in the tree but cannot be selected for embedding.
"""
from pathlib import Path
from zipfile import ZipFile, is_zipfile
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QLabel
from qgis.core import QgsProject, QgsSettings, QgsLayerTree, QgsLayerTreeModel, QgsLayerTreeGroup, QgsLayerTreeLayer, QgsReadWriteContext, QgsLayerTreeUtils
from qgis.gui import QgsGui


class QgsEmbeddedLayerTreeModel(QgsLayerTreeModel):
    def flags(self, index):
        flags = super().flags(index)
        if isinstance(self.index2node(index), QgsLayerTreeLayer): flags &= ~Qt.ItemIsSelectable
        return flags

    def data(self, index, role=Qt.DisplayRole):
        if role in (Qt.FontRole, Qt.ForegroundRole): return None
        if role == Qt.ToolTipRole and isinstance(self.index2node(index), QgsLayerTreeLayer):
            return '当前支持选择父组进行原生嵌入；单图层嵌入接口尚未移植。'
        return super().data(index, role)


class QgsProjectLayerGroupDialog(QDialog):
    def __init__(self, parent=None, projectFile=''):
        super().__init__(parent)
        uic.loadUi(str(Path(__file__).resolve().parents[1] / 'ui/qgsprojectlayergroupdialogbase.ui'), self)
        QgsGui.enableAutoGeometryRestore(self)
        self.mRootGroup = QgsLayerTree()
        self.mModel = QgsEmbeddedLayerTreeModel(self.mRootGroup, self)
        self.mTreeView.setModel(self.mModel)
        self.mProjectPath = ''
        self.mProjectFileWidget.setFilter('QGIS 工程 (*.qgs *.qgz *.QGS *.QGZ)')
        self.mProjectFileWidget.setDefaultRoot(QgsSettings().value('qgis/last_embedded_project_path', str(Path.home())))
        self.mStatusLabel = QLabel('请选择要嵌入的组。单图层嵌入接口尚未移植，可先在源工程中将图层放入一个组。', self)
        self.mStatusLabel.setWordWrap(True)
        self.gridLayout.addWidget(self.mStatusLabel, self.gridLayout.rowCount(), 0)
        self.mButtonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.mTreeView.selectionModel().selectionChanged.connect(self.onTreeViewSelectionChanged)
        self.mProjectFileWidget.fileChanged.connect(self.changeProjectFile)
        self.mButtonBox.accepted.connect(self.accept)
        self.mButtonBox.rejected.connect(self.reject)
        self.mButtonBox.helpRequested.connect(self.showHelp)
        if projectFile: self.mProjectFileWidget.setFilePath(projectFile)

    @staticmethod
    def readProjectDocument(filename):
        path = Path(filename)
        if is_zipfile(path):
            with ZipFile(path) as archive:
                candidates = [name for name in archive.namelist() if name.lower().endswith('.qgs')]
                if len(candidates) != 1: raise ValueError('QGZ 中必须包含一个 QGS 工程文件')
                content = archive.read(candidates[0])
        else: content = path.read_bytes()
        document = QDomDocument()
        result = document.setContent(content)
        if not result[0]: raise ValueError('工程 XML 无法读取：' + result[1])
        return document

    def changeProjectFile(self, *args):
        self.mProjectPath = ''
        self.mRootGroup.removeAllChildren()
        self.mButtonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        filename = self.mProjectFileWidget.filePath()
        try:
            current = QgsProject.instance().fileName()
            if current and Path(filename).resolve() == Path(current).resolve(): raise ValueError('不能从当前工程嵌入自身')
            document = self.readProjectDocument(filename)
            root = document.documentElement()
            element = root.firstChildElement('layer-tree-group')
            if element.isNull(): QgsLayerTreeUtils.readOldLegend(self.mRootGroup, root.firstChildElement('legend'))
            else: self.mRootGroup.readChildrenFromXml(element, QgsReadWriteContext())
            self.removeEmbeddedNodes(self.mRootGroup)
            self.mProjectPath = str(Path(filename).resolve())
            self.mTreeView.expandAll()
            self.mStatusLabel.setText('请选择组；已嵌入的节点不会再次嵌入。单图层请先在源工程中归组。')
        except (OSError, ValueError, RuntimeError) as error:
            self.mRootGroup.removeAllChildren()
            self.mStatusLabel.setText(str(error))

    def removeEmbeddedNodes(self, group):
        for child in list(group.children()):
            if child.customProperty('embedded', False): group.removeChildNode(child)
            elif isinstance(child, QgsLayerTreeGroup): self.removeEmbeddedNodes(child)

    def selectedNodes(self): return self.mTreeView.selectedNodes(True)
    def selectedGroups(self): return [node.name() for node in self.selectedNodes() if isinstance(node, QgsLayerTreeGroup)]
    def selectedLayerIds(self): return []
    def selectedProjectFile(self): return self.mProjectPath
    def isValid(self): return bool(self.mProjectPath)

    def onTreeViewSelectionChanged(self, *args):
        self.mButtonBox.button(QDialogButtonBox.Ok).setEnabled(self.isValid() and bool(self.selectedGroups()))

    def accept(self):
        if not self.isValid() or not self.selectedGroups(): return
        QgsSettings().setValue('qgis/last_embedded_project_path', str(Path(self.mProjectPath).parent))
        super().accept()

    def showHelp(self):
        from qgis.PyQt.QtCore import QUrl
        from qgis.PyQt.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl('https://docs.qgis.org/3.34/en/docs/user_manual/introduction/general_tools.html#nesting-projects'))
