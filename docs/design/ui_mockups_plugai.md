# PlugAI UI Mockups (Text Wireframes)

**Date**: January 24, 2026
**Status**: Draft

These are lightweight ASCII wireframes to visualize layout options.

---

## Option A — Chat‑First (Desktop)

```
+---------------------------------------------------------------------------------+
| PlugAI | Models | Sessions | Profile                                        [⚙] |
+---------------------------------------------------------------------------------+
| Models (Text/Image/3D) |                    Chat                                 |
| - GPT-4                |  [assistant] Hello! How can I help?                    |
| - DeepSeek R1          |  [user] Write a haiku about stars                       |
| - SDXL                 |  [assistant] ...                                       |
|------------------------|                                                       |
| Sessions               |                                                       |
| - New Session          |                                                       |
| - Project X            |                                                       |
+------------------------+-----------------------------+--------------------------+
| Settings (Drawer)      | Prompt: [________________]  | Send ▶                  |
| Temperature [----]     |                             |                          |
| Max Tokens [----]      |                             |                          |
+------------------------+-----------------------------+--------------------------+
```

**Best for**: text-heavy usage and quick chat flow.

**Auto-switch rule**: Use for text models when layout mode is Auto.

---

## Option B — Studio (Image/3D‑first)

```
+---------------------------------------------------------------------------------+
| PlugAI | Models | Presets | Profile                                      [⚙]    |
+---------------------------------------------------------------------------------+
| Models + Modality Tabs  |                   Canvas/Preview                       |
| [Text] [Image] [3D]     |  [Image/3D Preview Area]                              |
| - SDXL (selected)       |  [Gallery Thumbs]                                     |
| - DreamShaper           |                                                       |
|-------------------------+--------------------------------------+-----------------|
| Prompt: [______________________________]                     | Settings ▸      |
| Generate ▶                                                 | Steps [---]       |
|                                                          | CFG [---]         |
+----------------------------------------------------------+--------------------+
```

**Best for**: image/3D generation workflows (Foooocus‑like).

**Auto-switch rule**: Use for image/3D models when layout mode is Auto.

---

## Option C — Compact Mobile‑First

```
+------------------------------+
| PlugAI        [Model ▾] [≡] |
+------------------------------+
| Chat / Canvas area           |
| [assistant] ...              |
| [user] ...                   |
+------------------------------+
| Prompt: [______________] ▶   |
+------------------------------+
| Bottom Sheet (Settings)      |
| Temperature [----]           |
| Max Tokens  [----]           |
+------------------------------+
```

**Best for**: mobile and small screens.

**Auto-switch rule**: Use on mobile devices when layout mode is Auto.

---

## Authentication & Profile (All Options)

```
+-----------------------------+
| PlugAI Login                |
| Email: [______________]     |
| Password: [___________]     |
| Invite Token: [________]    |
| [Register] [Login]          |
+-----------------------------+

+-----------------------------+
| Profile & Preferences       |
| Preferred Models: [..]      |
| Default Modality: [Text ▾]  |
| Layout Mode: [Auto ▾]       |
| Layout Lock: [Chat/Studio]  |
| API Base URL: [________]    |
| Provider Keys [Manage]      |
| API Tokens   [Manage]       |
+-----------------------------+
```
