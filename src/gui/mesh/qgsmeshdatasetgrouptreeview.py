"""List-model portion of QGIS qgsmeshdatasetgrouptreeview.cpp."""
from qgis.PyQt.QtCore import QAbstractListModel, QModelIndex, Qt


class QgsMeshDatasetGroupListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mItems = []
        self.mDisplayProviderName = False

    def syncToLayer(self, layer):
        self.beginResetModel()
        # Calculations can rebuild the native tree while this Python dialog is
        # still open. Keep values, not borrowed pointers into the old tree.
        self.mItems = []
        if layer:
            root = layer.datasetGroupTreeRootItem()
            for group in root.enabledDatasetGroupIndexes():
                item = root.childFromDatasetGroupIndex(group)
                self.mItems.append((group, item.name(), item.providerName()))
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.mItems) if not parent.isValid() else 0

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < self.rowCount(): return None
        group, name, providerName = self.mItems[index.row()]
        if role == Qt.UserRole: return group
        if role == Qt.DisplayRole:
            return providerName if self.mDisplayProviderName else name
        return None

    def setDisplayProviderName(self, enabled): self.mDisplayProviderName = enabled
    def variableNames(self): return [self.data(self.index(row)) for row in range(self.rowCount())]
