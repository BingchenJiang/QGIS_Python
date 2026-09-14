"""Identify controller corresponding to qgsmaptoolidentifyaction.cpp."""
from qgis.gui import QgsMapToolIdentify
from qgis.PyQt.QtWidgets import QTreeWidgetItem


class QgsMapToolIdentifyAction(QgsMapToolIdentify):
    def __init__(self, canvas, app):
        super().__init__(canvas)
        self.mApp = app
        self.mResults = []

    def canvasReleaseEvent(self, event):
        self.showIdentifyResults(self.identify(event.pos().x(), event.pos().y(), self.TopDownAll, self.AllLayers))

    def showIdentifyResults(self, results):
        self.mResults = list(results)
        tree = self.mApp.mIdentifyResults
        tree.clear()
        for result in self.mResults:
            group = QTreeWidgetItem(tree, [result.mLayer.name(), result.mLabel])
            feature = result.mFeature
            if feature.isValid():
                for field, value in zip(feature.fields(), feature.attributes()):
                    QTreeWidgetItem(group, [field.displayName(), str(value)])
            for key, value in result.mDerivedAttributes.items():
                QTreeWidgetItem(group, [key, str(value)])
            for key, value in result.mAttributes.items():
                QTreeWidgetItem(group, [key, str(value)])
        tree.expandAll()
        self.mApp.mIdentifyResultsDock.show()
