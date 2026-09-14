"""QgsMapToolFormAnnotation, corresponding to qgsmaptoolformannotation.cpp."""
from qgis.gui import QgsFormAnnotation
from .qgsmaptoolannotation import QgsMapToolAnnotation


class QgsMapToolFormAnnotation(QgsMapToolAnnotation):
    def createItem(self): return QgsFormAnnotation()
