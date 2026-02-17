# SysAdmin AI Next

An advanced AI-powered system administration assistant with policy-driven security, plugin extensibility, and intelligent automation.

## Features

### 1. Policy Engine (OPA Integration)

Declarative security policies using Open Policy Agent with local fallback.

```python
from sysadmin_ai.policy import PolicyEngine

engine = PolicyEngine()
result = engine.evaluate("rm -rf /")
# result.allowed = False
# result.action = PolicyAction.BLOCK
```

**Key capabilities:**
- OPA server integration with automatic fallback to local evaluation
- Rego policy file support
- Built-in dangerous command detection
- Custom rule definitions

### 2. Command Dry-Run Mode

Preview commands without executing them - perfect for CI/CD pipelines.

```bash
# Check what would happen
sysadmin-ai execute "apt install nginx" --dry-run

# Validate in CI/CD
sysadmin-ai check "deploy-script.sh"
```

### 3. Plugin System

Custom executors via entry points for extensibility.

```python
from sysadmin_ai.plugins import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"
    
    def can_handle(self, command: str) -> bool:
        return command.startswith("myapp ")
    
    async def execute(self, command: str, context: dict) -> dict:
        # Custom execution logic
        return {"success": True, "output": "..."}
```

Register in `pyproject.toml`:
```toml
[project.entry-points."sysadmin_ai.plugins"]
my_plugin = "my_package:MyPlugin"
```

### 4. LLM-Generated Playbooks

Export sessions as Ansible, Terraform, or shell scripts.

```bash
# Export as Ansible playbook
sysadmin-ai export --format ansible --output deploy.yml

# Export as Terraform
sysadmin-ai export --format terraform --output infrastructure.tf

# Export as shell script
sysadmin-ai export --format shell --output deploy.sh
```

### 5. Fuzzy Command Recovery

Smart alternatives when policies block commands.

```python
from sysadmin_ai.recovery import RecoveryEngine

engine = RecoveryEngine()
suggestions = engine.suggest_alternatives("rm -rf /")
# Returns safe alternatives like:
# - "rm -rf /path/to/specific/directory"
# - "trash-put /path (move to trash)"
```

### 6. Multi-User Session Isolation

Per-user sandbox namespaces for secure execution.

```python
from sysadmin_ai.sandbox import SandboxManager

manager = SandboxManager(backend="chroot")
sandbox = manager.create_sandbox(
    user_id="user123",
    config=SandboxConfig(
        memory_limit="512m",
        network_mode="none",
    )
)
```

### 7. Cost Tracking

Token usage logging per command for budget management.

```python
from sysadmin_ai.cost import CostTracker

tracker = CostTracker()

with tracker.track(command="ls -la", user_id="user123") as ctx:
    ctx.add_tokens(prompt_tokens=100, completion_tokens=50)
    # Execute command...

# Get usage stats
stats = tracker.get_user_stats("user123")
# stats = {"total_commands": 1, "total_tokens": 150, "total_cost_usd": 0.00025}
```

## Installation

```bash
pip install sysadmin-ai-next
```

For development:

```bash
git clone https://github.com/YOUR_USERNAME/sysadmin-ai-next.git
cd sysadmin-ai-next
pip install -e ".[dev]"
```

## Quick Start

### CLI Usage

```bash
# Execute a command with policy checking
sysadmin-ai execute "docker ps"

# Dry run mode
sysadmin-ai execute "rm -rf /tmp/old" --dry-run

# Check if command would be allowed
sysadmin-ai check "apt install nginx"

# List loaded policies
sysadmin-ai policies

# List available plugins
sysadmin-ai plugins
```

### Python API

```python
import asyncio
from sysadmin_ai import SysAdminAI

async def main():
    ai = SysAdminAI(
        user_id="admin",
        enable_opa=True,
        dry_run=False,
        track_costs=True,
    )
    
    result = await ai.execute_command("docker ps")
    print(result["output"])
    
    # Export session as playbook
    playbook = ai.export_session(format_type="ansible")
    print(playbook)

asyncio.run(main())
```

## Configuration

### OPA Integration

Start OPA server:

```bash
docker run -d -p 8181:8181 openpolicyagent/opa:latest run --server
```

The policy engine will automatically use OPA when available, falling back to local evaluation if not.

### Custom Policies

Add Rego policy files to the `policies/` directory:

```rego
package sysadmin_ai

import future.keywords.if

default allow := false

allow if {
    not dangerous_command
}

dangerous_command if {
    input.command == "rm -rf /"
}
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Formatting
black src/ tests/

# Linting
ruff check src/ tests/

# Type checking
mypy src/
```

## Architecture

```
sysadmin-ai-next/
├── src/sysadmin_ai/
│   ├── cli.py              # CLI entry point
│   ├── core.py             # Main orchestrator
│   ├── policy/             # OPA policy engine
│   ├── plugins/            # Plugin system
│   ├── sandbox/            # Session isolation
│   ├── playbooks/          # Playbook generation
│   ├── recovery/           # Fuzzy command recovery
│   └── cost/               # Token tracking
├── policies/               # Rego policy files
├── tests/                  # Test suite
└── docs/                   # Documentation
```

## Security

This tool executes system commands. Always:

1. Review policies before deployment
2. Use `--dry-run` in CI/CD pipelines
3. Enable session isolation for multi-user environments
4. Monitor cost tracking for unexpected usage

## License

MIT License - see LICENSE file for details.
