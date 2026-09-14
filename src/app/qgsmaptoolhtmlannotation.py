"""QgsMapToolHtmlAnnotation, corresponding to qgsmaptoolhtmlannotation.cpp."""
from qgis.core import QgsHtmlAnnotation
from .qgsmaptoolannotation import QgsMapToolAnnotation


class QgsMapToolHtmlAnnotation(QgsMapToolAnnotation):
    def createItem(self): return QgsHtmlAnnotation()
