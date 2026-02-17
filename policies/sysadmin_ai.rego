# SysAdmin AI Security Policies

package sysadmin_ai

import future.keywords.if
import future.keywords.in

# Default deny
default allow := false

# Allow if no violations
allow if {
    count(violations) == 0
}

# Collect all violations
violations contains violation if {
    some violation in destructive_violations
}

violations contains violation if {
    some violation in credential_violations
}

violations contains violation if {
    some violation in network_violations
}

violations contains violation if {
    some violation in k8s_violations
}

# Destructive operations
destructive_patterns := [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=.*of=/dev/[sh]d",
    "> /dev/sd",
    "shred",
    "format C:",
]

destructive_violations contains {
    "type": "destructive",
    "severity": "critical",
    "message": sprintf("Destructive operation detected: %s", [pattern]),
} if {
    some pattern in destructive_patterns
    regex.match(pattern, input.command)
}

# Credential access
credential_patterns := [
    "cat /etc/shadow",
    "cat /etc/gshadow",
    "cat .*/.ssh/id_",
    "cat /proc/self/environ",
    "mimikatz",
]

credential_violations contains {
    "type": "credential_access",
    "severity": "high",
    "message": sprintf("Credential access attempt: %s", [pattern]),
} if {
    some pattern in credential_patterns
    regex.match(pattern, input.command)
}

# Network attacks
network_patterns := [
    "curl .*|.*sh",
    "wget .*|.*sh",
    "nc -e",
    "ncat -e",
    "bash -i >",
    "python.*-c.*socket",
]

network_violations contains {
    "type": "network_attack",
    "severity": "high",
    "message": sprintf("Potential network attack: %s", [pattern]),
} if {
    some pattern in network_patterns
    regex.match(pattern, input.command)
}

# Kubernetes safety
k8s_patterns := [
    "kubectl delete.*--force",
    "kubectl delete.*--grace-period=0",
    "kubectl get secret",
    "kubectl exec.*-it",
    "helm delete",
    "helm uninstall",
]

k8s_violations contains {
    "type": "kubernetes",
    "severity": "high",
    "message": sprintf("Dangerous Kubernetes operation: %s", [pattern]),
} if {
    some pattern in k8s_patterns
    regex.match(pattern, input.command)
}

# Graylist - requires confirmation
graylist_patterns := [
    "apt install",
    "yum install",
    "pip install",
    "npm install",
    "systemctl restart",
    "systemctl stop",
    "iptables -A",
    "iptables -D",
    "ufw enable",
    "ufw disable",
]

graylist_match if {
    some pattern in graylist_patterns
    regex.match(pattern, input.command)
}

# Decision output
decision := {
    "allow": allow,
    "violations": violations,
    "requires_confirmation": graylist_match,
    "risk_score": calculate_risk_score,
}

# Calculate risk score based on violations
calculate_risk_score := score if {
    critical_count := count({v | some v in violations; v.severity == "critical"})
    high_count := count({v | some v in violations; v.severity == "high"})
    medium_count := count({v | some v in violations; v.severity == "medium"})
    
    score := (critical_count * 100) + (high_count * 50) + (medium_count * 25)
}
