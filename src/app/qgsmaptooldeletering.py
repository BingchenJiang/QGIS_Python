from .qgsmaptooldeletepart import QgsMapToolDeletePart


class QgsMapToolDeleteRing(QgsMapToolDeletePart):
    def __init__(self, canvas): super().__init__(canvas, deleteRing=True)
