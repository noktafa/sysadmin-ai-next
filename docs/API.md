# API Reference

## Core API

### SysAdminAI

Main orchestrator class that coordinates all components.

```python
class SysAdminAI:
    def __init__(
        self,
        user_id: str | None = None,
        enable_opa: bool = True,
        dry_run: bool = False,
        track_costs: bool = True,
    )
```

**Parameters:**
- `user_id` - User identifier for session isolation
- `enable_opa` - Enable OPA policy engine
- `dry_run` - Preview mode (no actual execution)
- `track_costs` - Enable token usage tracking

**Methods:**

#### execute_command()

```python
async def execute_command(
    self,
    command: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]
```

Execute a command with full policy checking and recovery.

**Returns:**
```python
{
    "command": str,
    "user_id": str,
    "dry_run": bool,
    "allowed": bool,
    "executed": bool,
    "output": str | None,
    "error": str | None,
    "suggestions": list[str],
    "cost": dict | None,
}
```

#### export_session()

```python
def export_session(self, format_type: str = "ansible") -> str
```

Export session history as a playbook.

**Parameters:**
- `format_type` - One of: "ansible", "terraform", "shell"

## Policy Engine

### PolicyEngine

```python
class PolicyEngine:
    def __init__(
        self,
        opa_url: str = "http://localhost:8181",
        policy_dir: str | Path | None = None,
    )
```

**Methods:**

#### evaluate()

```python
def evaluate(self, command: str) -> PolicyResult
```

Evaluate a command against security policies.

#### add_rule()

```python
def add_rule(self, rule: PolicyRule) -> None
```

Add a custom policy rule.

#### dry_run()

```python
def dry_run(self, command: str) -> dict[str, Any]
```

Preview policy evaluation without enforcing.

### PolicyRule

```python
@dataclass
class PolicyRule:
    name: str
    description: str
    pattern: str  # Regex pattern
    action: PolicyAction
    severity: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)
```

### PolicyAction

```python
class PolicyAction(Enum):
    ALLOW = "allow"
    BLOCK = "block"
    CONFIRM = "confirm"
    LOG = "log"
```

### PolicyResult

```python
@dataclass
class PolicyResult:
    allowed: bool
    action: PolicyAction
    rule: PolicyRule | None
    message: str
    context: dict[str, Any]
    requires_confirmation: bool
```

## Plugin System

### Plugin (Abstract Base)

```python
class Plugin(ABC):
    name: str
    version: str
    description: str

    @abstractmethod
    def can_handle(self, command: str) -> bool:
        """Check if plugin can handle command."""

    @abstractmethod
    async def execute(
        self,
        command: str,
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute the command."""
```

### PluginManager

```python
class PluginManager:
    def __init__(self) -> None
    def register_plugin(self, plugin: Plugin) -> None
    def get_plugin_for_command(self, command: str) -> Plugin | None
    def list_plugins(self) -> list[dict[str, Any]]
```

## Sandbox Manager

### SandboxManager

```python
class SandboxManager:
    def __init__(self, backend: str = "chroot")
```

**Methods:**

#### create_sandbox()

```python
def create_sandbox(
    self,
    user_id: str,
    config: SandboxConfig | None = None,
) -> Sandbox
```

#### execute_in_sandbox()

```python
def execute_in_sandbox(
    self,
    sandbox_id: str,
    command: str,
    timeout: int | None = None,
) -> dict[str, Any]
```

#### destroy_sandbox()

```python
def destroy_sandbox(self, sandbox_id: str) -> bool
```

### SandboxConfig

```python
@dataclass
class SandboxConfig:
    user_id: str | None = None
    namespace: str = "default"
    cpu_limit: str = "1.0"
    memory_limit: str = "512m"
    disk_limit: str = "1g"
    network_mode: str = "none"
    allowed_hosts: list[str] = field(default_factory=list)
    read_only_paths: list[str] = field(default_factory=list)
    writable_paths: list[str] = field(default_factory=list)
    command_timeout: int = 30
    max_session_duration: int = 3600
    drop_capabilities: bool = True
    no_new_privileges: bool = True
```

## Recovery Engine

### RecoveryEngine

```python
class RecoveryEngine:
    def suggest_alternatives(self, command: str) -> list[CommandSuggestion]
    def explain_block(self, command: str, rule_id: str | None) -> str
    def get_learning_suggestion(self, command: str, output: str) -> str | None
```

### CommandSuggestion

```python
@dataclass
class CommandSuggestion:
    original: str
    suggestion: str
    reason: str
    confidence: float  # 0.0 to 1.0
    safe: bool
```

## Cost Tracker

### CostTracker

```python
class CostTracker:
    def __init__(
        self,
        enabled: bool = True,
        default_model: str = "gpt-3.5-turbo",
        log_file: str | Path | None = None,
    )
```

**Methods:**

#### track()

```python
@contextmanager
def track(
    self,
    command: str = "",
    user_id: str = "",
    model: str | None = None,
) -> Generator[CostContext, None, None]
```

**Usage:**
```python
with tracker.track(command="ls", user_id="user1") as ctx:
    ctx.add_tokens(prompt_tokens=100, completion_tokens=50)
    # ... execute command ...
```

#### get_user_stats()

```python
def get_user_stats(self, user_id: str) -> dict[str, Any]
```

**Returns:**
```python
{
    "user_id": str,
    "total_commands": int,
    "total_tokens": int,
    "total_cost_usd": float,
    "average_cost_per_command": float,
}
```

#### get_global_stats()

```python
def get_global_stats(self) -> dict[str, Any]
```

### TokenUsage

```python
@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: TokenUsage) -> None
```

## Playbook Generator

### PlaybookGenerator

```python
class PlaybookGenerator:
    def export(
        self,
        history: list[CommandRecord],
        format_type: str = "ansible",
    ) -> str
```

**Formats:**
- `"ansible"` - Ansible playbook (YAML)
- `"terraform"` - Terraform configuration (HCL)
- `"shell"` - Shell script (Bash)

### CommandRecord

```python
@dataclass
class CommandRecord:
    command: str
    timestamp: str
    user: str
    output: str | None = None
    success: bool = True
```

## CLI Commands

### execute

```bash
sysadmin-ai execute [OPTIONS] COMMAND
```

**Options:**
- `--dry-run, -n` - Preview without executing
- `--user, -u` - User ID for session isolation
- `--no-opa` - Disable OPA policy engine
- `--track-cost` - Track token usage
- `--format, -f` - Output format: rich, json, plain

### check

```bash
sysadmin-ai check [OPTIONS] COMMAND
```

Check if a command would be allowed without executing it.

### export

```bash
sysadmin-ai export [OPTIONS]
```

**Options:**
- `--format, -f` - Output format: ansible, terraform, shell
- `--output, -o` - Output file path
- `--user, -u` - User ID for session

### plugins

```bash
sysadmin-ai plugins
```

List available plugins.

### policies

```bash
sysadmin-ai policies
```

List loaded security policies.

## Exceptions

All components may raise:

- `PolicyViolationError` - Command blocked by policy
- `SandboxError` - Sandbox execution failure
- `PluginError` - Plugin execution failure
- `CostTrackingError` - Cost tracking failure
