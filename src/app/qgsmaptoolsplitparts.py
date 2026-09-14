from .qgsmaptoolsplitfeatures import _GeometryEditCapture


class QgsMapToolSplitParts(_GeometryEditCapture):
    def __init__(self, canvas, cadDock): super().__init__(canvas, cadDock, 'splitParts')
