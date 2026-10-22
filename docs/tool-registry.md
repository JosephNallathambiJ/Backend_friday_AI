# Structured Tool Contract & Registry

## 1. Tool Contract Specification

Every tool in FRIDAY AI implements the `BaseTool` contract (`app/tools/base.py`):

```python
class BaseTool(ABC):
    name: str
    description: str
    input_schema: type[BaseModel] | dict[str, Any]
    output_schema: type[BaseModel] | dict[str, Any]
    required_capabilities: list[str]
    risk_level: ToolRiskLevel  # READ_ONLY, LOCAL_MUTATION, NETWORK_ACCESS, DESTRUCTIVE
    requires_approval: bool
    supports_dry_run: bool
    timeout_seconds: int
    idempotent: bool

    def validate_parameters(self, parameters: dict[str, Any]) -> dict[str, Any]: ...
    def audit_metadata(self, parameters: dict[str, Any]) -> dict[str, Any]: ...
    async def execute(self, parameters: dict[str, Any], dry_run: bool = False) -> ToolResult: ...
```

## 2. Registered Tools Catalog

| Tool Name | Risk Level | Required Capabilities | Requires Approval | Description |
| :--- | :--- | :--- | :--- | :--- |
| `list_files` | `READ_ONLY` | `filesystem.read` | No | List directory contents within approved root |
| `read_file` | `READ_ONLY` | `filesystem.read` | No | Read text lines with size bounding |
| `search_files` | `READ_ONLY` | `filesystem.read` | No | Search files by pattern in permitted roots |
| `get_file_metadata` | `READ_ONLY` | `filesystem.read` | No | Read file metadata without loading file content |
| `write_file` | `LOCAL_MUTATION` | `filesystem.write` | No | Atomic write with automatic backup |
| `copy_file` | `LOCAL_MUTATION` | `filesystem.write` | No | Copy file within approved roots |
| `move_file` | `LOCAL_MUTATION` | `filesystem.write` | No | Move or rename file within approved roots |
| `delete_file` | `DESTRUCTIVE` | `filesystem.delete` | **Yes** | Move file to recoverable trash |
| `git_status` | `READ_ONLY` | `filesystem.read` | No | Inspect repository branch and status |
| `git_diff` | `READ_ONLY` | `filesystem.read` | No | Inspect pending diffs |
| `run_terminal_command`| `LOCAL_MUTATION` | `process.execute` | **Yes** | Run profiled commands (`argv`, `shell=False`) |
| `security_scan` | `READ_ONLY` | `filesystem.read` | No | Static analysis and secret scan |
| `web_search` | `NETWORK_ACCESS` | `network.fetch` | No | Search public web sources |
| `fetch_webpage` | `NETWORK_ACCESS` | `network.fetch` | No | Fetch webpage text with SSRF protection |
| `browser_navigate` | `NETWORK_ACCESS` | `browser.navigate` | No | Open URL in isolated browser |
| `browser_read` | `READ_ONLY` | `browser.read` | No | Extract visible DOM text and links |
| `browser_interact` | `LOCAL_MUTATION` | `browser.interact` | Dynamic | Click, fill, or submit web forms |
| `browser_close` | `READ_ONLY` | `browser.navigate` | No | Terminate isolated browser session |
| `get_system_info` | `READ_ONLY` | `system.info.read` | No | Read system specs and platform telemetry |
| `launch_application` | `LOCAL_MUTATION`| `applications.launch` | No | Launch approved app (e.g. Calculator, TextEdit) |
| `send_notification` | `READ_ONLY` | `notifications.send`| No | Dispatch local OS desktop notification |
| `search_contacts` | `READ_ONLY` | `contacts.read` | No | Search contacts by name or organization |
| `create_contact` | `LOCAL_MUTATION` | `contacts.write` | No | Add contact to authorized storage |
| `delete_contact` | `DESTRUCTIVE` | `contacts.write` | **Yes** | Delete authorized contact record |

## 3. How to Register a New Tool

1. Create a tool class inheriting from `BaseTool` in `app/tools/`.
2. Define a Pydantic `input_schema`.
3. Declare `name`, `risk_level`, and `required_capabilities`.
4. Register the instance in `ToolRegistry` (`app/tools/registry.py`):
   ```python
   tool_registry.register(MyNewTool())
   ```
