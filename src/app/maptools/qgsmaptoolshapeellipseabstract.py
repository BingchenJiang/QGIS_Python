from src.gui.maptools.qgsmaptoolshapeabstract import QgsMapToolShapeAbstract


class QgsMapToolShapeEllipseAbstract(QgsMapToolShapeAbstract):
    def ellipseCurve(self, ellipse):
        return None if ellipse.isEmpty() else ellipse.toLineString(self.segments())
