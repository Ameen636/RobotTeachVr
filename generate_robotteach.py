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
# --- v3 detail materials: painted steel, brushed metal, carton, rubber tire,
# --- lens glass, skin/workwear for humanoids, shelf blue, copper, LCD screen
M_PAINT  = add_mat("PaintWhite", [0.87,0.88,0.90,1.0], 0.15, 0.35)
M_STEELL = add_mat("SteelLight", [0.68,0.70,0.73,1.0], 0.95, 0.30)
M_CARTON = add_mat("Carton", [0.64,0.49,0.31,1.0], 0.0, 0.85)
M_TAPE   = add_mat("PackTape", [0.80,0.74,0.60,1.0], 0.0, 0.55)
M_TIRE   = add_mat("Tire", [0.05,0.05,0.06,1.0], 0.0, 0.95)
M_LENS   = add_mat("LensGlass", [0.30,0.60,0.88,1.0], 0.1, 0.08, emissive=[0.08,0.20,0.35])
M_SKIN   = add_mat("Skin", [0.84,0.61,0.47,1.0], 0.0, 0.6)
M_PANTS  = add_mat("WorkPants", [0.15,0.19,0.27,1.0], 0.0, 0.8)
M_SILVER = add_mat("HiVisStripe", [0.75,0.77,0.78,1.0], 0.6, 0.4)
M_SHELFB = add_mat("ShelfBlue", [0.10,0.27,0.60,1.0], 0.4, 0.5)
M_COPPER = add_mat("Copper", [0.55,0.30,0.15,1.0], 1.0, 0.35)
M_LCD    = add_mat("LCDScreen", [0.45,0.62,0.48,1.0], 0.0, 0.4, emissive=[0.25,0.42,0.25])

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

# ---------- v3 detailed geometry (flat-shaded, auto-corrected winding) ----------
def _norm(v):
    v = np.array(v, float); n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v

def _push_poly(P, N, UV, I, pts, n):
    """pts: 3 or 4 verts. Flips winding so geometric normal matches n."""
    pts = [np.array(p, float) for p in pts]
    n = _norm(n)
    g = np.cross(pts[1] - pts[0], pts[2] - pts[0])
    if float(np.dot(g, n)) < 0:
        pts = [pts[0], pts[-1]] + list(reversed(pts[1:-1]))
    base = len(P)
    for p in pts:
        P.append(p); N.append(n)
    m = len(pts)
    UV.extend([[0, 0], [1, 0], [1, 1], [0, 1]][:m] if m == 4 else [[0.5, 0.5], [0, 0], [1, 0]])
    if m == 4:
        I.extend([base, base + 1, base + 2, base, base + 2, base + 3])
    else:
        I.extend([base, base + 1, base + 2])

def _push_poly4n(P, N, UV, I, pts, ns):
    """quad with per-vert smooth normals; flips winding to match avg normal."""
    pts = [np.array(p, float) for p in pts]
    ns = [_norm(n) for n in ns]
    avg = _norm(sum(ns))
    g = np.cross(pts[1] - pts[0], pts[2] - pts[0])
    if float(np.dot(g, avg)) < 0:
        pts = [pts[0], pts[3], pts[2], pts[1]]
        ns = [ns[0], ns[3], ns[2], ns[1]]
    base = len(P)
    for p, n in zip(pts, ns):
        P.append(p); N.append(n)
    UV.extend([[0, 0], [1, 0], [1, 1], [0, 1]])
    I.extend([base, base + 1, base + 2, base, base + 2, base + 3])

def make_bevelbox(c=0.07):
    """Unit 1x1x1 box with 45deg chamfered edges (6 faces + 12 bevels + 8 corners)."""
    P, N, UV, I = [], [], [], []
    a = 0.5 - c
    S = 1.0 / math.sqrt(2.0)
    # faces
    _push_poly(P, N, UV, I, [(0.5, -a, -a), (0.5, -a, a), (0.5, a, a), (0.5, a, -a)], (1, 0, 0))
    _push_poly(P, N, UV, I, [(-0.5, -a, a), (-0.5, -a, -a), (-0.5, a, -a), (-0.5, a, a)], (-1, 0, 0))
    _push_poly(P, N, UV, I, [(-a, 0.5, -a), (-a, 0.5, a), (a, 0.5, a), (a, 0.5, -a)], (0, 1, 0))
    _push_poly(P, N, UV, I, [(-a, -0.5, a), (-a, -0.5, -a), (a, -0.5, -a), (a, -0.5, a)], (0, -1, 0))
    _push_poly(P, N, UV, I, [(-a, -a, 0.5), (a, -a, 0.5), (a, a, 0.5), (-a, a, 0.5)], (0, 0, 1))
    _push_poly(P, N, UV, I, [(a, -a, -0.5), (-a, -a, -0.5), (-a, a, -0.5), (a, a, -0.5)], (0, 0, -1))
    # 12 edge bevels
    for sx in (-1, 1):
        for sy in (-1, 1):
            _push_poly(P, N, UV, I, [(sx * 0.5, sy * a, -a), (sx * 0.5, sy * a, a),
                                     (sx * a, sy * 0.5, a), (sx * a, sy * 0.5, -a)], (sx * S, sy * S, 0))
            _push_poly(P, N, UV, I, [(sx * 0.5, -a, sy * a), (sx * 0.5, a, sy * a),
                                     (sx * a, a, sy * 0.5), (sx * a, -a, sy * 0.5)], (sx * S, 0, sy * S))
    for sy in (-1, 1):
        for sz in (-1, 1):
            _push_poly(P, N, UV, I, [(-a, sy * 0.5, sz * a), (a, sy * 0.5, sz * a),
                                     (a, sy * a, sz * 0.5), (-a, sy * a, sz * 0.5)], (0, sy * S, sz * S))
    # 8 corners
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                _push_poly(P, N, UV, I, [(sx * 0.5, sy * a, sz * a), (sx * a, sy * 0.5, sz * a),
                                         (sx * a, sy * a, sz * 0.5)], (sx, sy, sz))
    return (np.array(P, np.float32), np.array(N, np.float32),
            np.array(UV, np.float32), np.array(I, np.uint16))

def make_taperbox(top=0.62):
    """Unit box, top face scaled to `top` (tapered machine links)."""
    P, N, UV, I = [], [], [], []
    b, t = 0.5, 0.5 * top
    s = 1.0 - top  # slope over unit height
    nX = _norm((1, s, 0)); nZ = _norm((0, s, 1))
    _push_poly(P, N, UV, I, [(b, -0.5, -b), (b, -0.5, b), (t, 0.5, t), (t, 0.5, -t)], nX)
    _push_poly(P, N, UV, I, [(-b, -0.5, b), (-b, -0.5, -b), (-t, 0.5, -t), (-t, 0.5, t)], -nX)
    _push_poly(P, N, UV, I, [(-b, -0.5, b), (b, -0.5, b), (t, 0.5, t), (-t, 0.5, t)], nZ)
    _push_poly(P, N, UV, I, [(b, -0.5, -b), (-b, -0.5, -b), (-t, 0.5, -t), (t, 0.5, -t)], -nZ)
    _push_poly(P, N, UV, I, [(-t, 0.5, -t), (-t, 0.5, t), (t, 0.5, t), (t, 0.5, -t)], (0, 1, 0))
    _push_poly(P, N, UV, I, [(-b, -0.5, b), (-b, -0.5, -b), (b, -0.5, -b), (b, -0.5, b)], (0, -1, 0))
    return (np.array(P, np.float32), np.array(N, np.float32),
            np.array(UV, np.float32), np.array(I, np.uint16))

def make_sphere(lon=14, lat=9):
    P, N, UV, I = [], [], [], []
    for j in range(lat + 1):
        th = math.pi * j / lat
        for i in range(lon + 1):
            ph = 2 * math.pi * i / lon
            p = [0.5 * math.sin(th) * math.cos(ph), 0.5 * math.cos(th), 0.5 * math.sin(th) * math.sin(ph)]
            P.append(p); N.append(_norm(p)); UV.append([i / lon, j / lat])
    for j in range(lat):
        for i in range(lon):
            a = j * (lon + 1) + i; b = a + 1; c = a + lon + 1; d = c + 1
            I.extend([a, c, b, b, c, d])
    return (np.array(P, np.float32), np.array(N, np.float32),
            np.array(UV, np.float32), np.array(I, np.uint16))

def make_gear(teeth=12, thick=0.22):
    """Unit spur gear: outer r=0.5, root r=0.40, flat shaded."""
    P, N, UV, I = [], [], [], []
    Rout, Rroot, h = 0.5, 0.40, thick / 2
    prof = []
    for k in range(teeth):
        a0 = 2 * math.pi * k / teeth
        for f, r in ((0.00, Rroot), (0.18, Rroot), (0.30, Rout), (0.55, Rout), (0.67, Rroot)):
            a = a0 + f * 2 * math.pi / teeth
            prof.append((r * math.cos(a), r * math.sin(a)))
    n = len(prof)
    for i in range(n):
        (x0, z0), (x1, z1) = prof[i], prof[(i + 1) % n]
        nm = _norm(((x0 + x1) / 2, 0, (z0 + z1) / 2))
        _push_poly(P, N, UV, I, [(x0, -h, z0), (x1, -h, z1), (x1, h, z1), (x0, h, z0)], nm)
    top_c = len(P); P.append([0, h, 0]); N.append([0, 1, 0]); UV.append([0.5, 0.5])
    bot_c = len(P); P.append([0, -h, 0]); N.append([0, -1, 0]); UV.append([0.5, 0.5])
    top_ring, bot_ring = [], []
    for (x, z) in prof:
        top_ring.append(len(P)); P.append([x, h, z]); N.append([0, 1, 0]); UV.append([0.5 + x, 0.5 + z])
        bot_ring.append(len(P)); P.append([x, -h, z]); N.append([0, -1, 0]); UV.append([0.5 + x, 0.5 + z])
    for i in range(n):
        j = (i + 1) % n
        I.extend([top_c, top_ring[i], top_ring[j]])
        I.extend([bot_c, bot_ring[j], bot_ring[i]])
    return (np.array(P, np.float32), np.array(N, np.float32),
            np.array(UV, np.float32), np.array(I, np.uint16))

def make_tube(points, radius=0.02, radial=7):
    """Round cable/hose swept along a polyline. points in local units."""
    pts = [np.array(p, float) for p in points]
    P, N, UV, I = [], [], [], []
    up = np.array([0.0, 1.0, 0.0])
    rings = []
    for k, p in enumerate(pts):
        t = _norm(pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)])
        side = np.cross(t, up)
        if np.linalg.norm(side) < 1e-6:
            side = np.array([1.0, 0.0, 0.0])
        side = _norm(side); upv = _norm(np.cross(side, t))
        ring, nr = [], []
        for i in range(radial):
            a = 2 * math.pi * i / radial
            d = side * math.cos(a) + upv * math.sin(a)
            ring.append(p + radius * d); nr.append(d)
        rings.append((ring, nr))
    for k in range(len(pts)):
        for i in range(radial):
            P.append(rings[k][0][i]); N.append(rings[k][1][i]); UV.append([i / radial, k / max(1, len(pts) - 1)])
    for k in range(len(pts) - 1):
        for i in range(radial):
            a = k * radial + i; b = k * radial + (i + 1) % radial
            c = (k + 1) * radial + i; d = (k + 1) * radial + (i + 1) % radial
            _push_poly4n(P, N, UV, I, [P[a], P[b], P[d], P[c]],
                         [N[a], N[b], N[d], N[c]])
    return (np.array(P, np.float32), np.array(N, np.float32),
            np.array(UV, np.float32), np.array(I, np.uint16))

GEOMS["BBOX"] = make_bevelbox()
GEOMS["TBOX"] = make_taperbox()
GEOMS["SPH"] = make_sphere()
GEOMS["GEAR12"] = make_gear(12)
GEOMS["GEAR10"] = make_gear(10, thick=0.3)

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
def bbox(parent, name, mat, pos, size, rot=None):
    """Chamfered box — default for visible machine housings."""
    return add_node(name, parent, mesh_id("BBOX",mat,f"{name}_m"), t=pos, s=size, r=rot)
def tbox(parent, name, mat, pos, size, rot=None):
    """Tapered link (bottom full, top 62%) — robot arm segments."""
    return add_node(name, parent, mesh_id("TBOX",mat,f"{name}_m"), t=pos, s=size, r=rot)
def sph(parent, name, mat, pos, size, rot=None, geom="SPH"):
    if isinstance(size, (int, float)): size = [size, size, size]
    return add_node(name, parent, mesh_id(geom,mat,f"{name}_m"), t=pos, s=size, r=rot)
def gear(parent, name, mat, pos, dia, thick, rot=None, teeth=12):
    g = f"GEAR{teeth}"
    return add_node(name, parent, mesh_id(g,mat,f"{name}_m"), t=pos, s=[dia,thick / 0.22,dia], r=rot)
def tube(parent, name, mat, points, radius):
    key = f"TUBE_{name}"
    if key not in GEOMS:
        GEOMS[key] = make_tube(points, radius)
    return add_node(name, parent, mesh_id(key,mat,f"{name}_m"))

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

# ============ v3 machine builders (nested pivots, chamfered parts) ============
def robot_arm(parent, name, x, z, ry, paint, dark=M_DSTEEL, scale=1.0, tool_disc=False):
    """Articulated arm with true joint hierarchy, reaching toward local -Z."""
    s = scale
    g = add_node(name, parent, t=[x, 0, z], r=euler_to_quat(0, ry, 0))
    cyl(g, name+"_Anchor", dark, [0, 0.05, 0], size=[0.62 * s, 0.10 * s, 0.62 * s])
    for bx, bz in ((-0.24, -0.24), (0.24, -0.24), (-0.24, 0.24), (0.24, 0.24)):
        sph(g, name+f"_Bolt_{bx}_{bz}", dark, [bx * s, 0.11 * s, bz * s], 0.05 * s)
    cyl(g, name+"_TurretRing", dark, [0, 0.13 * s, 0], size=[0.48 * s, 0.07 * s, 0.48 * s])
    cyl(g, name+"_Turret", paint, [0, 0.30 * s, 0], size=[0.44 * s, 0.28 * s, 0.44 * s])
    sph(g, name+"_TurretCapL", paint, [-0.20 * s, 0.36 * s, 0], 0.13 * s)
    sph(g, name+"_TurretCapR", paint, [0.20 * s, 0.36 * s, 0], 0.13 * s)
    j1 = add_node(name+"_J1_Waist", g, t=[0, 0.44 * s, 0], r=euler_to_quat(0, 18, 0))
    bbox(j1, name+"_ShoulderBlock", paint, [0, 0.10 * s, 0], [0.34 * s, 0.30 * s, 0.30 * s])
    cyl(j1, name+"_ShoulderAxle", dark, [0, 0.16 * s, 0], size=[0.20 * s, 0.40 * s, 0.20 * s],
        rot=euler_to_quat(0, 0, 90))
    sph(j1, name+"_ShoulderCapL", paint, [-0.20 * s, 0.16 * s, 0], 0.12 * s)
    sph(j1, name+"_ShoulderCapR", paint, [0.20 * s, 0.16 * s, 0], 0.12 * s)
    j2 = add_node(name+"_J2_Shoulder", j1, t=[0, 0.20 * s, 0], r=euler_to_quat(-28, 0, 0))
    tbox(j2, name+"_UpperArm", paint, [0, 0.42 * s, 0], [0.26 * s, 0.85 * s, 0.22 * s])
    bbox(j2, name+"_UpperArmCollar", dark, [0, 0.06 * s, 0], [0.28 * s, 0.10 * s, 0.24 * s])
    sph(j2, name+"_ElbowCapL", paint, [-0.11 * s, 0.85 * s, 0], 0.11 * s)
    sph(j2, name+"_ElbowCapR", paint, [0.11 * s, 0.85 * s, 0], 0.11 * s)
    j3 = add_node(name+"_J3_Elbow", j2, t=[0, 0.85 * s, 0], r=euler_to_quat(55, 0, 0))
    cyl(j3, name+"_ElbowAxle", dark, [0, 0, 0], size=[0.16 * s, 0.24 * s, 0.16 * s],
        rot=euler_to_quat(0, 0, 90))
    tbox(j3, name+"_Forearm", paint, [0, 0.36 * s, 0], [0.18 * s, 0.75 * s, 0.16 * s])
    bbox(j3, name+"_ForearmCollar", dark, [0, 0.10 * s, 0], [0.20 * s, 0.08 * s, 0.18 * s])
    j4 = add_node(name+"_J4_Wrist", j3, t=[0, 0.74 * s, 0], r=euler_to_quat(-32, 0, 0))
    cyl(j4, name+"_WristBody", dark, [0, 0.09 * s, 0], size=[0.14 * s, 0.20 * s, 0.14 * s])
    cyl(j4, name+"_Flange", M_STEELL, [0, 0.21 * s, 0], size=[0.17 * s, 0.05 * s, 0.17 * s])
    for k, fa in enumerate((45, 135, 225, 315)):
        fr = math.radians(fa)
        cyl(j4, name+f"_FlangeBolt{k}", dark,
            [0.06 * s * math.cos(fr), 0.235 * s, 0.06 * s * math.sin(fr)],
            size=[0.025 * s, 0.03 * s, 0.025 * s], geom="CYL8")
    if tool_disc:
        cyl(j4, name+"_ToolChanger", M_ASTEEL, [0, 0.27 * s, 0], size=[0.19 * s, 0.07 * s, 0.19 * s])
        y0 = 0.32 * s
    else:
        y0 = 0.25 * s
    bbox(j4, name+"_Palm", dark, [0, y0 + 0.05 * s, 0], [0.17 * s, 0.10 * s, 0.11 * s])
    for sx in (-1, 1):
        fg = add_node(name+f"_Finger_{'L' if sx < 0 else 'R'}", j4,
                      t=[sx * 0.070 * s, y0 + 0.10 * s, 0], r=euler_to_quat(0, 0, sx * -7))
        bbox(fg, name+f"_Phalanx_{sx}", M_ASTEEL, [0, 0.09 * s, 0], [0.045 * s, 0.18 * s, 0.07 * s])
        bbox(fg, name+f"_TipPad_{sx}", M_RUBBER, [sx * -0.008 * s, 0.16 * s, -0.035 * s],
             [0.02 * s, 0.12 * s, 0.03 * s], rot=euler_to_quat(18, 0, 0))
    return g

def motor_unit(parent, name, x, y, z, dia=0.34, length=0.5, ry=0, mount=True):
    """Finned TEFC motor: feet, stator + cooling fins, fan cowl, terminal box, shaft."""
    g = add_node(name, parent, t=[x, y, z], r=euler_to_quat(0, ry, 0))
    if mount:
        box(g, name+"_RailL", M_DSTEEL, [-0.10, -dia * 0.42, 0], [0.08, 0.10, length * 1.1])
        box(g, name+"_RailR", M_DSTEEL, [0.10, -dia * 0.42, 0], [0.08, 0.10, length * 1.1])
    box(g, name+"_FootL", M_DSTEEL, [-dia * 0.32, -dia * 0.30, 0], [0.07, 0.12, length * 0.7])
    box(g, name+"_FootR", M_DSTEEL, [dia * 0.32, -dia * 0.30, 0], [0.07, 0.12, length * 0.7])
    cyl(g, name+"_Stator", M_ORANGE, [0, 0, 0], size=[dia, length, dia],
        rot=euler_to_quat(90, 0, 0))
    for k in range(6):
        a = math.pi * k / 6
        fin = add_node(name+f"_Fin{k}", g, t=[dia * 0.48 * math.cos(a), 0, dia * 0.48 * math.sin(a)],
                       r=euler_to_quat(0, -math.degrees(a), 0))
        box(fin, name+f"_FinB{k}", M_ORANGE, [0, 0, 0], [0.025, length * 0.9, 0.06])
    cyl(g, name+"_FanCowl", M_DSTEEL, [0, 0, length * 0.58], size=[dia * 0.96, length * 0.22, dia * 0.96],
        rot=euler_to_quat(90, 0, 0))
    cyl(g, name+"_DriveEnd", M_DSTEEL, [0, 0, -length * 0.55], size=[dia * 0.8, length * 0.14, dia * 0.8],
        rot=euler_to_quat(90, 0, 0))
    cyl(g, name+"_Shaft", M_STEELL, [0, 0, -length * 0.72], size=[dia * 0.28, length * 0.24, dia * 0.28],
        rot=euler_to_quat(90, 0, 0))
    bbox(g, name+"_TerminalBox", M_DSTEEL, [0, dia * 0.58, length * 0.05], [0.20, 0.14, 0.24])
    return g

def conveyor_line(parent, prefix, cx, cz, length, belt_y=0.90, frame_mat=M_DSTEEL,
                  belt_mat=M_RUBBER, rail=True, motor=True):
    """Roller/belt conveyor: channels, legs+feet, rollers, drums, rails, drive, photoeyes."""
    g = add_node(prefix, parent, t=[cx, 0, cz])
    for sz in (-1, 1):
        bbox(g, prefix+"_Channel", frame_mat, [0, belt_y - 0.13, sz * 0.46], [length, 0.24, 0.10])
    for i in (-1, 0, 1):
        box(g, prefix+f"_Cross{i}", frame_mat, [i * length * 0.32, belt_y - 0.22, 0], [0.10, 0.08, 0.86])
    nlegs = max(2, int(length / 1.6) + 1)
    for i in range(nlegs):
        lx = -length / 2 + 0.25 + i * (length - 0.5) / max(1, nlegs - 1)
        for sz in (-1, 1):
            box(g, prefix+f"_Leg{i}{sz}", frame_mat, [lx, (belt_y - 0.25) / 2, sz * 0.40],
                [0.10, belt_y - 0.25, 0.10])
            box(g, prefix+f"_Foot{i}{sz}", frame_mat, [lx, 0.02, sz * 0.40], [0.26, 0.04, 0.26])
            cyl(g, prefix+f"_Pad{i}{sz}", M_RUBBER, [lx, 0.055, sz * 0.40],
                size=[0.09, 0.035, 0.09], geom="CYL8")
    nroll = int(length / 0.42)
    for i in range(nroll):
        lx = -length / 2 + 0.25 + i * 0.42
        cyl(g, prefix+f"_Roller{i}", M_STEELL, [lx, belt_y - 0.015, 0],
            size=[0.09, 0.86, 0.09], rot=euler_to_quat(90, 0, 0))
    for ex in (-1, 1):
        cyl(g, prefix+f"_Drum{ex}", M_DSTEEL, [ex * (length / 2 - 0.08), belt_y - 0.01, 0],
            size=[0.14, 0.88, 0.14], rot=euler_to_quat(90, 0, 0))
    box(g, prefix+"_Belt", belt_mat, [0, belt_y + 0.035, 0], [length - 0.1, 0.035, 0.84])
    if rail:
        for sz in (-1, 1):
            box(g, prefix+f"_Rail{sz}", M_STEELL, [0, belt_y + 0.30, sz * 0.52], [length - 0.4, 0.045, 0.045])
            for px in (-length / 2 + 0.6, 0, length / 2 - 0.6):
                box(g, prefix+f"_RailPost{sz}{px}", M_DSTEEL, [px, belt_y + 0.16, sz * 0.52],
                    [0.05, 0.24, 0.05])
    if motor:
        mu = motor_unit(g, prefix+"_Drive", length / 2 - 0.55, belt_y - 0.42, 0.0,
                        dia=0.26, length=0.42, ry=90)
        bbox(g, prefix+"_Gearbox", M_PAINT, [length / 2 - 0.55, belt_y - 0.18, 0.0], [0.30, 0.24, 0.24])
    for ex, px in (("W", -length / 2 + 0.9), ("E", length / 2 - 0.9)):
        box(g, prefix+f"_EyePost{ex}", M_DSTEEL, [px, belt_y + 0.28, -0.52], [0.06, 0.5, 0.06])
        bbox(g, prefix+f"_EyeHead{ex}", M_DSTEEL, [px, belt_y + 0.52, -0.48], [0.10, 0.09, 0.14])
        sph(g, prefix+f"_EyeLens{ex}", M_RED, [px, belt_y + 0.52, -0.40], 0.035)
    return g

def carton(parent, name, mat, x, y, z, s=0.4, ry=0):
    g = add_node(name, parent, t=[x, y, z], r=euler_to_quat(0, ry, 0))
    bbox(g, name+"_Body", mat, [0, 0, 0], [s, s * 0.75, s])
    box(g, name+"_Tape", M_TAPE, [0, s * 0.375 + 0.004, 0], [s * 1.002, 0.012, s * 0.22])
    plane(g, name+"_Label", M_WHITE, [s * 0.1, 0, s * 0.5 + 0.002], [s * 0.4, s * 0.3])
    nodes[-1]["rotation"] = euler_to_quat(90, 0, 0)
    return g

def pallet_stack(parent, name, x, z, ry=0, cartons=0, cmat=M_CARTON):
    g = add_node(name, parent, t=[x, 0, z], r=euler_to_quat(0, ry, 0))
    for sz in (-0.45, 0, 0.45):
        box(g, name+"_Stringer", M_WOOD, [0, 0.10, sz], [1.2, 0.09, 0.12])
    for i in range(5):
        box(g, name+f"_Slat{i}", M_WOOD, [-0.5 + i * 0.25, 0.175, 0], [0.20, 0.035, 1.1])
    for i, cm in enumerate(cartons if isinstance(cartons, list) else [cmat] * cartons):
        carton(g, name+f"_Box{i}", cm, -0.25 + 0.5 * (i % 2), 0.19 + 0.38 + 0.36 * (i // 2), 0,
               s=0.48, ry=5 * i)
    return g

def shelving(parent, name, x, z, ry=0, w=2.1, h=1.8, d=0.6, levels=(0.4, 1.0, 1.6)):
    g = add_node(name, parent, t=[x, 0, z], r=euler_to_quat(0, ry, 0))
    for sx in (-1, 1):
        for sz in (-1, 1):
            box(g, name+"_Upright", M_SHELFB, [sx * (w / 2 - 0.05), h / 2, sz * (d / 2 - 0.05)],
                [0.10, h, 0.10])
            box(g, name+"_FootPl", M_SHELFB, [sx * (w / 2 - 0.05), 0.02, sz * (d / 2 - 0.05)],
                [0.22, 0.04, 0.22])
    for lv in levels:
        for sz in (-1, 1):
            box(g, name+f"_Beam{lv}{sz}", M_ORANGE, [0, lv, sz * (d / 2 - 0.05)], [w, 0.12, 0.08])
        box(g, name+f"_Deck{lv}", M_STEELL, [0, lv - 0.075, 0], [w - 0.1, 0.03, d - 0.1])
    for k, s in enumerate((1, -1)):
        brace = add_node(name+f"_Brace{k}", g, t=[0, h / 2, -s * (d / 2 - 0.02)],
                         r=euler_to_quat(0, 0, s * 38))
        box(brace, name+f"_BraceB{k}", M_SHELFB, [0, 0, 0], [0.07, h * 1.05, 0.05])
    return g

def humanoid(parent, name, x, z, ry, vest, helmet):
    """Recognizable worker: boots, legs, hi-vis torso+stripes, arms, head+hard hat."""
    g = add_node(name, parent, t=[x, 0, z], r=euler_to_quat(0, ry, 0))
    for sx in (-1, 1):
        bbox(g, name+f"_Boot{sx}", M_TIRE, [sx * 0.11, 0.06, 0.02], [0.13, 0.12, 0.26])
        cyl(g, name+f"_Leg{sx}", M_PANTS, [sx * 0.11, 0.45, 0], size=[0.14, 0.66, 0.14])
        ag = add_node(name+f"_Arm{sx}", g, t=[sx * 0.26, 1.32, 0], r=euler_to_quat(6, 0, sx * -4))
        cyl(ag, name+f"_Sleeve{sx}", vest, [0, -0.16, 0], size=[0.11, 0.32, 0.11])
        cyl(ag, name+f"_Forearm{sx}", M_SKIN, [0, -0.44, 0.01], size=[0.09, 0.28, 0.09])
        sph(ag, name+f"_Hand{sx}", M_SKIN, [0, -0.62, 0.02], 0.10)
    bbox(g, name+"_Hips", M_PANTS, [0, 0.85, 0], [0.34, 0.18, 0.22])
    bbox(g, name+"_Torso", vest, [0, 1.15, 0], [0.40, 0.48, 0.25])
    box(g, name+"_StripeF", M_SILVER, [0, 1.18, 0.13], [0.41, 0.07, 0.012])
    box(g, name+"_StripeB", M_SILVER, [0, 1.18, -0.13], [0.41, 0.07, 0.012])
    sph(g, name+"_Head", M_SKIN, [0, 1.55, 0.01], 0.24)
    sph(g, name+"_Helmet", helmet, [0, 1.63, 0.0], [0.27, 0.17, 0.27])
    cyl(g, name+"_Brim", helmet, [0, 1.585, 0.0], size=[0.32, 0.03, 0.32])
    return g

# ===== Zone 1: Warehouse (-12,-8) =====
# zone floor border
for (ox,oz,w,d) in [(-12,-13.5,14,0.15),(-12,-2.5,14,0.15),(-19,-8,0.15,11),(-5,-8,0.15,11)]:
    plane(z1,f"Border_{ox}_{oz}",M_YELLOW,[ox,0.012,oz],[w,d])
# conveyor line 6m along X at (-12,0,-9): channels, legs, rollers, rails, drive
conveyor_line(z1, "ConvLine", -12, -9, 6.0, belt_y=0.90)
# feeder hopper at west end: rim + slanted throat + legs + outlet chute
fh = add_node("FeederHopper", z1, t=[-15.4, 0, -9])
box(fh, "FeederHopper_RimN", M_ASTEEL, [0, 1.62, -0.55], [1.0, 0.08, 0.08])
box(fh, "FeederHopper_RimS", M_ASTEEL, [0, 1.62, 0.55], [1.0, 0.08, 0.08])
box(fh, "FeederHopper_RimW", M_ASTEEL, [-0.5, 1.62, 0], [0.08, 0.08, 1.1])
box(fh, "FeederHopper_RimE", M_ASTEEL, [0.5, 1.62, 0], [0.08, 0.08, 1.1])
for sx, sz, rx, rz in ((0, -1, -22, 0), (0, 1, 22, 0), (-1, 0, 0, 22), (1, 0, 0, -22)):
    bbox(fh, f"FeederHopper_Panel{sx}{sz}", M_PAINT, [sx * 0.28, 1.15, sz * 0.28],
         [0.85 if sx == 0 else 0.06, 0.75, 0.85 if sz == 0 else 0.06],
         rot=euler_to_quat(rx, 0, rz))
bbox(fh, "FeederHopper_Throat", M_DSTEEL, [0, 0.72, 0], [0.4, 0.25, 0.4])
for lx, lz in ((-0.4, -0.4), (0.4, -0.4), (-0.4, 0.4), (0.4, 0.4)):
    box(fh, f"FeederHopper_Leg{lx}{lz}", M_DSTEEL, [lx, 0.35, lz], [0.09, 0.7, 0.09])
box(fh, "FeederHopper_Chute", M_DSTEEL, [0.55, 0.95, 0], [0.6, 0.12, 0.7])
# parcels on belt (taped cartons, mixed sizes)
carton(z1, "Parcel_1", M_CARTON, -13.8, 1.12, -9.0, s=0.42, ry=4)
carton(z1, "Parcel_2", M_BLUE, -13.0, 1.09, -9.1, s=0.36, ry=-6)
carton(z1, "Parcel_3", M_CARTON, -12.2, 1.14, -8.9, s=0.46, ry=9)
carton(z1, "Parcel_4", M_WHITE, -11.3, 1.06, -9.0, s=0.32, ry=-3)
carton(z1, "Parcel_5", M_RED, -10.4, 1.10, -9.05, s=0.40, ry=7)
# articulated sorting arm south of conveyor, reaching toward the belt
robot_arm(z1, "SortArm", -12, -7.3, 0, M_ORANGE, scale=1.1)
# sorting bins
def open_bin(parent,name,mat,x,z,label=None):
    g = add_node(name, parent, t=[x,0,z])
    bbox(g,f"{name}_Bottom",mat,[0,0.18,0],[0.9,0.10,0.7])
    bbox(g,f"{name}_W1",mat,[0,0.48,-0.32],[0.9,0.62,0.06])
    bbox(g,f"{name}_W2",mat,[0,0.48,0.32],[0.9,0.62,0.06])
    bbox(g,f"{name}_W3",mat,[-0.42,0.48,0],[0.06,0.62,0.7])
    bbox(g,f"{name}_W4",mat,[0.42,0.48,0],[0.06,0.62,0.7])
    box(g,f"{name}_Rim",M_DSTEEL,[0,0.80,0],[0.96,0.05,0.76])
    plane(g,f"{name}_Label",M_WHITE,[0,0.5,0.36],[0.4,0.25])
    nodes[-1]["rotation"] = euler_to_quat(90,0,0)
    for cx,cz in ((-0.36,-0.26),(0.36,-0.26),(-0.36,0.26),(0.36,0.26)):
        cyl(g,f"{name}_Caster{cx}{cz}",M_TIRE,[cx,0.06,cz],size=[0.11,0.09,0.11],geom="CYL8")
open_bin(z1,"BinA",M_BLUE,-10.5,-5.5)
open_bin(z1,"BinB",M_GREEN,-12.0,-5.5)
open_bin(z1,"BinFull",M_RED,-13.5,-5.5)
box(z1,"BinFull_Lid",M_DSTEEL,[-13.5,0.78,-5.5],[0.95,0.06,0.75])
# AGV: chassis + striped bumper, deck, wheels, lidar, e-stop, lamp stack
ag = add_node("AGV", z1, t=[-8.5, 0, -6.0])
bbox(ag, "AGV_Chassis", M_DSTEEL, [0, 0.24, 0], [1.2, 0.16, 0.8])
bbox(ag, "AGV_Bumper", M_YELLOW, [0, 0.17, -0.44], [1.24, 0.12, 0.10])
for i, bx in enumerate((-0.4, -0.13, 0.13, 0.4)):
    box(ag, f"AGV_Stripe{i}", M_TIRE, [bx, 0.17, -0.495], [0.13, 0.12, 0.012])
bbox(ag, "AGV_Deck", M_STEELL, [0, 0.35, 0.02], [1.0, 0.06, 0.7])
for wx, wz in ((-0.42, -0.30), (0.42, -0.30), (-0.42, 0.30), (0.42, 0.30)):
    cyl(ag, f"AGV_Wheel{wx}{wz}", M_TIRE, [wx, 0.11, wz], size=[0.22, 0.09, 0.22],
        rot=euler_to_quat(90, 0, 0))
    cyl(ag, f"AGV_Hub{wx}{wz}", M_STEELL, [wx, 0.11, wz], size=[0.10, 0.10, 0.10],
        rot=euler_to_quat(90, 0, 0))
sph(ag, "AGV_CasterF", M_DSTEEL, [0, 0.06, -0.36], 0.09)
sph(ag, "AGV_CasterR", M_DSTEEL, [0, 0.06, 0.36], 0.09)
cyl(ag, "AGV_LidarMast", M_DSTEEL, [-0.35, 0.50, 0.25], size=[0.07, 0.24, 0.07])
cyl(ag, "AGV_Lidar", M_DSTEEL, [-0.35, 0.65, 0.25], size=[0.16, 0.12, 0.16])
cyl(ag, "AGV_LidarBand", M_LENS, [-0.35, 0.65, 0.25], size=[0.165, 0.045, 0.165])
cyl(ag, "AGV_EstopBase", M_YELLOW, [0.35, 0.40, 0.25], size=[0.07, 0.04, 0.07])
sph(ag, "AGV_Estop", M_RED, [0.35, 0.44, 0.25], 0.055)
cyl(ag, "AGV_LampPole", M_DSTEEL, [0.45, 0.55, -0.30], size=[0.04, 0.40, 0.04])
cyl(ag, "AGV_LampR", M_RED, [0.45, 0.78, -0.30], size=[0.09, 0.09, 0.09])
cyl(ag, "AGV_LampG", M_GREEN, [0.45, 0.68, -0.30], size=[0.09, 0.09, 0.09])
bbox(ag, "AGV_Scanner", M_DSTEEL, [0, 0.13, -0.50], [0.5, 0.07, 0.08])
box(ag, "AGV_ScanLens", M_LENS, [0, 0.13, -0.545], [0.44, 0.04, 0.012])
carton(ag, "AGV_Parcel", M_CARTON, 0.05, 0.60, -0.02, s=0.5, ry=-4)
# aisle + stray pallet blocking path to dock
plane(z1,"AisleLine_1",M_YELLOW,[-16.5,0.012,-4.0],[0.15,6.0])
plane(z1,"AisleLine_2",M_YELLOW,[-14.5,0.012,-4.0],[0.15,6.0])
pallet_stack(z1, "StrayPallet", -15.5, -4.0, ry=3, cartons=[M_BLUE, M_RED])
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

M_BEIGE = add_mat("PanelBeige", [0.82,0.76,0.66,1.0], 0.0, 0.6)
M_FLOORTINT = add_mat("FloorTint", [0.58,0.58,0.60,1.0], 0.0, 0.9)
M_STRIPE = M_RUBBER  # black stripes reuse rubber

def ao_skirt(parent, name, x, z, w, d):
    box(parent, name+"_AO", M_DARK, [x,0.012,z], [w+0.3,0.025,d+0.3])

def hazard_strip(parent, name, x, z, n=6, along_x=True):
    for i in range(n):
        mat = M_YELLOW if i%2==0 else M_STRIPE
        off = (i-n/2)*0.32
        if along_x: plane(parent, f"{name}_{i}", mat, [x+off,0.015,z], [0.3,0.6])
        else: plane(parent, f"{name}_{i}", mat, [x,0.015,z+off], [0.6,0.3])

def totem(parent, name, mat, x, z):
    box(parent, name+"_Pole", M_DSTEEL, [x,1.0,z], [0.12,2.0,0.12])
    box(parent, name+"_Head", mat, [x,2.1,z], [0.7,0.5,0.15])
    box(parent, name+"_Glow", M_LED, [x,2.1,z+0.09], [0.6,0.4,0.02])

def npc(parent, name, vest_mat, x, z, ry=0):
    g = add_node(name, parent, t=[x,0,z], r=euler_to_quat(0,ry,0))
    cyl(g, name+"_Legs", M_DSTEEL, [0,0.4,0], size=[0.32,0.8,0.32])
    cyl(g, name+"_Body", vest_mat, [0,1.0,0], size=[0.38,0.6,0.24])
    cyl(g, name+"_Head", M_BEIGE, [0,1.5,0], size=[0.22,0.25,0.22])
    return g

def waypoint(parent, name, x, z):
    cyl(parent, name, M_YELLOW, [x,0.03,z], size=[0.3,0.04,0.3], geom="CYL12")

def spawn_pt(parent, name, x, y, z):
    return add_node(name, parent, t=[x,y,z])

def spawn_pt(parent, name, x, y, z):
    return add_node(name, parent, t=[x,y,z])

def control_post(parent, prefix, x, z, ry=0):
    g = add_node(prefix+"_ControlPost", parent, t=[x,0,z], r=euler_to_quat(0,ry,0))
    box(g, prefix+"_Desk", M_BEIGE, [0,0.75,0], [1.4,0.08,0.7])
    for lx,lz in [(-0.6,-0.28),(0.6,-0.28),(-0.6,0.28),(0.6,0.28)]:
        box(g, prefix+f"_Leg_{lx}_{lz}", M_DSTEEL, [lx,0.37,lz], [0.07,0.75,0.07])
    box(g, prefix+"_Screen", M_DARK, [0,1.25,-0.15], [0.9,0.55,0.06])
    box(g, prefix+"_ScreenGlow", M_HOLO, [0,1.25,-0.11], [0.8,0.45,0.02])
    box(g, prefix+"_BtnPanel", M_BEIGE, [0,0.85,0.15], [0.7,0.06,0.25])
    cyl(g, prefix+"_BtnG", M_GREEN, [-0.2,0.9,0.15], size=[0.07,0.05,0.07])
    cyl(g, prefix+"_BtnB", M_BLUE, [0,0.9,0.15], size=[0.07,0.05,0.07])
    cyl(g, prefix+"_BtnR", M_RED, [0.2,0.9,0.15], size=[0.09,0.06,0.09])
    box(g, prefix+"_Mast", M_DSTEEL, [0.6,1.2,0], [0.06,1.0,0.06])
    cyl(g, prefix+"_LampR", M_RED, [0.6,1.75,0], size=[0.12,0.12,0.12])
    cyl(g, prefix+"_LampG", M_GREEN, [0.6,1.6,0], size=[0.12,0.12,0.12])
    return g

# ---- Building dressing: baseboards, trays, pipes, dock stripes ----
for (wx,wz,w,d) in [(0,-14.8,40,0.25),(0,14.8,40,0.25),(19.8,0,0.25,30)]:
    box(bld, f"Baseboard_{wx}_{wz}", M_DSTEEL, [wx,0.12,wz], [w if w>1 else 0.25,0.25,d if d>1 else 0.25])
box(bld, "CableTray_Main", M_DSTEEL, [0,5.2,-5], [38,0.12,0.5])
cyl(bld, "Pipe_Orange", M_ORANGE, [0,5.0,6], size=[0.18,38,0.18], rot=euler_to_quat(0,0,90))
cyl(bld, "Pipe_Gray", M_ASTEEL, [0,4.8,6.4], size=[0.12,38,0.12], rot=euler_to_quat(0,0,90))
hazard_strip(bld, "DockStripes", -18.0, 0, n=12, along_x=False)
# zone floor tints (subtle darker insets)
box(z1, "FloorTint_Z1", M_FLOORTINT, [-12,0.005,-8], [13.6,0.012,10.6])
box(z2, "FloorTint_Z2", M_FLOORTINT, [12,0.005,-8], [13.6,0.012,10.6])
# columns bolts
for cx in [-15,-5,5,15]:
    for cz in [-10,10]:
        for ox,oz in [(-0.15,-0.15),(0.15,-0.15),(-0.15,0.15),(0.15,0.15)]:
            cyl(bld, f"Bolt_{cx}_{cz}_{ox}_{oz}", M_RUBBER, [cx+ox,0.03,cz+oz], size=[0.06,0.05,0.06], geom="CYL8")
# extinguisher + barrels
cyl(bld, "Extinguisher", M_RED, [4.5,0.35,0.5], size=[0.15,0.6,0.15])
box(bld, "Ext_Hose", M_RUBBER, [4.5,0.6,0.6], [0.05,0.05,0.25])
cyl(bld, "Barrel_B", M_BLUE, [-4.5,0.45,12.5], size=[0.6,0.9,0.6])
cyl(bld, "Barrel_G", M_GREEN, [-3.7,0.45,12.5], size=[0.6,0.9,0.6])

# ---- Z1 details (Naima: maquette Convoyeur/Bras/BacA/BacB/BacPlein/PosteControle/Palette/AGV/Quai) ----
control_post(z1, "Z1", -9.0, -4.2, ry=-25)
ao_skirt(z1, "AO_Conv", -12, -9, 6.2, 1.2)
ao_skirt(z1, "AO_Robot", -12, -7.3, 1.2, 1.2)
box(z1, "ConvTrim_Y1", M_YELLOW, [-12,0.9,-9.48], [6.0,0.05,0.06])
box(z1, "ConvTrim_Y2", M_YELLOW, [-12,0.9,-8.52], [6.0,0.05,0.06])
spawn_pt(z1, "Spawn_Colis", -15.4, 1.6, -9)
box(z1, "BinFull_Sensor", M_RED, [-13.5,0.85,-5.15], [0.12,0.08,0.06])
box(z1, "CableTray_Z1", M_DSTEEL, [-10.5,0.06,-6.5], [3.5,0.08,0.3])
totem(z1, "Totem_Z1", M_ORANGE, -5.8, -3.2)
hazard_strip(z1, "GateStrip_Z1", -15.5, -7.2, n=6, along_x=True)
waypoint(z1, "AGV_WP1_BacPlein", -13.5, -4.5)
waypoint(z1, "AGV_WP2_Aisle", -15.5, -2.0)
waypoint(z1, "AGV_WP3_Quai", -18.0, 0.5)

# ---- Z2 details (Chaima: Convoyeur/Camera/Bras/Conformes/Rebuts/PosteInspection/Auditeur) ----
z2arm = add_node("RebutArm_Base", z2, t=[14.6,0,-9])
cyl(z2arm, "RebutArm_Foot", M_WHITE, [0,0.15,0], size=[0.5,0.3,0.5])
box(z2arm, "RebutArm_Col", M_WHITE, [0,0.6,0], [0.25,0.6,0.25])
box(z2arm, "RebutArm_Arm", M_WHITE, [-0.4,1.0,0], [0.9,0.16,0.16], rot=euler_to_quat(0,0,-20))
box(z2arm, "RebutArm_Grip", M_DSTEEL, [-0.8,0.85,0], [0.15,0.2,0.2])
control_post(z2, "Z2_Inspect", 12.0, -4.0, ry=180)
cyl(z2, "RingLight", M_LED, [12,1.92,-9], size=[0.3,0.06,0.3])
ao_skirt(z2, "AO_InspectConv", 12, -9, 5.2, 1.1)
box(z2, "ConvTrimW_Y1", M_WHITE, [12,0.9,-9.42], [5.0,0.05,0.05])
spawn_pt(z2, "Spawn_Piece", 9.8, 1.1, -9)
npc(z2, "Auditeur_NPC", M_BLUE, 11.0, -3.0, ry=180)
waypoint(z2, "Audit_WP1_Poste", 11.5, -4.2)
waypoint(z2, "Audit_WP2_Aisle", 12.0, -6.5)
waypoint(z2, "Audit_WP3_Bacs", 12.0, -5.0)
totem(z2, "Totem_Z2", M_BLUE, 5.8, -3.2)
box(z2, "CableTray_Z2", M_DSTEEL, [12,0.06,-7.0], [0.3,0.08,3.5])

# ---- Z3 details (Ameen: Magasin/Plateau/Bras+Securite/PosteAssemblage/PosteControle/Operateur) ----
box(z3, "AssemblyPost_Top", M_GREEN, [-11,0.82,6.5], [1.8,0.06,1.0])
for lx,lz in [(-11.8,6.1),(-10.2,6.1),(-11.8,6.9),(-10.2,6.9)]:
    box(z3, f"AsmLeg_{lx}_{lz}", M_DSTEEL, [lx,0.4,lz], [0.08,0.8,0.08])
box(z3, "AssemblyMat", M_GREEN, [-11,0.87,6.5], [1.5,0.02,0.8])
control_post(z3, "Z3_Supervision", -11, 12.3, ry=180)
ao_skirt(z3, "AO_AsmRobot", -13, 8, 1.4, 1.4)
spawn_pt(z3, "Spawn_Kit", -14.5, 0.6, 9.5)
spawn_pt(z3, "Spawn_Device", -9.5, 1.0, 7.0)
npc(z3, "Operateur_NPC", M_GREEN, -14.5, 11.5, ry=0)
waypoint(z3, "Op_WP1_Magasin", -14.5, 10.5)
waypoint(z3, "Op_WP2_Gate", -12, 11.6)
waypoint(z3, "Op_WP3_Plateau", -11, 10.0)
totem(z3, "Totem_Z3", M_GREEN, -5.8, 12.5)
hazard_strip(z3, "GateStrip_Z3", -12, 11.0, n=6, along_x=True)
box(z3, "SafetyCurtain_Emitter", M_RED, [-8.5,1.2,8], [0.1,0.3,0.1])
box(z3, "SafetyCurtain_Recv", M_GREEN, [-8.5,1.2,10], [0.1,0.3,0.1])

# ---- Z4 details (Jihed: Convoyeur/Moteur/Capteur1-2/Armoire+Fusibles/Magasin/Multimetre/Technicien) ----
for (px,py,pz) in [(12,0.78,9.6),(11.0,1.36,8.6),(13.0,1.36,9.4),(14.5,0.78,11.1)]:
    cyl(z4, f"TestPoint_{px}_{pz}", M_BLUE, [px,py,pz], size=[0.06,0.04,0.06])
box(z4, "PowerCutoff_Box", M_RED, [13.8,1.2,11.3], [0.25,0.35,0.12])
box(z4, "PowerCutoff_Lever", M_DSTEEL, [13.8,1.2,11.2], [0.05,0.2,0.08])
box(z4, "FaultTag_Capteur2", M_RED, [13.0,1.5,9.4], [0.2,0.05,0.2])
ao_skirt(z4, "AO_TestConv", 12, 9, 4.2, 1.0)
box(z4, "CableTray_Z4", M_DSTEEL, [13.2,0.06,10.2], [2.5,0.08,0.3])
spawn_pt(z4, "Spawn_Spare", 11.0, 0.7, 11.0)
npc(z4, "Technicien_NPC", M_YELLOW, 12.5, 4.5, ry=180)
waypoint(z4, "Tech_WP1_Patrol", 11.0, 5.0)
waypoint(z4, "Tech_WP2_Conv", 12.0, 7.5)
waypoint(z4, "Tech_WP3_Magasin", 11.0, 10.2)
totem(z4, "Totem_Z4", M_YELLOW, 5.8, 12.5)
cyl(bld, "Extinguisher_Z4", M_RED, [16.5,0.35,5.0], size=[0.15,0.6,0.15])

print(f"V2 nodes={len(nodes)} meshes={len(meshes)} mats={len(materials)}")

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
