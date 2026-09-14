from .qgsmaptoolsplitfeatures import _GeometryEditCapture


class QgsMapToolReshape(_GeometryEditCapture):
    def __init__(self, canvas, cadDock): super().__init__(canvas, cadDock, 'reshape')
