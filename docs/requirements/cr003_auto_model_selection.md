# Change Request CR-003: Auto Model Selection + Prompt-Side Dropdown

**Status**: Draft (Ready for Review)
**Created**: February 17, 2026
**Type**: UX Improvement + Routing Enhancement
**Priority**: High
**Affected Components**: Frontend UI, Backend Router, Dart/Python SDKs, Test Specs

## Problem Statement
The current workflow requires the user to select a model before composing a prompt. This adds friction and prevents a streamlined “just type” experience. The UI should allow a lightweight model picker next to the prompt input with a default of **Auto**, and the backend should start supporting basic auto-selection logic. The selector must also support **Free models only** and **Commercial models only** options to reduce cognitive load.

## Goals
- Remove the hard requirement for pre-selecting a model in the UI.
- Add a compact model dropdown next to the prompt input with a default **Auto** option.
- Provide selection modes: **Auto**, **Free models only**, **Commercial models only**, or **Specific model**.
- Introduce an initial auto-selection strategy in the backend (rule-based) as a foundation for smarter selection.

## Non‑Goals
- No ML-based model recommendation yet (rule-based only for now).
- No changes to model download or registry schema beyond what is required for selection.
- No changes to existing provider adapters beyond routing selection.

---

## Stakeholder Requirements

### SH-REQ-CR003-001: Frictionless prompt workflow
**Description**: Users should be able to send a prompt without manually selecting a model.

**Success Criteria**:
- The prompt can be submitted with model selection set to **Auto**.
- The UI does not block on model selection.
- The backend resolves an appropriate model when **Auto** is used.

### SH-REQ-CR003-002: Clear and discoverable model selector
**Description**: Users should have a compact model selector near the prompt input with a default **Auto** option and additional selection modes.

**Success Criteria**:
- The selector appears next to the prompt input.
- Default is **Auto**.
- Users can choose **Free models only** or **Commercial models only**.
- Users can still choose a specific model if they want.

### SH-REQ-CR003-003: Predictable auto-selection
**Description**: Auto-selection should be deterministic and transparent to users.

**Success Criteria**:
- Selection uses documented rules (no hidden behavior).
- The resolved model ID is returned in the response.
- Errors provide actionable guidance if no model can be selected.

---

## System Requirements

### SYS-REQ-CR003-001: Allow Auto model selection
**Description**: The API must accept a request without a specific model, or with model set to `auto`, and route to an appropriate model.

**Specification**:
- Request may omit `model` or set `model: "auto"`.
- Router chooses a model based on inputs and availability.
- Response includes the resolved model ID in `model`.

**Test**: TEST-SYS-CR003-001

### SYS-REQ-CR003-002: Rule-based model auto-detection
**Description**: Provide an initial rule-based model selection strategy with prompt-based inference.

**Specification**:
- Infer **modality intent** from prompt content and inputs:
  - If `input.images` present → select image-capable model.
  - If `input.mesh` present → select 3D-capable model.
  - If prompt contains image intent keywords (e.g., "generate an image", "draw", "illustration") → prefer image models.
  - If prompt contains 3D intent keywords (e.g., "3D model", "mesh", "OBJ") → prefer 3D models.
  - Else → select text model.
- If the default for the detected modality is unavailable, fall back to the first available model in that modality.

**Test**: TEST-SYS-CR003-002

### SYS-REQ-CR003-003: UI model selector placement
**Description**: The frontend must move model selection into a dropdown next to the prompt input.

**Specification**:
- Selector is shown adjacent to the prompt input field.
- Default is **Auto**.
- Selector modes: **Auto**, **Free models only**, **Commercial models only**, or **Specific model**.
- Selecting a model updates any schema/parameters panel as today.

**Test**: TEST-INT-CR003-001

### SYS-REQ-CR003-004: Preserve manual selection behavior
**Description**: When a user chooses a model explicitly, the system must honor it.

**Specification**:
- If `model` is set to a concrete model ID, auto-selection is bypassed.
- The router uses the selected model’s modality for processing.
### SYS-REQ-CR003-005: Selection mode filters
**Description**: The API must accept selection modes that constrain auto-selection to free or commercial models.

**Specification**:
- Client may send `model: "auto"` with an additional `selection_mode` value: `auto | free_only | commercial_only | model`.
- `free_only` restricts selection to models with provider type `local` or other non-commercial providers.
- `commercial_only` restricts selection to models from commercial providers (openai, anthropic, google, azure, xai).
- If no model matches the constraint, return a clear error with guidance.

**Test**: TEST-SYS-CR003-004

**Test**: TEST-SYS-CR003-003

---

## Software Requirements

### Frontend

**Story ID**: US-FE-CR003-001
**Title**: Prompt-side model dropdown with selection modes
**Priority**: High
**Story Points**: 5

As a user
I want a compact model selector next to the prompt input
So that I can keep focus on the prompt while still choosing a model

**Acceptance Criteria**:
- [ ] A dropdown is shown next to the prompt input.
- [ ] Default value is **Auto**.
- [ ] The dropdown offers **Auto**, **Free models only**, **Commercial models only**, and specific models.
- [ ] When a model is selected, schema/parameters update as usual.

**Traceability**: SYS-REQ-CR003-003, SYS-REQ-CR003-004
**Status**: Not Started

---

### Backend

**Story ID**: US-BE-CR003-001
**Title**: Auto selection routing with filters
**Priority**: High
**Story Points**: 5

As a developer
I want the backend to resolve a model when none is specified
So that clients can send prompts without selecting a model

**Acceptance Criteria**:
- [ ] `model` may be omitted or set to `auto`.
- [ ] Rule-based selection chooses an appropriate model using prompt intent.
- [ ] Selection can be constrained to free-only or commercial-only providers.
- [ ] Response includes the resolved `model`.
- [ ] If no suitable model exists, return a clear error.

**Traceability**: SYS-REQ-CR003-001, SYS-REQ-CR003-002
**Status**: Not Started

---

## Architecture & Design (Delta)

### Frontend Design
- Add a **ModelSelectorDropdown** next to the prompt input component.
- Replace the hard dependency on “selected model required” with **Auto** default.
- On **Auto**, the parameters panel should show a minimal state or the default modality schema.

**UI Sketch** (Text)
```
[ Model: Auto ▼ ] [ Prompt input ..................................... ] [ Send ]
```

### Backend Design
- Extend router selection logic to recognize `model: "auto"` or `model` omitted.
- Add rule-based resolver that maps prompt intent + input hints → modality → default or first available model.
- Apply selection filters for **Free models only** and **Commercial models only** when specified.
- Ensure resolved model ID is returned in the response.

### Data & Interface Notes
- No breaking API changes; `model` already optional. Treat `"auto"` as synonym for `null`.
- Explicit model IDs must bypass auto-selection.
- Introduce `selection_mode` field in the request (non-breaking default: `auto`).
- `input.images` and `input.mesh` are optional input payloads for multimodal requests (see Glossary).

---

## Test Specifications (Initial)

**TEST-SYS-CR003-001**: Auto selection when model is omitted
- **Steps**: Send a request without `model`.
- **Expected**: Response contains resolved `model` and valid output.

**TEST-SYS-CR003-002**: Auto selection with image input
- **Steps**: Send request with `input.images` and `model: auto`.
- **Expected**: Selected model is the default image model (or first available image model).

**TEST-SYS-CR003-003**: Manual model selection preserved
- **Steps**: Send request with explicit model ID.
- **Expected**: Router uses the specified model, no auto-selection applied.

**TEST-SYS-CR003-004**: Selection mode filters
- **Steps**: Send request with `selection_mode=free_only` and `selection_mode=commercial_only`.
- **Expected**: Router selects a model within the specified provider class or returns a clear error.

**TEST-INT-CR003-001**: Prompt-side dropdown default
- **Steps**: Open chat UI.
- **Expected**: Dropdown shows Auto by default; no blocking selection required.

---

## Traceability Matrix

Stakeholder → System

| Stakeholder Req ID | System Req ID(s) | Notes |
|---|---|---|
| SH-REQ-CR003-001 | SYS-REQ-CR003-001 | Auto model path |
| SH-REQ-CR003-002 | SYS-REQ-CR003-003 | Prompt-side dropdown |
| SH-REQ-CR003-003 | SYS-REQ-CR003-002, SYS-REQ-CR003-004 | Deterministic selection |

System → Software

| System Req ID | Software Component | User Story ID(s) | Notes |
|---|---|---|---|
| SYS-REQ-CR003-001 | Backend | US-BE-CR003-001 | Auto routing |
| SYS-REQ-CR003-002 | Backend | US-BE-CR003-001 | Rule-based selection |
| SYS-REQ-CR003-003 | Frontend | US-FE-CR003-001 | Dropdown UI |
| SYS-REQ-CR003-004 | Frontend/Backend | US-FE-CR003-001, US-BE-CR003-001 | Manual override |
| SYS-REQ-CR003-005 | Frontend/Backend | US-FE-CR003-001, US-BE-CR003-001 | Selection mode filters |

Requirements → Verification

| Requirement ID | Verification Type | Test/Procedure ID | Location | Notes |
|---|---|---|---|---|
| SYS-REQ-CR003-001 | Automated | TEST-SYS-CR003-001 | tests/system/test_auto_model_selection.py | New |
| SYS-REQ-CR003-002 | Automated | TEST-SYS-CR003-002 | tests/system/test_auto_model_selection.py | New |
| SYS-REQ-CR003-003 | Manual | TEST-INT-CR003-001 | docs/testing/manual_test_procedures.md | UI placement |
| SYS-REQ-CR003-004 | Automated | TEST-SYS-CR003-003 | tests/system/test_auto_model_selection.py | New |
| SYS-REQ-CR003-005 | Automated | TEST-SYS-CR003-004 | tests/system/test_auto_model_selection.py | New |

---

## Risks & Mitigations
- **Risk**: Auto-selection picks an unexpected model for some prompts.
  - **Mitigation**: Rule-based selection only; document rules and provide explicit override.
- **Risk**: UI still depends on model schema for parameter rendering.
  - **Mitigation**: In **Auto**, show a minimal parameter panel or default to text schema until a model is resolved.
- **Risk**: Free vs commercial classification is ambiguous for some providers.
  - **Mitigation**: Use a documented provider classification map and make it configurable.

---

## Glossary
- **input.images**: Optional array of base64-encoded image inputs included with a generation request. Used by image-capable or multimodal models.
- **input.mesh**: Optional base64-encoded 3D mesh payload (e.g., OBJ). Used by 3D-capable models.

---

## Definition of Ready / Done

**Ready**
- CR requirements defined and traceability filled.
- UI placement agreed (prompt-side dropdown).
- Auto-selection rules documented.

**Done**
- Dropdown and Auto option implemented.
- Auto-selection routing implemented.
- Tests added and passing per traceability.
- Docs updated to reflect Auto behavior.
