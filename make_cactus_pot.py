import math
import os
from mathutils import Vector

import bpy


OUT_DIR = os.path.dirname(os.path.abspath(__file__))
BLEND_PATH = os.path.join(OUT_DIR, "ribbed_cactus_pot.blend")
STL_PATH = os.path.join(OUT_DIR, "ribbed_cactus_pot.stl")
GLB_PATH = os.path.join(OUT_DIR, "ribbed_cactus_pot.glb")


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def make_mat(name, color, roughness=0.6):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def shade_and_smooth(obj, bevel=None, subdivision=None):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth()
    obj.select_set(False)

    if bevel:
        mod = obj.modifiers.new("soft bevels", "BEVEL")
        mod.width = bevel
        mod.segments = 5
        mod.affect = "EDGES"

    if subdivision:
        mod = obj.modifiers.new("soft surface", "SUBSURF")
        mod.levels = subdivision
        mod.render_levels = subdivision


def create_ribbed_cactus(mat):
    segments = 192
    rings = 72
    ribs = 8
    verts = []
    faces = []

    for i in range(rings + 1):
        v = i / rings
        z = 1.18 + 3.55 * v

        # Bulbous cactus profile: narrow neck/base, widest around the middle.
        profile = math.sin(math.pi * v) ** 0.42
        radius = 0.46 + 1.13 * profile
        radius *= 1.0 - 0.12 * max(0.0, v - 0.78) / 0.22

        for j in range(segments):
            theta = 2.0 * math.pi * j / segments
            rib = math.cos(ribs * theta)
            secondary = math.cos(ribs * theta * 2.0 + 0.55)
            rib_radius = radius * (1.0 + 0.145 * rib + 0.018 * secondary)

            x = rib_radius * math.cos(theta)
            y = rib_radius * math.sin(theta)

            # Slightly tuck each groove inward vertically for the sculpted crease feel.
            groove = max(0.0, -rib)
            z_offset = -0.045 * groove * math.sin(math.pi * v)
            verts.append((x, y, z + z_offset))

    for i in range(rings):
        for j in range(segments):
            a = i * segments + j
            b = i * segments + (j + 1) % segments
            c = (i + 1) * segments + (j + 1) % segments
            d = (i + 1) * segments + j
            faces.append((a, b, c, d))

    mesh = bpy.data.meshes.new("ribbed cactus mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("8-rib rounded cactus body", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    shade_and_smooth(obj, subdivision=1)
    return obj


def add_uv_sphere(name, location, scale, mat, rotation=(0, 0, 0), segments=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    shade_and_smooth(obj)
    return obj


def create_top_petals(mat):
    # Lower front ring, like the thick lip visible in the reference.
    for idx, angle in enumerate([math.radians(a) for a in (-18, 42, 102, 162, 222, 282)]):
        r = 0.58
        x = r * math.cos(angle)
        y = r * math.sin(angle)
        rot = (math.radians(12), 0, angle)
        petal = add_uv_sphere(
            f"lower thick petal {idx + 1}",
            (x, y, 4.68),
            (0.82, 0.28, 0.18),
            mat,
            rotation=rot,
        )
        petal.rotation_euler[2] = angle

    # Taller back petals, cupped upward.
    for idx, angle in enumerate([math.radians(a) for a in (25, 92, 155, 220, 292)]):
        r = 0.38
        x = r * math.cos(angle)
        y = r * math.sin(angle)
        petal = add_uv_sphere(
            f"upper cupped petal {idx + 1}",
            (x, y, 4.98),
            (0.62, 0.31, 0.24),
            mat,
            rotation=(math.radians(28), math.radians(4), angle),
        )
        petal.rotation_euler[2] = angle

    add_uv_sphere("central bud", (0, 0, 4.71), (0.46, 0.42, 0.22), mat, segments=48, rings=24)


def create_pot(pot_mat, soil_mat):
    bpy.ops.mesh.primitive_cone_add(vertices=160, radius1=1.42, radius2=1.82, depth=1.82, location=(0, 0, 0.13))
    pot = bpy.context.object
    pot.name = "tapered flower pot"
    pot.data.materials.append(pot_mat)
    shade_and_smooth(pot, bevel=0.035)

    bpy.ops.mesh.primitive_torus_add(
        major_radius=1.64,
        minor_radius=0.20,
        major_segments=192,
        minor_segments=24,
        location=(0, 0, 1.08),
    )
    rim = bpy.context.object
    rim.name = "rounded thick pot rim"
    rim.data.materials.append(pot_mat)
    shade_and_smooth(rim)

    bpy.ops.mesh.primitive_cylinder_add(vertices=160, radius=1.46, depth=0.16, location=(0, 0, 1.10))
    soil = bpy.context.object
    soil.name = "recessed soil surface"
    soil.data.materials.append(soil_mat)
    shade_and_smooth(soil, bevel=0.015)

    bpy.ops.mesh.primitive_torus_add(
        major_radius=1.25,
        minor_radius=0.045,
        major_segments=160,
        minor_segments=12,
        location=(0, 0, 1.18),
    )
    inner = bpy.context.object
    inner.name = "inner shadow groove"
    inner.data.materials.append(soil_mat)
    shade_and_smooth(inner)

    return pot


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_small_base_lobes(mat):
    for idx in range(8):
        angle = 2 * math.pi * idx / 8
        x = 0.78 * math.cos(angle)
        y = 0.78 * math.sin(angle)
        obj = add_uv_sphere(
            f"small root lobe {idx + 1}",
            (x, y, 1.30),
            (0.35, 0.20, 0.18),
            mat,
            rotation=(0, 0, angle),
            segments=32,
            rings=16,
        )
        obj.rotation_euler[2] = angle


def setup_scene():
    bpy.ops.object.light_add(type="AREA", location=(-3.2, -4.0, 7.0))
    key = bpy.context.object
    key.name = "large softbox"
    key.data.energy = 420
    key.data.size = 4.0

    bpy.ops.object.camera_add(location=(4.2, -8.1, 4.65))
    camera = bpy.context.object
    bpy.context.scene.camera = camera
    camera.data.lens = 38
    look_at(camera, (0, 0, 2.55))

    bpy.ops.mesh.primitive_plane_add(size=7.5, location=(0, 0, -0.82))
    floor = bpy.context.object
    floor.name = "dark preview floor"
    floor.data.materials.append(make_mat("matte dark floor", (0.018, 0.020, 0.022, 1), 0.9))

    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 80
    bpy.context.scene.view_settings.view_transform = "Filmic"
    bpy.context.scene.view_settings.look = "Medium High Contrast"
    bpy.context.scene.unit_settings.system = "METRIC"


def export_assets():
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)

    if hasattr(bpy.ops.wm, "stl_export"):
        bpy.ops.wm.stl_export(filepath=STL_PATH, export_selected_objects=False)
    elif hasattr(bpy.ops.export_mesh, "stl"):
        bpy.ops.export_mesh.stl(filepath=STL_PATH, use_selection=False)

    if hasattr(bpy.ops.export_scene, "gltf"):
        bpy.ops.export_scene.gltf(filepath=GLB_PATH, export_format="GLB")


def main():
    clear_scene()
    grey_clay = make_mat("single material grey clay", (0.46, 0.46, 0.43, 1), 0.72)
    dark_soil = make_mat("slightly darker recessed soil", (0.25, 0.24, 0.22, 1), 0.88)

    create_pot(grey_clay, dark_soil)
    create_ribbed_cactus(grey_clay)
    add_small_base_lobes(grey_clay)
    create_top_petals(grey_clay)
    setup_scene()

    export_assets()


if __name__ == "__main__":
    main()
