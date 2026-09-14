from .qgsmeasuretool import QgsMeasureTool


class QgsMapToolMeasureBearing(QgsMeasureTool):
    def __init__(self, canvas): super().__init__(canvas, measureMode='bearing')
