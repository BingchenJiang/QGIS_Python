from src.gui.maptools.qgsmaptoolshapeabstract import QgsMapToolShapeAbstract


class QgsMapToolShapeRectangleAbstract(QgsMapToolShapeAbstract):
    def rectangleCurve(self, rectangle):
        return rectangle.toLineString() if rectangle.isValid() else None
