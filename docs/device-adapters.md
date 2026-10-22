# Device Context & System Adapters

## 1. Overview

The `DeviceContextService` (`app/services/device_context_service.py`) provides safe, permitted access to host hardware telemetry and operating system capabilities.

## 2. Supported Capabilities

### System Telemetry (`get_system_info`)
Returns sanitized system hardware and runtime details:
- OS name (`Darwin`, `Linux`, `Windows`)
- Kernel / OS release
- Machine architecture (`arm64`, `x86_64`)
- Available CPU core count
- Active Python runtime version

### Local Application Launch (`launch_application`)
Supports launching explicitly allowed applications on macOS:
- Allowed applications: `Calculator`, `TextEdit`, `Notes`, `Terminal`, `Calendar`.
- Any application not on the allowlist is rejected with `SecurityPolicyError`.

### Desktop Notifications (`send_notification`)
Dispatches user alerts to the local desktop:
- On macOS: Uses `osascript` to trigger native notifications with sanitized strings.
- Gracefully handles unsupported platforms.
