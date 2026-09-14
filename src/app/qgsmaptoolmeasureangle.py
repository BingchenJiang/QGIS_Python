from .qgsmeasuretool import QgsMeasureTool


class QgsMapToolMeasureAngle(QgsMeasureTool):
    def __init__(self, canvas): super().__init__(canvas, measureMode='angle')
