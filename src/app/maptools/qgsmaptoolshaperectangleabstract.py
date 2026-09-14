from src.gui.maptools.qgsmaptoolshapeabstract import QgsMapToolShapeAbstract


class QgsMapToolShapeRectangleAbstract(QgsMapToolShapeAbstract):
    keepFirstSnappedZ = True
    def rectangleCurve(self, rectangle):
        return rectangle.toLineString() if rectangle.isValid() else None
