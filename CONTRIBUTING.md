# Contributing to SysAdmin AI Next

## Development Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/sysadmin-ai-next.git
cd sysadmin-ai-next

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

## Project Structure

```
sysadmin-ai-next/
├── src/sysadmin_ai/          # Main source code
│   ├── policy/               # Policy engine (OPA integration)
│   ├── plugins/              # Plugin system
│   ├── sandbox/              # Session isolation
│   ├── playbooks/            # Playbook generation
│   ├── recovery/             # Fuzzy command recovery
│   └── cost/                 # Token tracking
├── policies/                 # Rego policy files
├── tests/                    # Test suite
└── docs/                     # Documentation
```

## Adding New Features

### Adding a Policy Rule

1. Add rule to `src/sysadmin_ai/policy/engine.py` in `_load_builtin_rules()`
2. Or create a JSON policy file in `policies/`
3. Add tests in `tests/test_policy.py`

### Adding a Plugin

1. Create a new plugin class inheriting from `Plugin`, `ExecutorPlugin`, or `ToolPlugin`
2. Implement required methods
3. Register via entry points in `pyproject.toml`

### Adding Recovery Suggestions

1. Add patterns to `_alternatives` dict in `src/sysadmin_ai/recovery/recovery.py`
2. Include pattern, suggestion, and reason

## Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to all public functions
- Run `black` and `ruff` before committing

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sysadmin_ai --cov-report=html

# Run specific test file
pytest tests/test_policy.py

# Run with verbose output
pytest -vv
```

## Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and PRs where appropriate
