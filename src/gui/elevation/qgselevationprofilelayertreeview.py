"""Elevation-specific decorations from the native, unbound layer tree model."""
from html import escape
from xml.etree import ElementTree
from qgis.PyQt.QtCore import Qt, QSize, QModelIndex, QSortFilterProxyModel, pyqtSignal
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QTreeView, QHeaderView, QAbstractItemView
from qgis.core import (Qgis, QgsLayerTreeModel, QgsLayerTreeLayer, QgsVectorLayer,
                       QgsRasterLayer, QgsMeshLayer, QgsSingleSymbolRenderer,
                       QgsSymbolLayerUtils, QgsRenderContext, QgsProject, QgsElevationUtils)


class QgsElevationProfileLayerTreeModel(QgsLayerTreeModel):
    addLayers = pyqtSignal(list)
    TREE_MIME = 'application/qgis.layertreemodeldata'
    SOURCE_MIME = 'application/qgis.layertree.source'

    def __init__(self, rootNode, parent=None):
        super().__init__(rootNode, parent)
        self.setFlag(self.AllowNodeReorder)
        self.setFlag(self.AllowNodeChangeVisibility)
        self.setFlag(self.ShowLegend)
        self.setFlag(self.ShowLegendAsTree)
        self.setFlag(self.AllowLegendChangeState, False)
        self.mMimeSource = b''

    def setData(self, index, value, role=Qt.EditRole):
        node = self.index2node(index)
        result = super().setData(index, value, role)
        if result and role == Qt.CheckStateRole and isinstance(node, QgsLayerTreeLayer) and node.layer():
            node.layer().setCustomProperty('_include_in_elevation_profiles', value == Qt.Checked)
            QgsProject.instance().setDirty(True)
        return result

    def mimeData(self, indexes):
        data = super().mimeData(indexes)
        if data is not None:
            self.mMimeSource = bytes(data.data(self.SOURCE_MIME))
            data.setData('application/qgis.restrictlayertreemodelsubclass', b'QgsElevationProfileLayerTreeModel')
        return data

    def isInternalDrop(self, data):
        return bool(self.mMimeSource) and bytes(data.data(self.SOURCE_MIME)) == self.mMimeSource

    def layersFromMimeData(self, data):
        try: root = ElementTree.fromstring(bytes(data.data(self.TREE_MIME)))
        except (ElementTree.ParseError, ValueError): return []
        if root.tag != 'layer_tree_model_data': return []
        layers, seen = [], set()
        # Resolve live project layers; never import provider URIs from a drop.
        for node in root.iter('layer-tree-layer'):
            layerId = node.get('id', '')
            layer = QgsProject.instance().mapLayer(layerId)
            if layer is None or layerId in seen: continue
            properties = layer.elevationProperties()
            if (properties and properties.hasElevation()) or QgsElevationUtils.canEnableElevationForLayer(layer):
                layers.append(layer)
                seen.add(layerId)
        return layers

    def canDropMimeData(self, data, action, row, column, parent):
        if action == Qt.IgnoreAction: return True
        if not data.hasFormat(self.TREE_MIME): return False
        if self.isInternalDrop(data):
            # Copying internally would create duplicate profile entries.
            return action == Qt.MoveAction and super().canDropMimeData(data, action, row, column, parent)
        return action == Qt.CopyAction and bool(self.layersFromMimeData(data))

    def dropMimeData(self, data, action, row, column, parent):
        if not self.canDropMimeData(data, action, row, column, parent): return False
        if action == Qt.IgnoreAction: return True
        if self.isInternalDrop(data): return super().dropMimeData(data, action, row, column, parent)
        self.addLayers.emit(self.layersFromMimeData(data))
        return True

    def data(self, index, role=Qt.DisplayRole):
        if role not in (Qt.DecorationRole, Qt.ToolTipRole): return super().data(index, role)
        node = self.index2node(index)
        layer = node.layer() if isinstance(node, QgsLayerTreeLayer) else None
        if layer is None: return super().data(index, role)
        properties = layer.elevationProperties()
        if role == Qt.ToolTipRole:
            title = escape(layer.title() or layer.shortName() or layer.name())
            summary = properties.htmlSummary() if properties else ''
            return '<b>' + title + '</b>' + ('<br/>' + summary if summary else '')
        symbol = self.profileSymbol(layer)
        if symbol is None: return super().data(index, role)
        context = QgsRenderContext()
        return QIcon(QgsSymbolLayerUtils.symbolPreviewPixmap(symbol, QSize(16, 16), 0, context))

    @staticmethod
    def profileSymbol(layer):
        properties = layer.elevationProperties()
        if not isinstance(layer, (QgsVectorLayer, QgsRasterLayer, QgsMeshLayer)) or properties is None: return None
        if isinstance(layer, QgsVectorLayer) and properties.type() == Qgis.VectorProfileType.IndividualFeatures:
            symbol = None
            if layer.geometryType() in (Qgis.GeometryType.Point, Qgis.GeometryType.Line) and not properties.extrusionEnabled():
                symbol = properties.profileMarkerSymbol()
            elif layer.geometryType() == Qgis.GeometryType.Polygon and properties.extrusionEnabled():
                symbol = properties.profileFillSymbol()
            if symbol is None: symbol = properties.profileLineSymbol()
            if symbol is None: return None
            symbol = symbol.clone()
            if properties.respectLayerSymbology():
                renderer = layer.renderer()
                if not isinstance(renderer, QgsSingleSymbolRenderer): return None
                source = renderer.symbol()
                if source is None: return None
                if source.type() == symbol.type(): symbol = source.clone()
                else:
                    symbol.setColor(source.color())
                    symbol.setOpacity(source.opacity())
            return symbol
        symbol = (properties.profileLineSymbol() if properties.profileSymbology() == Qgis.ProfileSurfaceSymbology.Line
                  else properties.profileFillSymbol())
        return symbol.clone() if symbol is not None else None

    def refreshLayer(self, layer):
        node = self.rootGroup().findLayer(layer.id())
        if node:
            index = self.node2index(node)
            self.dataChanged.emit(index, index, [Qt.DecorationRole, Qt.ToolTipRole])


class QgsElevationProfileLayerTreeProxyModel(QSortFilterProxyModel):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.mModel = model
        self.setSourceModel(model)
        self.setDynamicSortFilter(True)

    def filterAcceptsRow(self, sourceRow, sourceParent):
        index = self.mModel.index(sourceRow, 0, sourceParent)
        node = self.mModel.index2node(index)
        if node is not None:
            if isinstance(node, QgsLayerTreeLayer):
                layer = node.layer()
                return bool(layer and layer.elevationProperties() and layer.elevationProperties().hasElevation())
            return True
        legend = self.mModel.index2legendNode(index)
        if legend is None: return False
        layer = legend.layerNode().layer()
        return (isinstance(layer, QgsVectorLayer) and layer.elevationProperties().respectLayerSymbology()
                and not isinstance(layer.renderer(), QgsSingleSymbolRenderer))


class QgsElevationProfileLayerTreeView(QTreeView):
    addLayers = pyqtSignal(list)

    def __init__(self, rootNode, parent=None):
        super().__init__(parent)
        self.mLayerTree = rootNode
        self.mModel = QgsElevationProfileLayerTreeModel(rootNode, self)
        self.mModel.addLayers.connect(self.addLayers)
        self.mProxyModel = QgsElevationProfileLayerTreeProxyModel(self.mModel, self)
        self.setModel(self.mProxyModel)
        self.setHeaderHidden(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setExpandsOnDoubleClick(False)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

    def proxyModel(self): return self.mProxyModel
    def layerTreeModel(self): return self.mModel

    def indexToLayer(self, index):
        source = self.mProxyModel.mapToSource(index)
        node = self.mModel.index2node(source)
        if isinstance(node, QgsLayerTreeLayer): return node.layer()
        legend = self.mModel.index2legendNode(source)
        return legend.layerNode().layer() if legend else None

    def currentLayer(self): return self.indexToLayer(self.currentIndex())

    def selectedLayers(self):
        layers = {}
        for index in self.selectionModel().selectedRows():
            layer = self.indexToLayer(index)
            if layer: layers[layer.id()] = layer
        return list(layers.values())

    def populateInitialLayers(self, project):
        priority = {Qgis.LayerType.PointCloud: 0, Qgis.LayerType.Vector: 1,
                    Qgis.LayerType.Mesh: 2, Qgis.LayerType.Raster: 3}
        layers = sorted(project.mapLayers().values(), key=lambda layer: priority.get(layer.type(), 4))
        for layer in layers: self.addLayer(layer)

    def addLayer(self, layer):
        if self.mLayerTree.findLayer(layer.id()): return
        node = self.mLayerTree.addLayer(layer)
        properties = layer.elevationProperties()
        checked = layer.customProperty('_include_in_elevation_profiles', None)
        if checked is None: checked = bool(properties and properties.showByDefaultInElevationProfilePlots())
        elif isinstance(checked, str): checked = checked.lower() in ('true', '1')
        node.setItemVisibilityChecked(bool(checked))

    def resizeEvent(self, event):
        self.header().setMinimumSectionSize(self.viewport().width())
        super().resizeEvent(event)
