"""Application layer-tree context menu; upstream class/file names retained."""
from qgis.PyQt.QtWidgets import QMenu, QInputDialog
from qgis.core import QgsLayerTreeLayer, QgsLayerTreeGroup, QgsMapLayerType
from qgis.gui import QgsLayerTreeViewMenuProvider


class QgsAppLayerTreeViewMenuProvider(QgsLayerTreeViewMenuProvider):
    def __init__(self, view, canvas, app):
        super().__init__()
        self.mView, self.mCanvas, self.mApp = view, canvas, app

    def createContextMenu(self):
        menu = QMenu(self.mView)
        defaults = self.mView.defaultActions()
        node = self.mView.currentNode()
        menu.addAction(defaults.actionAddGroup(menu))
        menu.addAction('展开全部', self.mView.expandAll)
        menu.addAction('折叠全部', self.mView.collapseAll)
        if node is None:
            return menu
        menu.addSeparator()
        menu.addAction(defaults.actionRenameGroupOrLayer(menu))
        menu.addAction('移除图层/组', self.mApp.removeLayer)
        if isinstance(node, QgsLayerTreeGroup):
            menu.addAction(defaults.actionMutuallyExclusiveGroup(menu))
            menu.addAction(defaults.actionGroupSelected(menu))
        if not isinstance(node, QgsLayerTreeLayer):
            return menu
        layer = node.layer()
        self.mApp.setActiveLayer(layer)
        menu.addSeparator()
        for name in ['mActionZoomToLayer', 'mActionZoomToSelected', 'mActionDuplicateLayer',
                     'mActionSetLayerScaleVisibility', 'mActionSetLayerCRS', 'mActionSetProjectCRSFromLayer']:
            action = getattr(self.mApp, name, None)
            if action:
                menu.addAction(action)
        menu.addAction(defaults.actionShowInOverview(menu))
        if layer.type() == QgsMapLayerType.VectorLayer:
            menu.addSeparator()
            for name in ['mActionOpenTable', 'mActionToggleEditing', 'mActionSaveEdits', 'mActionLayerSubsetString']:
                menu.addAction(getattr(self.mApp, name))
            menu.addAction(defaults.actionShowFeatureCount(menu))
        menu.addSeparator()
        export = menu.addMenu('导出')
        export.addAction(self.mApp.mActionLayerSaveAs)
        export.addAction('保存图层定义…', self.mApp.saveAsLayerDefinition)
        styles = menu.addMenu('样式')
        styles.addAction(self.mApp.mActionCopyStyle)
        styles.addAction(self.mApp.mActionPasteStyle)
        styles.addAction('加载样式…', self.mApp.loadStyle)
        styles.addAction('保存样式…', self.mApp.saveStyle)
        manager = layer.styleManager()
        styles.addSeparator()
        for name in manager.styles():
            action = styles.addAction(name or '默认')
            action.setCheckable(True)
            action.setChecked(name == manager.currentStyle())
            action.triggered.connect(lambda checked=False, n=name: manager.setCurrentStyle(n))
        styles.addAction('添加样式…', lambda: self.addStyle(layer))
        menu.addSeparator()
        for action in self.mApp.customLayerActions(layer):
            menu.addAction(action)
        menu.addAction(self.mApp.mActionLayerProperties)
        return menu

    def addStyle(self, layer):
        name, ok = QInputDialog.getText(self.mApp, '新样式', '名称')
        if ok and name:
            layer.styleManager().addStyleFromLayer(name)
            layer.styleManager().setCurrentStyle(name)

