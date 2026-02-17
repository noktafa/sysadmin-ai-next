# SysAdmin AI Security Policies

package sysadmin

import future.keywords.if
import future.keywords.in

# Default deny
default allow := false

# Allow if all checks pass
allow if {
    not dangerous_command
    not destructive_flags
    not sensitive_path_access
    user_has_permission
}

# Dangerous command patterns
dangerous_command if {
    patterns := ["rm -rf /", "mkfs.", "dd if=/dev/zero", "> /dev/sda"]
    pattern := patterns[_]
    contains(lower(input.command), pattern)
}

# Destructive flags
destructive_flags if {
    flags := ["rm -rf", "rm -f /", "--no-preserve-root"]
    flag := flags[_]
    contains(lower(input.command), flag)
}

# Sensitive path access
sensitive_path_access if {
    paths := ["/etc/shadow", "/etc/passwd", "/root/.ssh"]
    path := paths[_]
    contains(input.command, path)
}

# User permission check
user_has_permission if {
    input.user.permissions[_] == "admin"
}

user_has_permission if {
    not requires_admin
}

# Commands requiring admin
requires_admin if {
    admin_cmds := ["useradd", "userdel", "fdisk", "mkfs", "systemctl"]
    cmd := admin_cmds[_]
    startswith(lower(input.command), cmd)
}

# Deny reason
deny_reason := "Dangerous command pattern detected" if {
    dangerous_command
}

deny_reason := "Destructive flags detected" if {
    destructive_flags
}

deny_reason := "Sensitive path access attempted" if {
    sensitive_path_access
}

deny_reason := "Admin privileges required" if {
    not user_has_permission
}
