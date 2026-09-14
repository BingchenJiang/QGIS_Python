from src.gui.maptools.qgsmaptoolshapeabstract import QgsMapToolShapeAbstract


class QgsMapToolShapeRegularPolygonAbstract(QgsMapToolShapeAbstract):
    regularPolygon = True
    keepFirstSnappedZ = True
    def polygonCurve(self, polygon): return None if polygon.isEmpty() else polygon.toLineString()
