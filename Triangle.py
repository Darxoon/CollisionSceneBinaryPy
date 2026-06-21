class Triangle:
    Vertices: list[list[float]] = []

    A: int = None
    B: int = None
    C: int = None

    ID: int = None
    def __init__(self):
        self.Normal: list[float] = [0, 1, 0]