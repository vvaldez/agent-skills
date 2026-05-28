# Ansible Community of Practice — Baseline Standards

> **Source**: [Red Hat Communities of Practice — Automation Good Practices](https://redhat-cop.github.io/automation-good-practices/)
>
> This document captures the community standards for Ansible collections and roles
> as maintained by the Red Hat Community of Practice. For opinionated patterns built
> on top of these standards, see [ansible-patterns.md](ansible-patterns.md).

## Collection Structure

**Organization Level**: Collections at type/landscape level, not individual roles
- Simplifies distribution and Execution Environment builds
- Groups related automation logically

**Namespace Convention**: `namespace.collection_name`
- Example: `fieldcto_na.extractor` (using underscore, not hyphen)
- Clear organizational ownership

## Role Design Principles

### Functional Focus
- Design roles based on **functionality provided**, not software implementation
- Abstract provider differences
- Focus users on outcomes, not technical details

### Entry-Point Interface
- Create simplified entry-point role
- Allow implementation changes without breaking consumers
- Hide complexity behind clean interface

## Variable Management

### Naming Conventions

**User-Facing Variables** (`defaults/main.yml`):
```yaml
# Prefix with role name to avoid namespace collisions
rolename_packages: []
rolename_config_file: /etc/app/config.yaml
rolename_enabled: true
```

**Internal Variables** (`vars/main.yml` or in tasks):
```yaml
# Double underscore prefix for internal use
__rolename_temp_file: /tmp/processing
__rolename_computed_value: "{{ rolename_x | combine(rolename_y) }}"
```

### Variable Files Organization

**Distribution-Specific**:
```yaml
# vars/RedHat.yml
__rolename_packages:
  - httpd
  - mod_ssl

# vars/Debian.yml
__rolename_packages:
  - apache2
  - libapache2-mod-ssl
```

**Loading Strategy** (in tasks/main.yml):
```yaml
- name: Load distribution-specific variables
  include_vars: "{{ item }}"
  with_first_found:
    - "{{ ansible_distribution }}-{{ ansible_distribution_major_version }}.yml"
    - "{{ ansible_distribution }}.yml"
    - "{{ ansible_os_family }}.yml"
    - "default.yml"
```

### Collection-Level Variables

Define implicit variables in collection README:
```yaml
# Collections can define shared variables
# Referenced in role defaults but defined at collection level
namespace_collection_shared_config: /etc/shared
```

## Multi-Platform Support

**Avoid**: Conditional logic scattered in tasks
```yaml
# DON'T DO THIS
- name: Install package
  package:
    name: "{{ 'httpd' if ansible_os_family == 'RedHat' else 'apache2' }}"
```

**Do**: Use variable files
```yaml
# DO THIS
- name: Load OS-specific variables
  include_vars: "{{ ansible_os_family }}.yml"

- name: Install web server
  package:
    name: "{{ __rolename_webserver_package }}"
```

## Provider Management

When supporting multiple providers (Docker, Podman, etc.):

```yaml
# defaults/main.yml
rolename_provider: auto  # auto-detect or explicit choice

# tasks/main.yml
- name: Detect provider if auto
  set_fact:
    __rolename_provider: "{{ detected_provider }}"
  when: rolename_provider == 'auto'

- name: Include provider-specific tasks
  include_tasks: "providers/{{ __rolename_provider }}.yml"
```

## Argument Validation

Use `meta/argument_specs.yml` (Ansible 2.11+):

```yaml
argument_specs:
  main:
    short_description: Configure application
    options:
      rolename_config_file:
        description: Path to configuration file
        type: path
        required: false
        default: /etc/app/config.yaml
      rolename_packages:
        description: Additional packages to install
        type: list
        elements: str
        required: false
        default: []
```

## Security Best Practices

### Secret Management

**Never commit secrets**:
```yaml
# Use Ansible Vault for sensitive data
# vars/vault.yml (encrypted)
vault_api_password: "secret123"  # pragma: allowlist secret
vault_api_token: "abc123xyz"  # pragma: allowlist secret

# Reference in defaults/main.yml
rolename_api_password: "{{ vault_api_password }}"
```

**Provide vault template**:
```yaml
# vars/vault.yml.example (committed, not encrypted)
# Instructions:
# 1. Copy to vars/vault.yml
# 2. Fill in real values
# 3. Encrypt: ansible-vault encrypt vars/vault.yml
vault_api_password: "CHANGE_ME"  # pragma: allowlist secret
vault_api_token: "CHANGE_ME"  # pragma: allowlist secret
```

### No Secrets in Logs

```yaml
# Use no_log for sensitive tasks
- name: Authenticate to API
  uri:
    url: "{{ api_url }}/login"
    method: POST
    body:
      password: "{{ vault_password }}"
  no_log: true  # Prevents password in logs
```

## Documentation Requirements

### README.md Structure

```markdown
# Role Name

Brief description of functionality (outcomes, not implementation).

## Requirements

- Ansible 2.9+
- Python 3.6+
- Required collections

## Role Variables

### User-Facing Variables (defaults/main.yml)
| Variable | Default | Description |
|----------|---------|-------------|
| rolename_enabled | true | Enable the service |

### Collection-Level Variables
Variables defined at collection level.

## Example Playbook

- hosts: servers
  roles:
    - role: namespace.collection.rolename
      rolename_enabled: true

## Idempotency

This role is idempotent and can be run multiple times safely.

## Check Mode

Supports check mode with accurate change reporting.

## License

Apache License 2.0 (or specify)

## Author

Your Name
```

## Quality Checklist

- [ ] Variables namespaced with role name
- [ ] Internal variables use `__` prefix
- [ ] Distribution-specific vars in separate files
- [ ] Argument specs defined (Ansible 2.11+)
- [ ] Idempotent (same result on re-run)
- [ ] Check mode supported
- [ ] No secrets in code or logs
- [ ] Example playbook in README
- [ ] LICENSE file present
- [ ] All tasks have meaningful names
- [ ] Tags defined for selective execution

## Collection-Specific

### galaxy.yml Requirements

Every collection must have a properly formatted `galaxy.yml`:

```yaml
namespace: my_namespace
name: my_collection
version: 1.0.0
readme: README.md
authors:
  - Your Name <email@example.com>
description: Brief description of the collection's purpose
license_file: LICENSE
tags:
  - automation
  - infrastructure
dependencies: {}
repository: https://github.com/org/repo
```

### Directory Structure

```
my_namespace/my_collection/
├── galaxy.yml
├── README.md
├── LICENSE
├── meta/
│   └── runtime.yml
├── docs/
├── plugins/
│   ├── filter/
│   ├── modules/
│   └── module_utils/
├── roles/
│   └── my_role/
│       ├── defaults/main.yml
│       ├── handlers/main.yml
│       ├── meta/
│       │   ├── main.yml
│       │   └── argument_specs.yml
│       ├── tasks/main.yml
│       ├── templates/
│       ├── vars/
│       └── README.md
├── playbooks/
└── tests/
```

## Common Anti-Patterns to Avoid

**Don't**: Global variable names
```yaml
packages: []  # Will collide with other roles
```

**Do**: Namespaced names
```yaml
rolename_packages: []
```

**Don't**: Conditionals everywhere
```yaml
- name: Install
  package:
    name: "{{ 'pkg1' if ansible_os_family == 'RedHat' else 'pkg2' }}"
```

**Do**: Variable-based configuration
```yaml
- include_vars: "{{ ansible_os_family }}.yml"
- package:
    name: "{{ __rolename_package }}"
```

**Don't**: Hardcoded paths
```yaml
config_file: /etc/app/config.yaml
```

**Do**: User-configurable with sensible defaults
```yaml
rolename_config_file: /etc/app/config.yaml
```

## References

- [Red Hat CoP Automation Good Practices](https://redhat-cop.github.io/automation-good-practices/)
- [Ansible Collection Documentation](https://docs.ansible.com/ansible/latest/dev_guide/developing_collections.html)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)