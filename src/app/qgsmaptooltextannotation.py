"""QgsMapToolTextAnnotation, corresponding to qgsmaptooltextannotation.cpp."""
from qgis.core import QgsTextAnnotation
from .qgsmaptoolannotation import QgsMapToolAnnotation


class QgsMapToolTextAnnotation(QgsMapToolAnnotation):
    def createItem(self): return QgsTextAnnotation()
