"""YOLO26-seg inference: per-frame top detection + annotated frame.

Wraps ultralytics' tracker into a simple generator that yields, for each
frame, the annotated BGR image (masks + labels drawn by result.plot()) plus
the single highest-confidence detection as the candidate for the gate.
"""

from ultralytics import YOLO


class Detector:
    def __init__(self, model_path: str, device: str = "mps", conf: float = 0.5):
        self.model = YOLO(model_path)
        self.device = device
        self.conf = conf

    @property
    def names(self):
        return self.model.names

    def stream(self, source):
        """Yield (annotated_bgr_frame, top_class_name_or_None, top_conf).

        Uses model.track so detections carry IDs across frames; persist=True
        keeps the tracker state between yields. stream=True makes this a lazy
        generator so we process one frame at a time without buffering.
        """
        for r in self.model.track(
            source=source,
            stream=True,
            persist=True,
            conf=self.conf,
            device=self.device,
            verbose=False,
        ):
            annotated = r.plot()  # draws masks + labels for free
            top_class, top_conf = None, 0.0
            if r.boxes is not None and len(r.boxes) > 0:
                confs = r.boxes.conf.tolist()
                i = max(range(len(confs)), key=lambda k: confs[k])
                top_conf = float(confs[i])
                top_class = self.model.names[int(r.boxes.cls[i])]
            yield annotated, top_class, top_conf
