# PlugAI Frontend

Cross-platform Flutter UI for the Pluggably LLM API Gateway. Provides model browsing, chat with streaming, session management, settings, auth, and key/token management.

## Prerequisites
- Flutter 3.x (stable)
- Dart SDK (bundled with Flutter)
- Backend running locally or reachable over the network

## Quick Start

Install dependencies:

```bash
cd frontend
flutter pub get
```

Run the app:

```bash
flutter run -d chrome
```

Other devices:

```bash
flutter run -d ios
flutter run -d android
```

## Configuration

1. Open **Settings** in the app.
2. Set **API URL** to your backend base URL (default: `http://localhost:8000`).
3. If invite-only auth is enabled, use **Register** with an invite token, then **Login**.

## Features Implemented
- Model catalog with modality filters
- Schema-driven settings drawer (text/number/boolean/enum/slider)
- Chat with streaming responses, markdown rendering, cancel, and regenerate
- Sessions list/create/switch
- Auth (login/register/logout)
- Provider keys management
- User API tokens management
- Profile view

## Known Gaps
- Image generation gallery UI
- 3D preview UI
- Queue position indicator
- UI layout auto-switch/lock
- Download progress + retry for model downloads

## Tests

```bash
flutter test
```

## Lint

```bash
flutter analyze
```
