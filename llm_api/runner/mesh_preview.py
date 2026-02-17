from __future__ import annotations

import io
import os
import sys
from typing import Optional


def render_mesh_preview(obj_bytes: bytes, size: int = 512) -> Optional[bytes]:
    """Render a static PNG preview from OBJ bytes.

    Returns PNG bytes on success, or None on failure.
    """
    if not obj_bytes:
        return None

    try:
        # Optional dependency imports
        import numpy as np
        import trimesh
        import pyrender
    except Exception:
        return None

    # Prefer EGL for headless Linux if available (ignore if unsupported)
    if sys.platform.startswith("linux") and "PYOPENGL_PLATFORM" not in os.environ:
        os.environ["PYOPENGL_PLATFORM"] = "egl"

    try:
        mesh = trimesh.load(
            io.BytesIO(obj_bytes), file_type="obj", force="mesh", skip_materials=True
        )
        if mesh is None or mesh.is_empty:
            return None

        if isinstance(mesh, trimesh.Scene):
            # If multiple geometries, merge into a single mesh for preview.
            mesh = trimesh.util.concatenate(
                [g for g in mesh.geometry.values() if g is not None]
            )

        scene = pyrender.Scene(bg_color=[30, 30, 30, 255], ambient_light=[0.4, 0.4, 0.4])
        render_mesh = pyrender.Mesh.from_trimesh(mesh, smooth=False)
        scene.add(render_mesh)

        # Camera placement based on mesh bounds
        bounds = mesh.bounds
        center = bounds.mean(axis=0)
        extents = mesh.extents
        max_dim = float(max(extents)) if extents is not None else 1.0
        distance = max_dim * 2.5 if max_dim > 0 else 2.5

        camera = pyrender.PerspectiveCamera(yfov=1.0)
        camera_pose = _look_at(
            eye=center + np.array([0.0, 0.0, distance]),
            target=center,
            up=np.array([0.0, 1.0, 0.0]),
        )
        scene.add(camera, pose=camera_pose)

        light = pyrender.DirectionalLight(color=np.ones(3), intensity=2.0)
        scene.add(light, pose=camera_pose)

        renderer = pyrender.OffscreenRenderer(viewport_width=size, viewport_height=size)
        color, _ = renderer.render(scene)
        renderer.delete()

        # Encode to PNG
        from PIL import Image

        image = Image.fromarray(color)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception:
        return None


def _look_at(eye, target, up):
    import numpy as np

    forward = target - eye
    forward = forward / (np.linalg.norm(forward) + 1e-8)
    right = np.cross(forward, up)
    right = right / (np.linalg.norm(right) + 1e-8)
    true_up = np.cross(right, forward)

    pose = np.eye(4)
    pose[0, :3] = right
    pose[1, :3] = true_up
    pose[2, :3] = -forward
    pose[:3, 3] = eye
    return pose