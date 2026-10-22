# Scoped Filesystem Access & Recovery

## 1. Security Architecture

All file operations in FRIDAY AI are mediated through `FilesystemService` (`app/services/filesystem_service.py`) and verified against `PathValidator` (`app/security/path_validation.py`).

### Key Safeguards
- **Canonical Boundary Check**: All paths are resolved via `Path.resolve()` before checks, completely neutralizing `..` path traversal sequences.
- **Symlink Escape Defense**: Any symbolic link targeting a path outside the approved project roots is rejected with `SecurityPolicyError`.
- **Sensitive Path Denylist**: Access to `.env*`, `*.key`, `*.pem`, `*.token`, `.git`, `.venv`, and `node_modules` is blocked.
- **Atomic Writes**: Writes are written to an isolated temporary file in the same directory, flushed and synced (`os.fsync`), and atomically swapped via `os.replace`.
- **Automatic Backups**: Overwrites create a timestamped `.bak.<timestamp>` file before replacing existing content.
- **Recoverable Trash**: Deletions do not execute `rm` or unrecoverable filesystem drops. Files are safely relocated to `.friday_trash/<filename>.deleted.<timestamp>`.

## 2. Supported Operations & Tools

- `list_files`: Non-recursive and bounded recursive directory walk.
- `read_file`: Line-bounded read with a 10MB safety threshold.
- `search_files`: Filename pattern matching within approved roots.
- `get_file_metadata`: Stat inspection without loading file content into LLM context.
- `write_file`: Atomic text file write with optional backup creation.
- `copy_file` & `move_file`: Scoped copy and rename inside permitted roots.
- `delete_file`: Relocation to recoverable trash (requires `filesystem.delete` and human approval).
