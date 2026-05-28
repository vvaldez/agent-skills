# Ansible Automation Platform Patterns

> Curated by Vinny Valdez, Chief Architect for Automation, Red Hat FieldCTO NA.
> These patterns are specific to Red Hat Ansible Automation Platform (AAP) —
> Automation Hub content tiers, collection conventions, and AAP-specific security patterns.
>
> For generic Ansible patterns (tagging, idempotency, validation, etc.), see
> [ansible-patterns.md](ansible-patterns.md).
>
> For Red Hat Community of Practice baseline standards, see
> [ansible-cop-baseline.md](ansible-cop-baseline.md).

---

## Module & Collection Priority Order

**MANDATORY**: Always prefer higher-tier content. Moving down the list requires justification.

| Priority | Source | Approval | Examples |
|----------|--------|----------|----------|
| 1. Certified | Red Hat Automation Hub | Use freely | `redhat.rhel_system_roles`, `redhat.satellite` |
| 2. Validated | Red Hat Automation Hub | Document reasoning | `vmware.vmware`, `kubernetes.core` |
| 3. Community | Ansible Galaxy | Requires team approval | `community.vmware`, `community.general` |
| 4. command/shell | Last resort | **Hard stop** — must justify | `ansible.builtin.command`, `ansible.builtin.shell` |

### Rules

1. **Always check Automation Hub first** — certified and validated content is tested,
   supported, and maintained by Red Hat or partners
2. **Document why** when using validated content over certified — e.g., "certified
   collection doesn't cover vCenter 8.x folder operations yet"
3. **Team approval required** for community content — file a brief justification in the
   MR description explaining what certified/validated alternatives were considered
4. **command/shell is a hard stop** — if a native module exists for the operation, use it.
   The only exceptions are:
   - External CLI tools with no Ansible module (e.g., `govc`, `ipmitool`)
   - ESXi hosts with no Python interpreter (`ansible.builtin.raw` only)
   - One-off operations where writing a module would be overkill

### Anti-Patterns

[ANTI-PATTERN] **Don't**: Use `community.vmware` when `vmware.vmware` (validated) covers the operation
```yaml
# BAD: community when validated exists
- community.vmware.vmware_guest:
    hostname: "{{ vcenter }}"
```

[CORRECT] **Do**: Use the highest-tier module available
```yaml
# GOOD: validated content
- vmware.vmware.guest:
    hostname: "{{ vcenter }}"
```

[ANTI-PATTERN] **Don't**: Use `ansible.builtin.command` for operations that have a module
```yaml
# BAD: shelling out when a module exists
- ansible.builtin.command:
    cmd: systemctl restart httpd
```

[CORRECT] **Do**: Use the native module
```yaml
# GOOD: native module with idempotency
- ansible.builtin.systemd:
    name: httpd
    state: restarted
```

---

## Secure Logging Toggle (REQUIRED)

**Pattern**: Every role that uses `no_log: true` MUST expose a `<role>_secure_logging` variable to toggle it. NEVER hardcode `no_log: true` — always use the variable.

### Why?

1. **Debugging**: Hardcoded `no_log: true` makes failures invisible — output shows `censored` with no actionable info
2. **Development**: During role development, you NEED to see govc/API output to fix issues
3. **Production safety**: Defaults to `true` so secrets are hidden unless explicitly disabled
4. **Collection-wide toggle**: Falls back to `my_collection_secure_logging` so one extra var unmasks all roles

### Standard Pattern

Every role with credential-handling tasks:

```yaml
# defaults/main.yml
<role>_secure_logging: "{{ my_collection_secure_logging | default(true) }}"
```

Every task that handles credentials:

```yaml
- name: Clone VM from template
  community.vmware.vmware_guest:
    hostname: "{{ <role>_vcenter_hostname }}"
    password: "{{ <role>_vcenter_password }}"
    # ...
  no_log: "{{ <role>_secure_logging }}"
```

### Usage

```bash
# Normal run (secrets hidden):
ansible-navigator run playbook.yml --mode stdout

# Debug run (secrets visible — use with caution):
ansible-navigator run playbook.yml -e my_collection_secure_logging=false --mode stdout

# Debug single role:
ansible-navigator run playbook.yml -e vm_deploy_secure_logging=false --mode stdout
```

### HARD RULE: no_log value MUST be a variable

`no_log:` must ALWAYS reference the role's `_secure_logging` variable. Never `true`, never `false`, never omitted on credential tasks.

### Anti-Patterns

[ANTI-PATTERN] **Don't**: Hardcode `no_log: true`
```yaml
- name: Auth task
  community.vmware.vmware_guest:
    password: "{{ my_password }}"
  no_log: true  # Can't debug failures! No way to toggle without editing code.
```

[ANTI-PATTERN] **Don't**: Hardcode `no_log: false`
```yaml
- name: Auth task
  community.vmware.vmware_guest:
    password: "{{ my_password }}"
  no_log: false  # Secrets always visible!
```

[ANTI-PATTERN] **Don't**: Skip no_log entirely on credential tasks
```yaml
- name: Auth task
  community.vmware.vmware_guest:
    password: "{{ my_password }}"
  # no_log missing — secrets in output!
```

[CORRECT] **Do**: Always use the role's secure_logging variable
```yaml
- name: Auth task
  community.vmware.vmware_guest:
    password: "{{ my_password }}"
  no_log: "{{ my_role_secure_logging }}"
```

### Scope

Apply `no_log` to tasks that handle:
- Passwords / API tokens in module params or govc environment
- Cloud-init templates containing credentials (RHSM, SSH keys)
- Any `set_fact` that stores credentials (e.g., `__govc_env`)

Do NOT apply `no_log` to tasks that only reference non-secret vars (datacenter names, VM names, file paths).
