# Architecture Documentation

## Overview

SysAdmin AI Next is built with a modular architecture that separates concerns into distinct components while providing a unified interface through the `SysAdminAI` core class.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                            │
│                    (click, rich)                            │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                      Core API                               │
│                   SysAdminAI Class                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │   Policy    │ │   Plugin    │ │      Sandbox        │   │
│  │   Engine    │ │   Manager   │ │      Manager        │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │  Recovery   │ │   Cost      │ │     Playbook        │   │
│  │   Engine    │ │   Tracker   │ │    Generator        │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                    External Services                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │    OPA      │ │   Docker    │ │   Kubernetes        │   │
│  │   Server    │ │   (opt)     │ │    (opt)            │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Policy Engine

**Purpose:** Security policy evaluation and enforcement

**Key Classes:**
- `PolicyEngine` - Main evaluation engine
- `PolicyRule` - Individual rule definition
- `PolicyResult` - Evaluation result

**Flow:**
1. Command received
2. Check against OPA server (if available)
3. Fall back to local evaluation
4. Return allow/block/confirm decision

**Integration Points:**
- OPA HTTP API
- Rego policy files
- Core API callback

### 2. Plugin System

**Purpose:** Extensible command execution via entry points

**Key Classes:**
- `Plugin` (abstract base)
- `PluginManager` - Discovery and execution

**Entry Point Group:** `sysadmin_ai.plugins`

**Built-in Plugins:**
- `DockerPlugin` - Docker command safety
- `KubectlPlugin` - Kubernetes namespace protection
- `GitPlugin` - Git destructive operation warnings

### 3. Sandbox Manager

**Purpose:** Per-user isolated execution environments

**Key Classes:**
- `SandboxManager` - Sandbox lifecycle
- `Sandbox` - Individual sandbox instance
- `SandboxConfig` - Configuration

**Isolation Methods:**
- chroot (default)
- Docker (optional)
- Kubernetes (optional)

**Features:**
- Resource limits (CPU, memory, disk)
- Network isolation
- Filesystem restrictions
- Timeout enforcement

### 4. Recovery Engine

**Purpose:** Suggest safe alternatives for blocked commands

**Key Classes:**
- `RecoveryEngine` - Main suggestion engine
- `CommandSuggestion` - Individual suggestion

**Algorithms:**
- Pattern matching for dangerous commands
- Fuzzy string matching (thefuzz)
- Contextual suggestion based on violations

### 5. Cost Tracker

**Purpose:** Token usage and cost tracking

**Key Classes:**
- `CostTracker` - Main tracker
- `CostContext` - Per-execution context
- `TokenUsage` - Token counting

**Features:**
- Per-user statistics
- Model-based pricing
- Persistent logging
- Global aggregation

### 6. Playbook Generator

**Purpose:** Export sessions as infrastructure code

**Key Classes:**
- `PlaybookGenerator` - Main generator
- `CommandRecord` - Execution record

**Output Formats:**
- Ansible (YAML)
- Terraform (HCL)
- Shell script (Bash)

## Data Flow

### Command Execution Flow

```
User Input
    │
    ▼
┌──────────────┐
│     CLI      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Policy Eng. │ ──► Block? ──► Recovery Engine
└──────┬───────┘      │
       │ Allow        ▼
       │         Suggest alternatives
       ▼
┌──────────────┐
│ Cost Tracker │ ──► Start tracking
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Plugin Manager│ ──► Has plugin? ──► Execute plugin
└──────┬───────┘      │
       │ No           ▼
       │         Return result
       ▼
┌──────────────┐
│    Sandbox   │ ──► Execute in isolation
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Cost Tracker │ ──► Stop tracking, log usage
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Response   │
└──────────────┘
```

## Security Model

### Defense in Depth

1. **Policy Layer** - Declarative rules block dangerous commands
2. **Plugin Layer** - Domain-specific safety checks
3. **Sandbox Layer** - Resource and filesystem isolation
4. **Audit Layer** - Complete logging of all actions

### Trust Boundaries

```
Untrusted Input
      │
      ▼
┌─────────────────────────────────────┐
│  Policy Engine (validation layer)   │
└─────────────────────────────────────┘
      │
      ▼ (if allowed)
┌─────────────────────────────────────┐
│  Plugin System (domain layer)       │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Sandbox (isolation layer)          │
└─────────────────────────────────────┘
      │
      ▼
   System
```

## Extension Points

### Adding a New Plugin

1. Create class inheriting from `Plugin`
2. Implement `can_handle()` and `execute()`
3. Register in `pyproject.toml`:

```toml
[project.entry-points."sysadmin_ai.plugins"]
my_plugin = "my_package:MyPlugin"
```

### Adding a New Policy

1. Create Rego file in `policies/`:

```rego
package sysadmin_ai

default allow := false

allow if {
    # Your conditions
}
```

2. Or add programmatically:

```python
engine.add_rule(PolicyRule(
    name="my_rule",
    pattern=r"pattern",
    action=PolicyAction.BLOCK,
))
```

### Adding a New Output Format

Extend `PlaybookGenerator`:

```python
def _generate_myformat(self, history: list[CommandRecord]) -> str:
    # Generate output
    return output
```

## Performance Considerations

### Policy Evaluation
- OPA server provides sub-millisecond evaluation
- Local fallback adds ~1ms per command
- Rules are compiled once at startup

### Sandbox Creation
- chroot: ~50ms
- Docker: ~2s (image caching helps)
- Reuse sandboxes when possible

### Cost Tracking
- Minimal overhead (~0.1ms per command)
- Async logging to prevent blocking

## Deployment Patterns

### Single User (Local)
```
CLI -> Core API -> Local Sandbox
```

### Multi-User (Shared Server)
```
CLI -> Core API -> User Sandbox -> Isolated Execution
```

### CI/CD Integration
```
Pipeline -> CLI --dry-run -> Policy Check -> Exit Code
```

## Future Extensions

Potential areas for enhancement:

1. **Distributed Policy** - OPA Bundle API for policy distribution
2. **Web UI** - Browser-based interface
3. **Audit Dashboard** - Real-time monitoring
4. **ML-based Detection** - Anomaly detection for commands
5. **Multi-cloud** - AWS/GCP/Azure specific plugins
