#!/usr/bin/env python3
"""
RoboTeach VR - Procedural Industrial Training Facility Generator
Generates a unified real-scale (1 unit = 1 meter) GLB scene with:
 - Central Hub + 4 training zones
 - Low-poly manifold meshes, PBR Metallic-Roughness
 - Modular node hierarchy for Unity prefab separation
No external deps beyond numpy.
"""
import json, struct, math
import numpy as np

# ---------------- GLTF helpers ----------------
materials = []
def add_mat(name, base, metallic=0.0, roughness=0.6, emissive=None, alpha=None):
    m = {"name": name, "pbrMetallicRoughness": {
        "baseColorFactor": base, "metallicFactor": metallic, "roughnessFactor": roughness}}
    if emissive is not None:
        m["emissiveFactor"] = emissive
    if alpha is not None:
        m["alphaMode"] = alpha
        if alpha == "BLEND":
            m["doubleSided"] = True
    materials.append(m)
    return len(materials)-1

M_CONCRETE = add_mat("Concrete", [0.72,0.72,0.74,1.0], 0.0, 0.85)
M_YELLOW   = add_mat("SafetyYellow", [0.98,0.78,0.06,1.0], 0.0, 0.55)
M_DSTEEL   = add_mat("DarkSteel", [0.20,0.21,0.23,1.0], 0.9, 0.38)
M_ASTEEL   = add_mat("AluSteel", [0.62,0.64,0.67,1.0], 0.9, 0.32)
M_RUBBER   = add_mat("Rubber", [0.07,0.07,0.08,1.0], 0.0, 0.92)
M_ORANGE   = add_mat("RobotOrange", [0.94,0.36,0.05,1.0], 0.25, 0.45)
M_BLUE     = add_mat("BinBlue", [0.11,0.34,0.84,1.0], 0.0, 0.5)
M_GREEN    = add_mat("BinGreen", [0.09,0.62,0.24,1.0], 0.0, 0.5)
M_RED      = add_mat("BinRed", [0.82,0.12,0.12,1.0], 0.0, 0.5)
M_WHITE    = add_mat("DeskWhite", [0.91,0.91,0.92,1.0], 0.0, 0.42)
M_CAB      = add_mat("Cabinet", [0.42,0.50,0.48,1.0], 0.55, 0.5)
M_HOLO     = add_mat("HoloCyan", [0.25,0.90,1.0,0.85], 0.0, 0.2, emissive=[0.2,0.8,1.0], alpha="BLEND")
M_LED      = add_mat("LEDWhite", [1.0,1.0,1.0,1.0], 0.0, 0.3, emissive=[1.0,1.0,0.95])
M_WOOD     = add_mat("Wood", [0.52,0.36,0.20,1.0], 0.0, 0.8)
M_GLASS    = add_mat("Glass", [0.80,0.94,1.0,0.30], 0.0, 0.12, alpha="BLEND")
M_WARM     = add_mat("AccentWarm", [1.0,0.75,0.35,1.0], 0.0, 0.4, emissive=[1.0,0.62,0.18])
M_DARK     = add_mat("ScreenDark", [0.04,0.06,0.09,1.0], 0.2, 0.5, emissive=[0.05,0.12,0.2])
M_WALL     = add_mat("WallLight", [0.82,0.83,0.85,1.0], 0.0, 0.7)

# ---------------- primitive geometry (unit, centered) ----------------
def make_box():
    # 24 verts, correct normals/uvs, manifold
    P, N, UV, I = [], [], [], []
    faces = [
        # +X
        ([1,-1,-1],[1,1,-1],[1,1,1],[1,-1,1],[1,0,0]),
        # -X
        ([-1,-1,1],[-1,1,1],[-1,1,-1],[-1,-1,-1],[-1,0,0]),
        # +Y
        ([-1,1,-1],[-1,1,1],[1,1,1],[1,1,-1],[0,1,0]),
        # -Y
        ([-1,-1,1],[-1,-1,-1],[1,-1,-1],[1,-1,1],[0,-1,0]),
        # +Z
        ([-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1],[0,0,1]),
        # -Z
        ([1,-1,-1],[-1,-1,-1],[-1,1,-1],[1,1,-1],[0,0,-1]),
    ]
    # box spans -0.5..0.5 ; faces above are -1..1 so scale later
    for (a,b,c,d,n) in faces:
        base = len(P)
        for v in [a,b,c,d]:
            P.append([v[0]*0.5, v[1]*0.5, v[2]*0.5])
            N.append(n)
        UV.extend([[0,0],[1,0],[1,1],[0,1]])
        I.extend([base,base+1,base+2, base,base+2,base+3])
    return np.array(P,np.float32), np.array(N,np.float32), np.array(UV,np.float32), np.array(I,np.uint16)

def make_cyl(seg=12):
    P,N,UV,I = [],[],[],[]
    r, h = 0.5, 1.0
    # side
    for i in range(seg):
        a0 = 2*math.pi*i/seg; a1 = 2*math.pi*(i+1)/seg
        x0,z0 = math.cos(a0)*r, math.sin(a0)*r
        x1,z1 = math.cos(a1)*r, math.sin(a1)*r
        base = len(P)
        for (x,z,y) in [(x0,z0,-h/2),(x1,z1,-h/2),(x1,z1,h/2),(x0,z0,h/2)]:
            P.append([x,y,z]); n=[x/r,0,z/r]; N.append(n)
        UV.extend([[i/seg,0],[(i+1)/seg,0],[(i+1)/seg,1],[i/seg,1]])
        I.extend([base,base+1,base+2, base,base+2,base+3])
    # caps
    for top,ny in [(h/2,1.0),(-h/2,-1.0)]:
        c = len(P); P.append([0,top,0]); N.append([0,ny,0]); UV.append([0.5,0.5])
        ring=[]
        for i in range(seg):
            a=2*math.pi*i/seg; x,z=math.cos(a)*r, math.sin(a)*r
            P.append([x,top,z]); N.append([0,ny,0]); UV.append([0.5+x,0.5+z])
            ring.append(len(P)-1)
        for i in range(seg):
            if ny>0: I.extend([c, ring[i], ring[(i+1)%seg]])
            else: I.extend([c, ring[(i+1)%seg], ring[i]])
    return np.array(P,np.float32), np.array(N,np.float32), np.array(UV,np.float32), np.array(I,np.uint16)

def make_plane():
    P=np.array([[-0.5,0,-0.5],[0.5,0,-0.5],[0.5,0,0.5],[-0.5,0,0.5]],np.float32)
    N=np.array([[0,1,0]]*4,np.float32)
    UV=np.array([[0,0],[1,0],[1,1],[0,1]],np.float32)
    I=np.array([0,1,2,0,2,3],np.uint16)
    return P,N,UV,I

GEOMS = {"BOX": make_box(), "CYL12": make_cyl(12), "CYL8": make_cyl(8), "PLANE": make_plane()}

meshes = []  # list of {name, geom, mat}
mesh_cache = {}
def mesh_id(geom, mat, name=None):
    key=(geom,mat)
    if key in mesh_cache: return mesh_cache[key]
    mid=len(meshes)
    meshes.append({"name": name or f"{geom}_{mat}", "geom":geom, "mat":mat})
    mesh_cache[key]=mid
    return mid

nodes=[]
def euler_to_quat(rx=0, ry=0, rz=0):
    # degrees -> quat xyzw
    rx,ry,rz = map(math.radians,(rx,ry,rz))
    cx,sx=math.cos(rx/2),math.sin(rx/2); cy,sy=math.cos(ry/2),math.sin(ry/2); cz,sz=math.cos(rz/2),math.sin(rz/2)
    qx=sx*cy*cz+cx*sy*sz; qy=cx*sy*cz-sx*cy*sz; qz=cx*cy*sz+sx*sy*cz; qw=cx*cy*cz-sx*sy*sz
    return [qx,qy,qz,qw]

def add_node(name, parent=None, mesh=None, t=None, s=None, r=None):
    n={"name":name}
    if mesh is not None: n["mesh"]=mesh
    if t is not None: n["translation"]=[float(t[0]),float(t[1]),float(t[2])]
    if s is not None: n["scale"]=[float(s[0]),float(s[1]),float(s[2])]
    if r is not None: n["rotation"]=r
    n["children"]=[]
    idx=len(nodes); nodes.append(n)
    if parent is not None: nodes[parent]["children"].append(idx)
    return idx

def box(parent, name, mat, pos, size, rot=None):
    return add_node(name, parent, mesh_id("BOX",mat,f"{name}_m"), t=pos, s=size, r=rot)
def cyl(parent, name, mat, pos, r_top_dia=None, size=None, rot=None, geom="CYL12", dia=None, height=None):
    # size = [sx,sy,sz] where sx,sz scale diameter, sy height
    if size is None:
        size=[dia,height,dia]
    return add_node(name, parent, mesh_id(geom,mat,f"{name}_m"), t=pos, s=size, r=rot)
def plane(parent, name, mat, pos, size):
    # size [w,d]
    return add_node(name, parent, mesh_id("PLANE",mat,f"{name}_m"), t=pos, s=[size[0],1,size[1]])

# ---------------- hierarchy ----------------
root = add_node("RoboTeachVR")
bld = add_node("Building", root)
hub = add_node("CentralHub", root)
z1 = add_node("Zone1_Warehouse_Naima", root)
z2 = add_node("Zone2_VisionQC_Chaima", root)
z3 = add_node("Zone3_Assembly_Ameen", root)
z4 = add_node("Zone4_Diagnosis_Jihed", root)

# ===== Building: floor 40x30 =====
box(bld,"FloorSlab",M_CONCRETE,[0,-0.1,0],[40,0.2,30])
# perimeter walls h=4, thickness 0.3 (4 walls, dock opening on west)
box(bld,"Wall_North",M_WALL,[0,2.0,-15],[40,4.0,0.3])
box(bld,"Wall_South",M_WALL,[0,2.0,15],[40,4.0,0.3])
box(bld,"Wall_East",M_WALL,[20,2.0,0],[0.3,4.0,30])
box(bld,"Wall_West_A",M_WALL,[-20,2.0,-9.5],[0.3,4.0,11])
box(bld,"Wall_West_B",M_WALL,[-20,2.0,9.5],[0.3,4.0,11])
box(bld,"DockDoorFrame_Top",M_DSTEEL,[-20,3.6,0],[0.5,0.4,8.0])
box(bld,"DockDoor_Left",M_DSTEEL,[-20,1.5,-4.0],[0.5,3.0,0.4])
box(bld,"DockDoor_Right",M_DSTEEL,[-20,1.5,4.0],[0.5,3.0,0.4])
# columns
for cx in [-15,-5,5,15]:
    for cz in [-10,10]:
        box(bld,f"Column_{cx}_{cz}",M_DSTEEL,[cx,3.0,cz],[0.4,6.0,0.4])
# roof beams
for cz in [-10,0,10]:
    box(bld,f"RoofBeam_{cz}",M_DSTEEL,[0,5.7,cz],[40,0.3,0.4])
# LED strips
for lx in [-15,-9,-3,3,9,15]:
    for lz in [-10,0,10]:
        box(bld,f"LED_{lx}_{lz}",M_LED,[lx,5.45,lz],[2.2,0.1,0.35])
# accent zone lights (warm)
for (ax,az) in [(-12,-8),(12,-8),(-12,8),(12,8)]:
    box(bld,f"Accent_{ax}_{az}",M_WARM,[ax,5.2,az],[1.5,0.12,1.5])
# main walkways: yellow edge lines (cross)
plane(bld,"Walkway_N_S1",M_YELLOW,[ -1.2,0.012,0],[0.15,28])
plane(bld,"Walkway_N_S2",M_YELLOW,[ 1.2,0.012,0],[0.15,28])
plane(bld,"Walkway_E_W1",M_YELLOW,[0,0.012,-1.2],[38,0.15])
plane(bld,"Walkway_E_W2",M_YELLOW,[0,0.012,1.2],[38,0.15])

# ===== Central Hub plaza 8x8 =====
box(hub,"PlazaBase",M_DSTEEL,[0,0.03,0],[8,0.06,8])
plane(hub,"PlazaBorder_N",M_YELLOW,[0,0.065,-3.9],[8,0.2])
plane(hub,"PlazaBorder_S",M_YELLOW,[0,0.065,3.9],[8,0.2])
plane(hub,"PlazaBorder_E",M_YELLOW,[3.9,0.065,0],[0.2,8])
plane(hub,"PlazaBorder_W",M_YELLOW,[-3.9,0.065,0],[0.2,8])
# kiosk pedestal + holo
cyl(hub,"KioskPedestal",M_ASTEEL,[0,0.55,0],size=[0.8,1.1,0.8])
box(hub,"KioskBaseTrim",M_YELLOW,[0,0.12,0],[1.0,0.08,1.0])
box(hub,"HoloScreen",M_HOLO,[0,1.85,0],[1.4,0.8,0.06])
box(hub,"HoloScreenFrame",M_DSTEEL,[0,1.85,-0.05],[1.5,0.9,0.03])
cyl(hub,"HoloEmitter",M_DARK,[0,1.15,0],size=[0.3,0.15,0.3])
# 4 direction pads
plane(hub,"Pad_North",M_BLUE,[0,0.065,-2.8],[1.0,1.0])
plane(hub,"Pad_South",M_GREEN,[0,0.065,2.8],[1.0,1.0])
plane(hub,"Pad_West",M_ORANGE,[-2.8,0.065,0],[1.0,1.0])
plane(hub,"Pad_East",M_RED,[2.8,0.065,0],[1.0,1.0])

# ===== Zone 1: Warehouse (-12,-8) =====
# zone floor border
for (ox,oz,w,d) in [(-12,-13.5,14,0.15),(-12,-2.5,14,0.15),(-19,-8,0.15,11),(-5,-8,0.15,11)]:
    plane(z1,f"Border_{ox}_{oz}",M_YELLOW,[ox,0.012,oz],[w,d])
# conveyor line 6m along X at (-12,0,-9)
box(z1,"ConvFrame",M_DSTEEL,[-12,0.75,-9],[6.0,0.25,1.0])
box(z1,"ConvBelt",M_RUBBER,[-12,0.90,-9],[6.0,0.06,0.9])
for i,lx in enumerate([-14.5,-13.5,-12.5,-11.5,-10.5,-9.5]):
    cyl(z1,f"Roller_{i}",M_ASTEEL,[lx,0.88,-9],size=[0.12,0.9,0.12],rot=euler_to_quat(90,0,0),geom="CYL12")
for lx,lz in [(-14.8,-9.4),(-14.8,-8.6),(-9.2,-9.4),(-9.2,-8.6)]:
    box(z1,f"ConvLeg_{lx}_{lz}",M_DSTEEL,[lx,0.35,lz],[0.12,0.7,0.12])
# feeder hopper at west end
box(z1,"FeederHopper",M_ASTEEL,[-15.4,1.2,-9],[0.8,0.8,1.2])
box(z1,"FeederChute",M_DSTEEL,[-14.9,0.95,-9],[0.6,0.15,0.8])
# parcels on belt (mixed)
box(z1,"Parcel_1",M_BLUE,[-13.8,1.08,-9],[0.4,0.3,0.4])
box(z1,"Parcel_2",M_WOOD,[-13.0,1.05,-9.1],[0.35,0.25,0.35])
box(z1,"Parcel_3",M_GREEN,[-12.2,1.10,-8.9],[0.45,0.35,0.4])
box(z1,"Parcel_4",M_WHITE,[-11.3,1.03,-9],[0.3,0.2,0.3])
box(z1,"Parcel_5",M_RED,[-10.4,1.07,-9.05],[0.38,0.28,0.38])
# robot arm beside conveyor (south side)
cyl(z1,"RobotBase",M_DSTEEL,[-12,0.2,-6.2],size=[0.6,0.4,0.6])
box(z1,"RobotColumn",M_ORANGE,[-12,0.85,-6.2],[0.35,0.9,0.35])
box(z1,"RobotUpperArm",M_ORANGE,[-12,1.45,-6.7],[0.25,0.25,1.4],rot=euler_to_quat(20,0,0))
box(z1,"RobotForearm",M_ASTEEL,[-12,1.7,-7.6],[0.18,0.18,1.0],rot=euler_to_quat(-30,0,0))
box(z1,"RobotWrist",M_DSTEEL,[-12,1.45,-8.2],[0.2,0.2,0.25])
box(z1,"Gripper_L",M_DSTEEL,[-12.1,1.3,-8.4],[0.06,0.25,0.12])
box(z1,"Gripper_R",M_DSTEEL,[-11.9,1.3,-8.4],[0.06,0.25,0.12])
cyl(z1,"Joint_Shoulder",M_DSTEEL,[-12,1.3,-6.2],size=[0.4,0.3,0.4],rot=euler_to_quat(90,0,0))
# sorting bins
def open_bin(parent,name,mat,x,z,label=None):
    box(parent,f"{name}_Bottom",mat,[x,0.15,z],[0.9,0.1,0.7])
    box(parent,f"{name}_W1",mat,[x,0.45,z-0.32],[0.9,0.6,0.06])
    box(parent,f"{name}_W2",mat,[x,0.45,z+0.32],[0.9,0.6,0.06])
    box(parent,f"{name}_W3",mat,[x-0.42,0.45,z],[0.06,0.6,0.7])
    box(parent,f"{name}_W4",mat,[x+0.42,0.45,z],[0.06,0.6,0.7])
open_bin(z1,"BinA",M_BLUE,-10.5,-5.5)
open_bin(z1,"BinB",M_GREEN,-12.0,-5.5)
open_bin(z1,"BinFull",M_RED,-13.5,-5.5)
box(z1,"BinFull_Lid",M_DSTEEL,[-13.5,0.78,-5.5],[0.95,0.06,0.75])
# AGV
box(z1,"AGV_Base",M_ORANGE,[-8.5,0.18,-6.0],[1.2,0.25,0.8])
box(z1,"AGV_Top",M_DSTEEL,[-8.5,0.36,-6.0],[0.9,0.12,0.6])
cyl(z1,"AGV_Lidar",M_DARK,[-8.5,0.55,-6.0],size=[0.15,0.2,0.15])
box(z1,"AGV_Parcel",M_WOOD,[-8.5,0.58,-6.0],[0.5,0.3,0.5])
for wx,wz in [(-8.9,-6.35),(-8.1,-6.35),(-8.9,-5.65),(-8.1,-5.65)]:
    cyl(z1,f"AGV_Wheel_{wx}_{wz}",M_RUBBER,[wx,0.1,wz],size=[0.2,0.12,0.2],rot=euler_to_quat(90,0,0))
# aisle + stray pallet blocking path to dock
plane(z1,"AisleLine_1",M_YELLOW,[-16.5,0.012,-4.0],[0.15,6.0])
plane(z1,"AisleLine_2",M_YELLOW,[-14.5,0.012,-4.0],[0.15,6.0])
box(z1,"StrayPallet",M_WOOD,[-15.5,0.07,-4.0],[1.2,0.14,1.0])
box(z1,"StrayBox_1",M_BLUE,[-15.5,0.35,-4.0],[0.6,0.4,0.6])
box(z1,"StrayBox_2",M_RED,[-15.5,0.70,-4.1],[0.45,0.3,0.45])
box(z1,"DockPlatform",M_CONCRETE,[-19.0,0.15,0],[2.0,0.3,8.0])
box(z1,"DockBumper_1",M_RUBBER,[-18.0,0.3,-3.0],[0.2,0.4,0.6])
box(z1,"DockBumper_2",M_RUBBER,[-18.0,0.3,3.0],[0.2,0.4,0.6])

# ===== Zone 2: Vision QC (12,-8) =====
for (ox,oz,w,d) in [(12,-13.5,14,0.15),(12,-2.5,14,0.15),(5,-8,0.15,11),(19,-8,0.15,11)]:
    plane(z2,f"Border_{ox}_{oz}",M_YELLOW,[ox,0.012,oz],[w,d])
box(z2,"InspectConvFrame",M_WHITE,[12,0.75,-9],[5.0,0.25,0.9])
box(z2,"InspectBelt",M_ASTEEL,[12,0.90,-9],[5.0,0.05,0.8])
# parts: conforming (gray) + defective (red tint + crack)
cyl(z2,"Part_OK_1",M_ASTEEL,[10.5,1.02,-9],size=[0.3,0.18,0.3])
cyl(z2,"Part_OK_2",M_ASTEEL,[11.5,1.02,-9],size=[0.3,0.18,0.3])
cyl(z2,"Part_NOK_1",M_RED,[12.5,1.02,-9],size=[0.3,0.18,0.3])
box(z2,"Crack_1",M_DARK,[12.5,1.12,-9],[0.28,0.02,0.04])
box(z2,"Part_NOK_2",M_RED,[13.5,1.02,-9],size=[0.28,0.16,0.28])
box(z2,"MissingHoleMarker",M_DARK,[13.5,1.11,-9],[0.1,0.02,0.1])
# gantry + camera
box(z2,"GantryPost_L",M_DSTEEL,[12,1.1,-9.7],[0.15,2.2,0.15])
box(z2,"GantryPost_R",M_DSTEEL,[12,1.1,-8.3],[0.15,2.2,0.15])
box(z2,"GantryBeam",M_DSTEEL,[12,2.2,-9],[0.2,0.2,1.8])
box(z2,"VisionCamera",M_DARK,[12,2.0,-9],[0.35,0.25,0.35])
cyl(z2,"CameraLens",M_GLASS,[12,1.85,-9],size=[0.18,0.15,0.18])
box(z2,"Sensor_Left",M_RED,[11.6,1.9,-9],[0.12,0.08,0.12])
box(z2,"Sensor_Right",M_RED,[12.4,1.9,-9],[0.12,0.08,0.12])
box(z2,"ScanLight",M_HOLO,[12,1.3,-9],[0.7,0.5,0.7])
# inspection desk + instruments
box(z2,"DeskTop",M_WHITE,[12,0.85,-5.5],[1.8,0.08,0.9])
for lx,lz in [(11.2,-5.85),(12.8,-5.85),(11.2,-5.15),(12.8,-5.15)]:
    box(z2,f"DeskLeg_{lx}_{lz}",M_DSTEEL,[lx,0.42,lz],[0.08,0.85,0.08])
box(z2,"Caliper",M_ASTEEL,[11.6,0.92,-5.5],[0.3,0.03,0.06])
cyl(z2,"Gauge",M_WHITE,[12.3,0.95,-5.5],size=[0.15,0.06,0.15])
box(z2,"GaugeScreen",M_DARK,[12.3,0.99,-5.5],[0.1,0.02,0.08])
open_bin(z2,"BinConformes",M_GREEN,10.6,-5.5)
open_bin(z2,"BinRebuts",M_RED,13.4,-5.5)

# ===== Zone 3: Assembly (-12,8) =====
for (ox,oz,w,d) in [(-12,2.5,14,0.15),(-12,13.5,14,0.15),(-19,8,0.15,11),(-5,8,0.15,11)]:
    plane(z3,f"Border_{ox}_{oz}",M_YELLOW,[ox,0.012,oz],[w,d])
# safety fence 8x6 around cell center (-12,8)
fx0,fx1,fz0,fz1=-16,-8,5,11
for i,x in enumerate([-16,-14,-12,-10,-8]):
    for z in [5,11]:
        box(z3,f"FencePost_{i}_{z}",M_YELLOW,[x,0.9,z],[0.12,1.8,0.12])
for z in [5,11]:
    box(z3,f"FenceRail_Top_{z}",M_ORANGE,[-12,1.7,z],[8.2,0.08,0.08])
    box(z3,f"FencePanel_{z}",M_ORANGE,[-12,0.95,z],[8.2,1.3,0.04])
for x in [-16,-8]:
    box(z3,f"FenceRail_Top_X_{x}",M_ORANGE,[x,1.7,8],[0.08,0.08,6.2])
    box(z3,f"FencePanel_X_{x}",M_ORANGE,[x,0.95,8],[0.04,1.3,6.2])
box(z3,"SafetyGate",M_YELLOW,[-12,0.9,11],[1.5,1.7,0.08])
plane(z3,"SafetySign",M_YELLOW,[-12,1.4,10.9],[0.6,0.4])
# precision robot on pedestal
box(z3,"RobotPedestal",M_CONCRETE,[-13,0.25,8],[1.2,0.5,1.2])
cyl(z3,"ARobotBase",M_WHITE,[-13,0.65,8],size=[0.5,0.3,0.5])
box(z3,"ARobotColumn",M_WHITE,[-13,1.1,8],[0.3,0.6,0.3])
box(z3,"ARobotArm",M_ORANGE,[-13,1.5,7.5],[0.22,0.22,1.1],rot=euler_to_quat(25,0,0))
box(z3,"ARobotForearm",M_WHITE,[-13,1.65,6.8],[0.16,0.16,0.9],rot=euler_to_quat(-20,0,0))
box(z3,"GripperBase",M_DSTEEL,[-13,1.55,6.3],[0.2,0.12,0.2])
box(z3,"Finger_L",M_DSTEEL,[-13.08,1.42,6.3],[0.05,0.2,0.08])
box(z3,"Finger_R",M_DSTEEL,[-12.92,1.42,6.3],[0.05,0.2,0.08])
# storage magazine rack
box(z3,"RackFrame_L",M_DSTEEL,[-15.5,0.9,9.5],[0.1,1.8,0.6])
box(z3,"RackFrame_R",M_DSTEEL,[-13.5,0.9,9.5],[0.1,1.8,0.6])
for sy in [0.4,1.0,1.6]:
    box(z3,f"RackShelf_{sy}",M_ASTEEL,[-14.5,sy,9.5],[2.1,0.06,0.6])
    for k in range(3):
        cyl(z3,f"GearStock_{sy}_{k}",M_ASTEEL,[-15.2+k*0.7,sy+0.12,9.5],size=[0.25,0.12,0.25])
# staging tray + reducer kit
box(z3,"StagingTable",M_WHITE,[-11,0.8,9.0],[1.6,0.08,1.0])
for lx,lz in [(-11.7,8.6),(-10.3,8.6),(-11.7,9.4),(-10.3,9.4)]:
    box(z3,f"StageLeg_{lx}_{lz}",M_DSTEEL,[lx,0.4,lz],[0.08,0.8,0.08])
box(z3,"Tray",M_DSTEEL,[-11,0.88,9.0],[1.2,0.05,0.8])
box(z3,"ReducerHousing",M_ASTEEL,[-11.3,1.0,9.0],[0.4,0.2,0.3])
cyl(z3,"ReducerGear_1",M_ORANGE,[-10.8,1.0,8.9],size=[0.25,0.08,0.25])
cyl(z3,"ReducerGear_2",M_ASTEEL,[-10.8,1.0,9.2],size=[0.18,0.08,0.18])
cyl(z3,"ReducerShaft",M_DSTEEL,[-11.0,1.05,9.0],size=[0.06,0.35,0.06],rot=euler_to_quat(0,0,90))
# showcase
box(z3,"ShowPedestal",M_WHITE,[-9.5,0.4,7.0],[1.0,0.8,1.0])
box(z3,"ShowGlass",M_GLASS,[-9.5,1.2,7.0],[0.9,0.8,0.9])
box(z3,"ShowProduct",M_ORANGE,[-9.5,0.95,7.0],[0.4,0.25,0.3])
box(z3,"ShowBase",M_DSTEEL,[-9.5,0.83,7.0],[0.95,0.05,0.95])

# ===== Zone 4: Diagnosis (12,8) =====
for (ox,oz,w,d) in [(12,2.5,14,0.15),(12,13.5,14,0.15),(5,8,0.15,11),(19,8,0.15,11)]:
    plane(z4,f"Border_{ox}_{oz}",M_YELLOW,[ox,0.012,oz],[w,d])
# testing conveyor 4m + motor + sensors
box(z4,"TestConvFrame",M_DSTEEL,[12,0.70,9.0],[4.0,0.25,0.8])
box(z4,"TestBelt",M_RUBBER,[12,0.86,9.0],[4.0,0.05,0.7])
cyl(z4,"DriveMotor",M_ORANGE,[12,0.55,9.6],size=[0.4,0.5,0.4],rot=euler_to_quat(90,0,0))
box(z4,"MotorMount",M_DSTEEL,[12,0.3,9.6],[0.5,0.15,0.4])
box(z4,"SensorPost_1",M_DSTEEL,[11.0,1.0,8.5],[0.08,0.6,0.08])
box(z4,"SensorHead_1",M_RED,[11.0,1.3,8.6],[0.12,0.1,0.15])
box(z4,"SensorPost_2",M_DSTEEL,[13.0,1.0,9.5],[0.08,0.6,0.08])
box(z4,"SensorHead_2",M_RED,[13.0,1.3,9.4],[0.12,0.1,0.15])
box(z4,"TestPart",M_ASTEEL,[12,0.98,9.0],[0.4,0.18,0.4])
# electrical cabinet openable
box(z4,"CabBody_Back",M_CAB,[14.5,0.9,11.0],[0.9,1.8,0.08])
box(z4,"CabBody_Left",M_CAB,[14.08,0.9,11.25],[0.06,1.8,0.5])
box(z4,"CabBody_Right",M_CAB,[14.92,0.9,11.25],[0.06,1.8,0.5])
box(z4,"CabBody_Top",M_CAB,[14.5,1.83,11.25],[0.9,0.06,0.5])
box(z4,"CabBody_Bottom",M_CAB,[14.5,0.03,11.25],[0.9,0.06,0.5])
box(z4,"CabBackplate",M_WHITE,[14.5,0.9,11.05],[0.75,1.6,0.03])
# open door 90deg (hinged left)
box(z4,"CabDoor",M_CAB,[13.7,0.9,11.0],[0.06,1.75,0.85],rot=euler_to_quat(0,75,0))
# wiring + fuses
box(z4,"Wire_Red",M_RED,[14.5,1.3,11.08],[0.7,0.04,0.02])
box(z4,"Wire_Blue",M_BLUE,[14.5,1.15,11.08],[0.7,0.04,0.02])
box(z4,"Wire_Yellow",M_YELLOW,[14.5,1.0,11.08],[0.7,0.04,0.02])
for i in range(3):
    cyl(z4,f"Fuse_{i}",M_WHITE,[14.3+i*0.2,0.75,11.08],size=[0.08,0.15,0.08])
box(z4,"BreakerBox",M_DARK,[14.5,0.5,11.08],[0.5,0.3,0.1])
# spare parts magazine
box(z4,"SpareRack_L",M_DSTEEL,[10.0,0.9,11.0],[0.1,1.8,0.6])
box(z4,"SpareRack_R",M_DSTEEL,[12.0,0.9,11.0],[0.1,1.8,0.6])
for sy in [0.5,1.1,1.7]:
    box(z4,f"SpareShelf_{sy}",M_ASTEEL,[11.0,sy,11.0],[2.1,0.06,0.6])
box(z4,"SpareMotor",M_ORANGE,[10.6,0.68,11.0],[0.4,0.3,0.3])
box(z4,"SpareFuseBox",M_BLUE,[11.4,0.62,11.0],[0.35,0.18,0.3])
# workbench + multimeter
box(z4,"BenchTop",M_WOOD,[12,0.85,6.0],[1.8,0.08,0.8])
for lx,lz in [(11.2,5.7),(12.8,5.7),(11.2,6.3),(12.8,6.3)]:
    box(z4,f"BenchLeg_{lx}_{lz}",M_DSTEEL,[lx,0.42,lz],[0.08,0.85,0.08])
box(z4,"BenchVise",M_DSTEEL,[11.5,0.95,6.0],[0.25,0.15,0.2])
box(z4,"Multimeter",M_YELLOW,[12.4,0.95,6.0],[0.22,0.06,0.15])
box(z4,"MultimeterScreen",M_DARK,[12.4,0.985,6.0],[0.14,0.015,0.08])
cyl(z4,"Probe_Red",M_RED,[12.0,0.93,6.2],size=[0.03,0.15,0.03],rot=euler_to_quat(0,0,80))
cyl(z4,"Probe_Black",M_RUBBER,[12.1,0.93,6.25],size=[0.03,0.15,0.03],rot=euler_to_quat(0,0,80))

print(f"nodes={len(nodes)} meshes={len(meshes)} mats={len(materials)}")

# ---------------- build GLB ----------------
bin_chunks=[]
bufferViews=[]
accessors=[]
def push_data(arr):
    b = arr.tobytes()
    off = sum(len(c) for c in bin_chunks)
    # pad start to 4-byte
    pad = (-off) % 4
    if pad:
        bin_chunks.append(b"\x00"*pad); off+=pad
    bin_chunks.append(b)
    # pad end later handled globally; return offset/len
    return off, len(b)

# meshes -> primitives
gltf_meshes=[]
for m in meshes:
    P,N,UV,I = GEOMS[m["geom"]]
    o1,l1=push_data(P); o2,l2=push_data(N); o3,l3=push_data(UV); o4,l4=push_data(I)
    bv_base=len(bufferViews)
    bufferViews.append({"buffer":0,"byteOffset":o1,"byteLength":l1})
    bufferViews.append({"buffer":0,"byteOffset":o2,"byteLength":l2})
    bufferViews.append({"buffer":0,"byteOffset":o3,"byteLength":l3})
    bufferViews.append({"buffer":0,"byteOffset":o4,"byteLength":l4})
    a_base=len(accessors)
    accessors.append({"bufferView":bv_base,"componentType":5126,"count":len(P),"type":"VEC3",
        "min":[float(P[:,0].min()),float(P[:,1].min()),float(P[:,2].min())],
        "max":[float(P[:,0].max()),float(P[:,1].max()),float(P[:,2].max())]})
    accessors.append({"bufferView":bv_base+1,"componentType":5126,"count":len(N),"type":"VEC3"})
    accessors.append({"bufferView":bv_base+2,"componentType":5126,"count":len(UV),"type":"VEC2"})
    accessors.append({"bufferView":bv_base+3,"componentType":5123,"count":len(I),"type":"SCALAR"})
    gltf_meshes.append({"name":m["name"],"primitives":[{"attributes":{"POSITION":a_base,"NORMAL":a_base+1,"TEXCOORD_0":a_base+2},"indices":a_base+3,"material":m["mat"]}]})

bin_blob=b"".join(bin_chunks)
# pad blob to 4
if len(bin_blob)%4: bin_blob+=b"\x00"*(4-len(bin_blob)%4)
# fix bufferViews byteLength already ok; total buffer length
gltf={
 "asset":{"version":"2.0","generator":"RoboTeachVR-procgen","copyright":"RoboTeach VR"},
 "scene":0,
 "scenes":[{"name":"RoboTeachVR_Facility","nodes":[root]}],
 "nodes":[],
 "meshes":gltf_meshes,
 "materials":materials,
 "accessors":accessors,
 "bufferViews":bufferViews,
 "buffers":[{"byteLength":len(bin_blob)}]
}
for n in nodes:
    o={}
    o["name"]=n["name"]
    if "mesh" in n: o["mesh"]=n["mesh"]
    if "translation" in n: o["translation"]=n["translation"]
    if "scale" in n: o["scale"]=n["scale"]
    if "rotation" in n: o["rotation"]=n["rotation"]
    if n["children"]: o["children"]=n["children"]
    gltf["nodes"].append(o)

import os
out="/home/ameen/RobotTeachVr/RoboTeachVR.glb"
j=json.dumps(gltf,separators=(",",":")).encode()
if len(j)%4: j+=b" "*(4-len(j)%4)
total=12+8+len(j)+8+len(bin_blob)
with open(out,"wb") as f:
    f.write(struct.pack("<III",0x46546C67,2,total))
    f.write(struct.pack("<II",len(j),0x4E4F534A)); f.write(j)
    f.write(struct.pack("<II",len(bin_blob),0x004E4942)); f.write(bin_blob)
print("wrote",out,os.path.getsize(out),"bytes")
