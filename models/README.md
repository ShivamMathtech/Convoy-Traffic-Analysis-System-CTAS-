This directory should contain `default_model.pt` (a YOLO-compatible detection
model, e.g. yolov8n.pt).

The file is intentionally not shipped with the repository. Get it with:

```bash
pip install ultralytics
# download yolov8n.pt from https://github.com/ultralytics/assets
# and place it here as: models/default_model.pt
```

Without it, CTAS still runs and honestly reports MODEL NOT AVAILABLE.
