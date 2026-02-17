# SysAdmin AI Next

An advanced AI-powered system administration assistant with policy-driven security, plugin extensibility, and intelligent automation.

## Features

1. **Policy Engine (OPA Integration)** - Declarative security policies using Open Policy Agent
2. **Command Dry-Run Mode** - Safe execution preview for CI/CD pipelines
3. **Plugin System** - Custom executors via entry points
4. **LLM-Generated Playbooks** - Export sessions as Ansible/Terraform
5. **Fuzzy Command Recovery** - Smart alternatives when policies block commands
6. **Multi-User Session Isolation** - Per-user sandbox namespaces
7. **Cost Tracking** - Token usage logging per command

## Quick Start

```bash
pip install sysadmin-ai-next
sysadmin-ai --help
```

## Architecture

```
sysadmin-ai-next/
├── src/
│   └── sysadmin_ai/
│       ├── __init__.py
│       ├── cli.py              # Main entry point
│       ├── policy/             # OPA policy engine
│       ├── plugins/            # Plugin system
│       ├── sandbox/            # Session isolation
│       ├── playbooks/          # LLM playbook generation
│       ├── recovery/           # Fuzzy command recovery
│       └── cost/               # Token tracking
├── policies/                   # Rego policy files
├── tests/
└── docs/
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
