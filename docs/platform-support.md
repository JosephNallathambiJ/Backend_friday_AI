# Operating System & Platform Support Matrix

## 1. Platform Matrix

| Subsystem | macOS (Darwin) | Linux | Windows |
| :--- | :--- | :--- | :--- |
| **Agent Runtime & Planner** | Supported (Full) | Supported (Full) | Supported (Full) |
| **SQLite + FTS5 Search** | Supported (Full) | Supported (Full) | Supported (Full) |
| **Filesystem Service** | Supported (Full) | Supported (Full) | Supported (Full) |
| **Command Runner** | Supported (Full) | Supported (Full) | Supported (POSIX / cmd) |
| **Web Research (HTTPX/BS4)**| Supported (Full) | Supported (Full) | Supported (Full) |
| **Browser Automation (Playwright)** | Supported (Full) | Supported (Full) | Supported (Full) |
| **Contacts Service** | Supported (Database/osascript)| Supported (Database) | Supported (Database) |
| **Desktop Notifications** | Supported (`osascript`)| Supported (`notify-send`) | Supported (`toast`) |
| **Application Launcher** | Supported (`open -a`) | Supported (`xdg-open`)| Supported (`start`) |

## 2. macOS-Specific Notes
- **Application Launching**: Uses `open -a <App>` restricted to `Calculator`, `TextEdit`, `Notes`, `Terminal`, `Calendar`.
- **Notifications**: Uses `osascript -e 'display notification ...'` with sanitized strings.
- **DNS Cache Flushing**: Uses `dscacheutil -flushcache` via the Privileged Tool Gateway.
