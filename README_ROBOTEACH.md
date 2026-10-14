# RoboTeach VR — Industrial Training Facility

Real-scale procedural smart-factory floor, 1 unit = 1 meter.
Generated: `RoboTeachVR.glb` (84 KB, 272 nodes, 31 meshes, 18 PBR materials)
Generator: `generate_robotteach.py` (numpy only, no Blender required)

## Layout (40 x 30 m, X x Z)
- `Building`: FloorSlab 40x30 concrete, walls h=4m, dock door west, 8 columns, 3 roof beams, 18 LED strips (emissive white) + 4 warm accents
- `CentralHub` (0,0): 8x8 plaza, kiosk pedestal + HoloScreen cyan emissive, 4 color pads N/S/E/W
- `Zone1_Warehouse_Naima` (-12,-8): 6m conveyor + 6 rollers + feeder hopper + 5 parcels, articulated arm (base/column/upper/fore/wrist+gripper), BinA blue / BinB green / Full red (open 5-piece), AGV + lidar + 4 wheels, aisle + stray pallet blocking path, dock platform + bumpers
- `Zone2_VisionQC_Chaima` (12,-8): 5m inspection conveyor, 2x OK cylinders + 2x NOK red (crack strip, missing-hole marker), gantry (2 posts+beam) + camera + lens glass + 2 red sensors + holo scan volume, desk + caliper + gauge, Conformes green / Rebuts red
- `Zone3_Assembly_Ameen` (-12,8): safety fence 8x6 yellow/orange + gate + sign, robot pedestal + precision arm + modular gripper (2 fingers), rack 3 shelves + 9 gears, staging table + tray + reducer kit (housing + 2 gears + shaft), showcase pedestal + glass + product
- `Zone4_Diagnosis_Jihed` (12,8): 4m test conveyor + drive motor + 2 sensor posts, open cabinet (back/left/right/top/bottom + door 75° open) + backplate + 3 wires + 3 fuses + breaker, spare rack 3 shelves + motor + fuse box, bench + vise + multimeter + screen + 2 probes

## Materials (Metallic-Roughness)
Concrete, SafetyYellow, DarkSteel (0.9/0.38), AluSteel, Rubber, RobotOrange, BinBlue/Green/Red, DeskWhite, Cabinet, HoloCyan (BLEND emissive), LEDWhite (emissive), Wood, Glass (BLEND), AccentWarm (emissive), ScreenDark, WallLight. All meshes have POSITION/NORMAL/TEXCOORD_0, indexed, 4-byte aligned.

## Unity import (URP + XR)
1. Unity 6+: drag `RoboTeachVR.glb` into `Assets/RoboTeachVR/`. Use UniGLTF or glTFast if native import missing.
2. Scale stays 1.0 (meters). Keep `RoboTeachVR` root at 0,0,0.
3. Prefab split: in Project view expand FBX/GLB → right-click `Building`, `CentralHub`, `Zone1..Zone4` → Prefab Unpack / Create Prefab. Each is already a clean parent node.
4. Lighting: add DirectionalLight (1.2, soft shadows 2048, frustum ±22m) + Hemisphere (sky #EAF2FF / ground #5A5A5A, 0.6) + 4 Spot accents over zones (warm, 40°, penumbra 0.5). Enable Baked GI or Light Probes for contact shadows. Emissive LED/Holo materials already set — enable Bloom (URP) for glow.
5. Collision: add BoxCollider to FloorSlab, conveyors, desks, cabinets (or MeshCollider for robots). Use XR Teleport anchors at plaza + 1 per zone.
6. VR perf: 31 shared meshes / ~272 nodes, <100 draw calls after static batching. Mark Building + desks as Static. LOD not needed (all low-poly: box 12 tris, cyl12 ~72 tris).

## Regenerate
```bash
python3 generate_robotteach.py  # rewrites RoboTeachVR.glb
```
Edit positions in the ZONE sections; `box()/cyl()/plane()` helpers handle mesh sharing automatically.
