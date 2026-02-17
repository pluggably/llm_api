# ADR 006: 3D Viewer Uses three_dart with OBJ Artifacts

**Date**: January 27, 2026  
**Status**: Proposed

## Context
The frontend needs to render 3D outputs and provide download capability. The backend currently emits mesh artifacts as OBJ. The UI must support rotate/zoom interaction and mesh download. Two options were considered:

- **Option A**: Use `three_dart` with an OBJ loader to render current OBJ artifacts.
- **Option B**: Use `model_viewer_plus`, which is better suited for GLB/GLTF but requires backend changes to output GLB/GLTF.

## Decision
Select **Option A**: `three_dart` + OBJ loader for the initial 3D preview implementation.

## Rationale
- Aligns with the current backend mesh output (OBJ) without additional backend changes.
- Provides immediate interactive preview (rotate/zoom) in Flutter web/mobile.
- Keeps scope localized to frontend changes for the first iteration.

## Consequences
- Viewer implementation depends on OBJ loading and may require additional performance tuning for large meshes.
- If GLB/GLTF becomes a requirement, the backend may need to add a mesh conversion step and the frontend can re-evaluate `model_viewer_plus`.

## Alternatives Considered
- **Option B**: `model_viewer_plus` with GLB/GLTF output from the backend. Rejected for now due to added backend scope.
