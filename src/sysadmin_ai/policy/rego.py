"""Rego policy loader for OPA integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RegoPolicyLoader:
    """Loader for Rego policy files."""
    
    def __init__(self, policy_dir: str | Path) -> None:
        """Initialize loader.
        
        Args:
            policy_dir: Directory containing .rego files
        """
        self.policy_dir = Path(policy_dir)
    
    def load_policies(self) -> dict[str, str]:
        """Load all Rego policies from directory.
        
        Returns:
            Dictionary mapping policy names to Rego source code
        """
        policies = {}
        
        if not self.policy_dir.exists():
            return policies
        
        for rego_file in self.policy_dir.glob("*.rego"):
            policy_name = rego_file.stem
            policies[policy_name] = rego_file.read_text()
        
        return policies
    
    def get_policy(self, name: str) -> str | None:
        """Get a specific policy by name."""
        rego_file = self.policy_dir / f"{name}.rego"
        if rego_file.exists():
            return rego_file.read_text()
        return None
    
    def validate_policy(self, name: str) -> dict[str, Any]:
        """Validate a Rego policy.
        
        Returns validation results with errors if any.
        """
        rego_source = self.get_policy(name)
        if not rego_source:
            return {"valid": False, "errors": [f"Policy '{name}' not found"]}
        
        # Basic syntax checks
        errors = []
        
        if "package" not in rego_source:
            errors.append("Missing package declaration")
        
        if "default" not in rego_source and "allow" not in rego_source:
            errors.append("No default or allow rule found")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
    
    def generate_opa_bundle(self, output_path: str | Path) -> None:
        """Generate an OPA bundle from all policies.
        
        Args:
            output_path: Path to write the bundle
        """
        import tarfile
        import io
        
        output_path = Path(output_path)
        
        # Create tar.gz bundle
        with tarfile.open(output_path, "w:gz") as tar:
            # Add .manifest file
            manifest = json.dumps({"revision": "1.0", "roots": ["sysadmin_ai"]})
            manifest_bytes = manifest.encode()
            manifest_info = tarfile.TarInfo(name=".manifest")
            manifest_info.size = len(manifest_bytes)
            tar.addfile(manifest_info, io.BytesIO(manifest_bytes))
            
            # Add all rego files
            for rego_file in self.policy_dir.glob("*.rego"):
                tar.add(rego_file, arcname=f"sysadmin_ai/{rego_file.name}")
