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
| 1. Certified | Red Hat Automation Hub | Use freely | `ansible.builtin.*`, `vmware.vmware`, `vmware.vmware_rest`, `kubernetes.core`, `redhat.rhel_system_roles`, `redhat.satellite`, `hashicorp.terraform` |
| 2. Validated | Red Hat Automation Hub | Document reasoning | `cloud.vmware_ops`, `cloud.terraform_ops`, `infra.aap_configuration`, `infra.aap_utilities`, `infra.ai` |
| 3. Community | Ansible Galaxy | Requires team approval | `community.vmware`, `community.general`, `community.crypto` |
| 4. command/shell | Last resort | **Hard stop** — must justify | `ansible.builtin.command`, `ansible.builtin.shell`, `ansible.builtin.raw` |

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

[ANTI-PATTERN] **Don't**: Use `community.vmware` when `vmware.vmware` (certified) covers the operation
```yaml
# BAD: community when certified exists
- community.vmware.vmware_guest:
    hostname: "{{ vcenter }}"
```

[CORRECT] **Do**: Use the highest-tier module available
```yaml
# GOOD: certified content
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

---

## AAP Credential Injection Fallback Chain

**Pattern**: Connection and credential variables cascade from AAP-injected
environment variables to inventory variables with an empty-string terminal, so the
same role runs identically from an AAP job template and from a controller.

Consumer-facing inventory vars (`openshift_host`, `openshift_api_key`, ...) are
deliberately unnamespaced — a shared inventory interface across roles, exempt
from role-prefix naming. Role-internal vars still use the `<role>_` and
`__<role>_` prefixes.

### Why?

1. **AAP job templates**: Credential types inject env vars (`K8S_AUTH_*` from the
   target credential, `VMWARE_*` from the source credential, `AAP_*` from the
   controller credential) — the role reads them with `lookup('env', ...)`
2. **Controller runs**: The same variables resolve from inventory when the role runs
   from a laptop/controller with no AAP injection
3. **One interface**: Consumers set inventory vars once; AAP overrides at runtime
4. **Vault-encrypt inventory credentials**: on non-AAP runs the inventory
   terminal holds the real credential — credential-bearing inventory vars must
   be vault-encrypted (`!vault`); plaintext credential values in inventory are
   a violation

### Standard Pattern

```yaml
# defaults/main.yml
my_role_openshift_host: >-
  {{
    lookup('env', 'K8S_AUTH_HOST')
    | default(openshift_host | default('', true), true)
  }}

my_role_openshift_api_key: >-
  {{
    lookup('env', 'K8S_AUTH_API_KEY')
    | default(openshift_api_key | default('', true), true)
  }}

# Bool-typed options need a | bool cast at the chain end (see the generic
# patterns reference): a raw env string must never reach a bool-typed
# argument-spec option.
my_role_openshift_verify_ssl: "{{ (lookup('env', 'K8S_AUTH_VERIFY_SSL')
  | default(openshift_verify_ssl | default(true), true)) | bool }}"
```

On non-AAP runs the inventory terminal holds the real credential — store
credential-bearing inventory vars vault-encrypted:

```yaml
# inventory/host_vars/<controller>.yml
openshift_api_key: !vault |
  $ANSIBLE_VAULT;1.2;AES256;
  <encrypted payload>
```

### Env Var Families

| Credential type | Injects | Resolves |
|-----------------|---------|----------|
| OpenShift target credential | `K8S_AUTH_HOST`, `K8S_AUTH_API_KEY`, `K8S_AUTH_VERIFY_SSL` | Cluster connection |
| vCenter source credential | `VMWARE_HOST`, `VMWARE_USER`, `VMWARE_PASSWORD`, `VMWARE_VALIDATE_CERTS` | Hypervisor connection |
| AAP controller credential | `AAP_HOSTNAME`, `AAP_USERNAME`, `AAP_PASSWORD`, `AAP_TOKEN` | Controller API |

### Empty-String Terminal Is the Exception, Not a Violation

The generic rule "no empty string defaults for required credentials" does NOT apply
to this pattern: the empty string is the fallback-chain terminal for a variable that
is optional as a role variable (the env var provides it under AAP). The contract is
enforced by an entry assert instead:

```yaml
# tasks/pre_validate.yml
- name: pre_validate | Validate required connection variables
  ansible.builtin.assert:
    that:
      - my_role_openshift_host | length > 0
      - my_role_openshift_api_key | length > 0
    fail_msg: >-
      OpenShift connection is required. Set openshift_host and openshift_api_key
      in the inventory (vault-encrypted — plaintext credential values in
      inventory are a violation; or run from AAP where the target credential
      injects K8S_AUTH_HOST and K8S_AUTH_API_KEY).
```

Credentials that are required as plain role variables (no env injection) must NOT
use empty-string defaults — give them no default at all and let the argument spec
or an assert enforce them.
