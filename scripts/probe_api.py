from qgis.core import QgsApplication, Qgis
from qgis import gui, core
app = QgsApplication([], True)
app.initQgis()
print(Qgis.QGIS_VERSION)
names = ['QgsBrowserDockWidget','QgsBrowserGuiModel','QgsVectorLayerProperties','QgsRasterLayerProperties','QgsMeshLayerProperties','QgsVectorTileLayerProperties','QgsDualView','QgsFieldCalculator','QgsExpressionSelectionDialog','QgsNewMemoryLayerDialog','QgsNewVectorLayerDialog','QgsNewGeoPackageLayerDialog','QgsStyleManagerDialog','QgsMessageLogViewer','QgsTemporalControllerWidget','QgsAdvancedDigitizingDockWidget','QgsSnappingWidget','QgsProjectionSelectionWidget','QgsSourceSelectProviderRegistry','QgsMapToolDigitizeFeature','QgsMapToolIdentify','QgsMapToolEmitPoint','QgsLayoutView','QgsLayoutViewToolAddItem','QgsBookmarkManagerModel','QgsLayerTreeMapCanvasBridge','QgsLayerTreeViewDefaultActions','QgsMapLayerActionRegistry','QgsVectorLayerTools','QgsAttributeDialog','QgsProcessingToolboxProxyModel','QgsProcessingAlgorithm','QgsGui','QgsProviderRegistry','QgsMapLayerStyleManager','QgsExpressionBuilderDialog']
for name in names:
    cls = getattr(gui, name, getattr(core, name, None))
    print('\n###', name, '\n', getattr(cls, '__doc__', 'UNAVAILABLE'))
    if cls:
        print('METHODS:', ','.join(n for n in dir(cls) if not n.startswith('_')))
