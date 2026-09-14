"""QgsMapToolSvgAnnotation, corresponding to qgsmaptoolsvgannotation.cpp."""
from qgis.core import QgsSvgAnnotation
from .qgsmaptoolannotation import QgsMapToolAnnotation


class QgsMapToolSvgAnnotation(QgsMapToolAnnotation):
    def createItem(self): return QgsSvgAnnotation()
