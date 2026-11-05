"""Build and render the 3D campaign scenes headlessly.

Usage: blender -b --factory-startup -P tools/blender_scenes.py -- [key|gift] [--preview]
Textures come from concept/print.html (see tools/render_print.py).
"""
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
TEX = ROOT / "assets" / "img" / "print"
OUT = ROOT / "assets" / "img" / "3d"
OUT.mkdir(parents=True, exist_ok=True)
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = "--preview" in ARGS
SCENES = [a for a in ARGS if not a.startswith("--")] or ["key", "gift"]


def srgb(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return (*linear, 1)


def bsdf(mat):
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def mat_color(name, hex_color, rough=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    node = bsdf(mat)
    node.inputs["Base Color"].default_value = srgb(hex_color)
    node.inputs["Roughness"].default_value = rough
    node.inputs["Metallic"].default_value = metallic
    return mat


def mat_image(name, file, rough=0.45):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    node = bsdf(mat)
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(TEX / file))
    tex.extension = "EXTEND"
    mat.node_tree.links.new(tex.outputs["Color"], node.inputs["Base Color"])
    node.inputs["Roughness"].default_value = rough
    return mat


def mat_cardboard():
    mat = mat_color("cardboard", "#C98A4F", 0.8)
    tree = mat.node_tree
    noise = tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 90
    noise.inputs["Detail"].default_value = 8
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = srgb("#B5763D")
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = srgb("#D69C62")
    tree.links.new(noise.outputs[0], ramp.inputs[0])
    tree.links.new(ramp.outputs[0], bsdf(mat).inputs["Base Color"])
    return mat


def cube(name, size, loc, rot=(0, 0, 0), mat=None, bevel=0.004):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
    if mat:
        obj.data.materials.append(mat)
    return obj


def plane(name, w, h, loc, rot, mat, bend=0.0, cuts=24):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (w, h, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.subdivide(number_cuts=cuts)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.data.materials.append(mat)
    if bend:
        mod = obj.modifiers.new("bend", "SIMPLE_DEFORM")
        mod.deform_method = "BEND"
        mod.deform_axis = "Y"
        mod.angle = bend
    solid = obj.modifiers.new("solid", "SOLIDIFY")
    solid.thickness = 0.0015
    bpy.ops.object.shade_smooth()
    return obj


def brackets(sheet, w, h, mat, arm=0.05, thick=0.008, pad=0.03):
    """Corner brackets, the campaign's scan device, placed in the sheet's own plane."""
    bpy.context.view_layer.update()
    world = sheet.matrix_world.copy()
    rot = sheet.rotation_euler.copy()
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 + pad), sy * (h / 2 + pad)
            cube("br", (arm, thick, thick), world @ Vector((x - sx * arm / 2, y, 0.012)), rot, mat, 0)
            cube("br", (thick, arm, thick), world @ Vector((x, y - sy * arm / 2, 0.012)), rot, mat, 0)


def base(color, lens):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
            if any(d.type == kind for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == kind
                scene.cycles.device = "GPU"
                break
        except TypeError:
            continue
    scene.cycles.samples = 32 if PREVIEW else 192
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = srgb(color)
    bg.inputs[1].default_value = 0.42
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    bpy.context.object.is_shadow_catcher = True
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.data.lens = lens
    scene.camera = cam
    return scene, cam


def aim(cam, loc, target):
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


def light(kind, loc, energy, size=2.0, target=(0, 0, 0.3), color=(1, 1, 1)):
    bpy.ops.object.light_add(type=kind, location=loc)
    obj = bpy.context.object
    obj.data.energy = energy
    obj.data.color = color
    if kind == "AREA":
        obj.data.size = size
    obj.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


def carton(mat, label):
    w, d, h, t = 0.9, 0.62, 0.5, 0.012
    cube("bottom", (w, d, t), (0, 0, t / 2), mat=mat)
    for sx in (-1, 1):
        cube("side", (t, d, h), (sx * w / 2, 0, h / 2), mat=mat)
        cube("flap", (0.26, d, t), (sx * (w / 2 + 0.115), 0, h + 0.06), (0, sx * math.radians(-27), 0), mat=mat)
    for sy in (-1, 1):
        cube("side", (w, t, h), (0, sy * d / 2, h / 2), mat=mat)
        cube("flap", (w, 0.22, t), (0, sy * (d / 2 + 0.1), h + 0.05), (sy * math.radians(27), 0, 0), mat=mat)
    plane("label", 0.56, 0.31, (0.02, -d / 2 - 0.009, h * 0.5), (math.radians(90), 0, 0), label, cuts=1)


def scene_key():
    scene, cam = base("#006FF7", 62)
    scene.render.resolution_x, scene.render.resolution_y = (640, 800) if PREVIEW else (1600, 2000)
    paper = mat_image("invoice", "invoice.png", 0.5)
    orange = mat_color("orange", "#FC5E22", 0.35)
    carton(mat_cardboard(), mat_image("label", "label.png"))
    random.seed(11)
    w, h = 0.3, 0.42
    for i in range(12):
        p = i / 11
        ang = i * 2.35
        r = 0.2 + 0.62 * p ** 0.7
        loc = (r * math.cos(ang), r * math.sin(ang) * 0.6, 0.62 + 1.9 * p)
        rot = (math.radians(70 + random.uniform(-38, 38)), math.radians(random.uniform(-32, 32)), math.radians(random.uniform(-40, 40)))
        plane(f"sheet{i}", w, h, loc, rot, paper, bend=math.radians(random.uniform(-45, 45)), cuts=12)
    hero = plane("hero", 0.62, 0.868, (0.05, -1.25, 1.95), (math.radians(84), math.radians(4), math.radians(-6)), paper, cuts=8)
    brackets(hero, 0.62, 0.868, orange, arm=0.14, thick=0.022, pad=0.05)
    aim(cam, (1.5, -6.0, 1.7), (0, 0, 1.25))
    light("AREA", (-2.5, -3.5, 4.5), 210, 4, (0, 0, 1.2))
    light("AREA", (3.2, -2.0, 1.6), 50, 3, (0, 0, 1.2), (1.0, 0.8, 0.9))
    return scene


def mug(body_mat, inner_mat, handle_mat, loc, yaw):
    r, h, seg = 0.17, 0.36, 96
    verts, faces, uvs = [], [], []
    for i in range(seg + 1):
        a = 2 * math.pi * i / seg
        verts += [(r * math.cos(a), r * math.sin(a), 0), (r * math.cos(a), r * math.sin(a), h)]
    for i in range(seg):
        k = 2 * i
        faces.append((k, k + 2, k + 3, k + 1))
        uvs.append([(i / seg, 0), ((i + 1) / seg, 0), ((i + 1) / seg, 1), (i / seg, 1)])
    mesh = bpy.data.meshes.new("mug")
    mesh.from_pydata(verts, [], faces)
    layer = mesh.uv_layers.new(name="UVMap")
    for poly, quad in zip(mesh.polygons, uvs):
        for li, uv in zip(poly.loop_indices, quad):
            layer.data[li].uv = uv
    obj = bpy.data.objects.new("mug", mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(body_mat)
    mesh.materials.append(inner_mat)
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    obj.modifiers.new("weld", "WELD")
    solid = obj.modifiers.new("solid", "SOLIDIFY")
    solid.thickness = 0.014
    solid.offset = -1
    solid.material_offset = 1
    solid.material_offset_rim = 1
    obj.location = loc
    obj.rotation_euler[2] = yaw
    bpy.ops.mesh.primitive_cylinder_add(radius=r - 0.004, depth=0.012, location=(loc[0], loc[1], 0.012))
    bpy.context.object.data.materials.append(inner_mat)
    curve = bpy.data.curves.new("handle", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.019
    curve.bevel_resolution = 6
    spline = curve.splines.new("POLY")
    pts = [(loc[0] + r - 0.004 + 0.1 * math.cos(a), loc[1], h / 2 + 0.105 * math.sin(a)) for a in [math.pi * (k / 24 - 0.5) for k in range(25)]]
    spline.points.add(len(pts) - 1)
    for point, co in zip(spline.points, pts):
        point.co = (*co, 1)
    handle = bpy.data.objects.new("handle", curve)
    bpy.context.collection.objects.link(handle)
    curve.materials.append(handle_mat)
    return obj


def scene_gift():
    scene, cam = base("#FF78E6", 58)
    scene.render.resolution_x, scene.render.resolution_y = (800, 600) if PREVIEW else (2000, 1500)
    card = mat_cardboard()
    label = mat_image("label", "label.png")
    w, d, h, t = 1.1, 0.72, 0.34, 0.012
    origin = Vector((-0.42, 0.2, 0))
    cube("bottom", (w, d, t), origin + Vector((0, 0, t / 2)), mat=card)
    for sx in (-1, 1):
        cube("side", (t, d, h), origin + Vector((sx * w / 2, 0, h / 2)), mat=card)
    for sy in (-1, 1):
        cube("side", (w, t, h), origin + Vector((0, sy * d / 2, h / 2)), mat=card)
    plane("label", 0.5, 0.278, origin + Vector((0, -d / 2 - 0.009, h / 2)), (math.radians(90), 0, 0), label, cuts=1)
    # Lid leans against the back wall of the box.
    lid = Vector((-0.42, 0.85, 0.42))
    cube("lid", (w + .03, .74, .012), lid, (math.radians(68), 0, 0), mat=card)
    plane("note", 0.62, 0.86, origin + Vector((-0.1, 0.0, 0.33)), (math.radians(-14), math.radians(9), math.radians(9)), mat_image("nb2", "notebook.png"), cuts=4)
    book = mat_image("notebook", "notebook.png", 0.4)
    cube("pages", (.5, .7, .05), (0.62, -0.5, .03), (0, 0, math.radians(-14)), mat=mat_color("pg", "#F2F7FE", .6), bevel=.002)
    plane("cover", 0.51, 0.714, (0.62, -0.5, 0.058), (0, 0, math.radians(-14)), book, cuts=1)
    plane("stickers", 0.46, 0.644, (-0.3, -0.72, 0.004), (0, 0, math.radians(11)), mat_image("stickers", "stickers.png", 0.3), cuts=1)
    wrap = mat_image("mug", "mug.png", 0.22)
    mug(wrap, mat_color("inner", "#F2F7FE", .25), mat_color("hm", "#FC5E22", .25), (0.72, 0.28, 0), math.radians(78))
    aim(cam, (0.3, -3.9, 2.7), (0.1, -0.02, 0.2))
    light("AREA", (-2.2, -2.4, 3.8), 170, 4, (0, 0, .2))
    light("AREA", (3, -1, 2), 45, 3, (0, 0, .2), (1, .9, .8))
    return scene


for name in SCENES:
    scene = {"key": scene_key, "gift": scene_gift}[name]()
    scene.render.filepath = str(OUT / (f"{name}_preview.png" if PREVIEW else f"{name}.png"))
    bpy.ops.render.render(write_still=True)
    print("RENDERED", scene.render.filepath, scene.cycles.device)
