# Computer Vision — how CTAS measures the world

This document explains the math behind the pipeline in plain language.

## 1. Detection

A YOLO-family detector (Ultralytics-compatible) maps each frame to a list of
bounding boxes `[x1, y1, x2, y2]` with class (car/truck/bus/…) and confidence.
Only vehicle classes are kept (COCO: car, motorcycle, bus, truck).

Pipeline stages in `vision/preprocessing.py`:
resize to max width → optional CLAHE contrast → letterbox to model size →
NMS (IoU threshold) → min-area filter → return boxes.

## 2. Tracking (ByteTrack / BoT-SORT adapters)

- Each frame, new detections are matched to existing tracks by **IoU overlap**
  between predicted box (constant-velocity motion) and detected box
  (Hungarian/greedy assignment in `vision/tracker.py`).
- A track becomes *confirmed* after `min_hits` matches; it dies after
  `max_age` missed frames.
- Output: persistent `track_id`, centroid trajectory, velocity vector, heading.

## 3. Perspective localization (homography)

A pinhole camera sees the world in perspective: equal real distances shrink
with depth. To convert pixels → ground meters we estimate a 3×3 **homography**
`H` from 4+ correspondences between image points `(u, v)` and ground points
`(X, Y)`:

```
[X]       [u]
[Y]  =  H [v]
[1]       [1]        (in homogeneous coordinates)
```

`H` is solved with the Direct Linear Transform (`cv2.findHomography`).
Once calibrated, each vehicle footpoint (bottom-center of bbox) maps to
`(X, Y)` meters on the ground plane.

## 4. Speed

With calibrated world positions and frame timestamps:

```
speed = |P(t2) − P(t1)| / (t2 − t1)      →  m/s → ×3.6 = km/h
```

A moving-average window smooths jitter. Without calibration the same formula
runs on pixel centroids and is reported as `px/s` — never relabelled km/h.

## 5. Spacing & lane assignment

- **Spacing:** Euclidean distance between consecutive vehicle centroids
  (meters when calibrated, pixels otherwise).
- **Lanes:** operator-drawn polygons; `point-in-polygon` test assigns each
  vehicle to a lane, enabling per-lane flow and occupancy.

## 6. Convoy / group analysis

Vehicles form a *candidate group* when they stay within `dmax` distance and
`hmax` heading difference for at least `tmin` seconds (`vision/group_analysis.py`,
Union-Find clustering + persistence filter). Metrics: group size, span,
average speed, cohesion.

## 7. Events

Rule-based on real state only (`analytics/events.py`):

- **stopped_vehicle**: speed < threshold for N seconds
- **congestion**: density above threshold in a zone
- **overspeed**: speed above configured limit (metric only)
- **close_spacing**: spacing below safe distance (metric only)
- **lane_crossing / group_formed / group_dissolved / session events**

No rule ever fires on invented data; metric rules require calibration.

## 8. Demo source

`streaming/demo.py` renders a fully synthetic traffic scene and burns in
**"DEMO / SYNTHETIC DATA"** so synthetic results can never be mistaken for
real measurements.
