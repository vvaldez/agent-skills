# Ansible Patterns

> Curated by Vinny Valdez, Chief Architect for Automation, Red Hat FieldCTO NA.
> Developed since 2014, starting with OpenStack deployments before Red Hat acquired
> Ansible, through 11+ years of production automation architecture.
>
> For Ansible Automation Platform-specific patterns (content tiers, secure logging), see
> [ansible-automation-platform-patterns.md](ansible-automation-platform-patterns.md).
>
> For Red Hat Community of Practice baseline standards, see
> [ansible-cop-baseline.md](ansible-cop-baseline.md).

## Table of Contents

1. [Platform-Specific Inventory Hosts](#platform-specific-inventory-hosts)
2. [Platform Discriminator Variable](#platform-discriminator-variable)
3. [Running Playbooks](#running-playbooks)
4. [Dual Tag Application Pattern](#dual-tag-application-pattern)
5. ["always" Tag for Initialization and Finalization](#always-tag-for-initialization-and-finalization)
6. [Lifecycle Phase Tags](#lifecycle-phase-tags)
7. [Teardown with "never" Tag](#teardown-with-never-tag)
8. [Argument Specifications (REQUIRED)](#argument-specifications-required)
9. [Task File Organization](#task-file-organization)
10. [Running Roles with Tags](#running-roles-with-tags)
11. [Why Tag All Tasks?](#why-tag-all-tasks)
12. [Tag Inheritance Bug](#tag-inheritance-bug)
13. [Standard Tag Patterns](#standard-tag-patterns)
14. [Common Tag Combinations](#common-tag-combinations)
15. [Testing Tag Behavior](#testing-tag-behavior)
16. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
17. [Tag Inheritance Caveat: The `never` Tag Can Be Overridden](#tag-inheritance-caveat-the-never-tag-can-be-overridden)
18. [Idempotent External Tool Operations](#idempotent-external-tool-operations)
19. [Never Shell Out to SSH](#never-shell-out-to-ssh)
20. [Use assert Over fail Module](#use-assert-over-fail-module)
21. [Avoid set_fact with loop for Data Filtering](#avoid-setfact-with-loop-for-data-filtering)
22. [Always Use loop_control.loop_var](#always-use-loopcontrolloopvar)
23. [Use Handlers for Final User Output](#use-handlers-for-final-user-output)
24. [Playbook Level](#playbook-level)
25. [Role Level](#role-level)
26. [Task Level](#task-level)
27. [Overall Principles](#overall-principles)
28. [ISO Building Patterns](#iso-building-patterns)
30. [Core Architecture](#core-architecture)
31. [NoCloud ISO for Cloud-Init (Lightweight)](#nocloud-iso-for-cloud-init-lightweight)
32. [Full Kickstart ISO (Heavy - Baremetal/Full Install)](#full-kickstart-iso-heavy---baremetalfull-install)
33. [Playbook Calling Pattern](#playbook-calling-pattern)
34. [Key Variables](#key-variables)
35. [Important Notes](#important-notes)

---


## Table of Contents

1. [Playbook-Level Patterns](#playbook-level-patterns)
2. [Role-Level Patterns](#role-level-patterns)
3. [Task Tagging Patterns](#task-tagging-patterns)
4. [Idempotent Operations](#idempotent-operations)
5. [SSH via Command Module (Anti-Pattern)](#ssh-via-command-module-anti-pattern)
6. [Validation Patterns](#validation-patterns)

---

# Playbook-Level Patterns

## Platform-Specific Inventory Hosts

**Pattern**: Always target platform-specific inventory hosts rather than `localhost` for clarity and consistency.

### Available Inventory Hosts

**openshift_api**:
- Use for: OpenShift/KubeVirt platform operations
- Connection: local (via Kubernetes Python client)
- Context: OpenShift Cluster
- Example: Managing VMs via kubernetes.core modules

**vcenter_api**:
- Use for: vCenter platform operations
- Connection: local (via VMware Python SDK - pyvmomi)
- Context: vCenter Cluster
- Example: Managing VMs via vmware.vmware or community.vmware modules

**localhost**:
- Use for: Platform-agnostic utilities, file operations, local commands
- Connection: local
- Example: Building containers, running local scripts

### Playbook Structure Pattern

```yaml
---
# Descriptive title indicating platform
- name: <Action> for <Platform>
  hosts: <platform>_api  # Use openshift_api or vcenter_api
  gather_facts: true
  connection: local

  vars_files:
    - ../vars/vault.yml

  vars:
    my_platform: "{{ vault_platform }}"  # Platform discriminator
    # Platform-specific variables here

  pre_tasks:
    - name: Display <platform> information
      ansible.builtin.debug:
        msg:
          - "=========================================="
          - "<Platform> <Action>"
          - "=========================================="
          - "Platform: {{ my_platform }}"
          # Additional context here

    - name: Verify platform is set to <platform>
      ansible.builtin.assert:
        that:
          - my_platform == "<platform>"
        fail_msg: "Platform must be '<platform>' in vault.yml"
        success_msg: "Platform confirmed: <Platform>"

  roles:
    - role: my_namespace.my_collection.<role_name>
      vars:
        # Role-specific variables
      tags:
        - <tag>

  post_tasks:
    - name: Display completion summary
      ansible.builtin.debug:
        msg:
          - "=========================================="
          - "✓ <Platform> <Action> Complete"
          - "=========================================="
```

### Why Use Platform-Specific Hosts?

1. **Clarity**: Playbook execution output shows `[vcenter_api]` or `[openshift_api]` instead of generic `[localhost]`
2. **Context**: Immediately clear which platform is being targeted
3. **Extensibility**: Easy to add platform-specific variables or behaviors in inventory
4. **Consistency**: Matches pattern used in setup-test-environment.yml
5. **Debugging**: Easier to trace which platform a task is running against

## Platform Discriminator Variable

Always use `my_platform` variable to control platform-specific behavior:

```yaml
vars:
  my_platform: "{{ vault_platform }}"  # From vault.yml: "openshift" or "vcenter"
```

Roles use this variable to include the correct platform-specific task file:

```yaml
# roles/platform_auth/tasks/main.yml
- name: Include platform-specific authentication tasks
  ansible.builtin.include_tasks: "{{ platform_auth_platform }}.yml"
```

## Running Playbooks

### With Inventory (Recommended)

```bash
ansible-playbook --inventory playbooks/inventory.yml \
  playbooks/test-vcenter.yml \
  --vault-password-file ~/.ansible/vault_password
```

### Without Inventory (Not Recommended)

```bash
# This works but shows generic [localhost] in output
ansible-playbook playbooks/test-vcenter.yml \
  --vault-password-file ~/.ansible/vault_password
```

---

# Role-Level Patterns

## Dual Tag Application Pattern

**Pattern**: When using `include_tasks`, apply tags BOTH at the task level AND in the `apply` directive to ensure proper tag propagation.

### Why Dual Tags?

Tags on `include_tasks` alone don't propagate to included tasks. The `apply` directive ensures tags are inherited by all tasks in the included file.

### Standard Pattern

```yaml
- name: Include component installation tasks
  ansible.builtin.include_tasks:
    file: install-component.yml
    apply:
      tags:
        - component
        - setup
  tags:
    - component
    - setup
```

**Both locations must have identical tags** to ensure:
1. The include task itself runs when tags match
2. Tasks inside the included file inherit the tags
3. Tag filtering works consistently

### Anti-Pattern

[ANTI-PATTERN] **Don't**: Apply tags only on include_tasks
```yaml
- name: Include tasks
  ansible.builtin.include_tasks:
    file: setup.yml
  tags: [setup]  # Tags won't propagate to included tasks!
```

[CORRECT] **Do**: Use dual tag application
```yaml
- name: Include tasks
  ansible.builtin.include_tasks:
    file: setup.yml
    apply:
      tags: [setup]
  tags: [setup]
```

## "always" Tag for Initialization and Finalization

**Pattern**: Use `always` tag for tasks that must run regardless of tag filters (authentication, validation, cleanup).

### Initialization Pattern

```yaml
- name: Include pre-validation tasks
  ansible.builtin.include_tasks:
    file: pre-validate.yml
    apply:
      tags:
        - always
  tags:
    - always
```

### Finalization with block/always

```yaml
- name: Main deployment tasks
  block:
    - name: Include setup tasks
      ansible.builtin.include_tasks:
        file: setup.yml
        apply:
          tags: [setup]
      tags: [setup]

    - name: Include installation tasks
      ansible.builtin.include_tasks:
        file: install.yml
        apply:
          tags: [install]
      tags: [install]

  always:
    - name: Include cleanup tasks
      ansible.builtin.include_tasks:
        file: cleanup.yml
        apply:
          tags:
            - always
      tags:
        - always
```

**Why use block/always**: The `always` section runs even if earlier tasks fail, ensuring cleanup happens regardless of success/failure.

## Lifecycle Phase Tags

**Pattern**: Define clear lifecycle phases as tags to allow granular execution control.

### Common Lifecycle Phases

| Phase | Purpose | Example Tasks |
|-------|---------|---------------|
| `always` | Runs regardless of tag filters | Authentication, validation, cleanup |
| `setup` | Initial environment setup | Create namespaces, folders, prerequisites |
| `templates` | Template/image creation | Upload VMDKs, create base templates |
| `install` | Component installation | Deploy operators, CRs, applications |
| `configure` | Post-install configuration | Apply settings, configure integrations |
| `teardown` | Cleanup/removal | Delete resources (use with `never` tag) |

### Lifecycle Tag Pattern

```yaml
- name: Main role execution
  block:
    # Initialization (always runs)
    - name: Include initialization
      ansible.builtin.include_tasks:
        file: init.yml
        apply:
          tags: [always]
      tags: [always]

    # Setup phase
    - name: Include setup tasks
      when: component_setup_enabled | default(true)
      ansible.builtin.include_tasks:
        file: setup.yml
        apply:
          tags: [setup]
      tags: [setup]

    # Installation phase
    - name: Include installation tasks
      when: component_install_enabled | default(true)
      ansible.builtin.include_tasks:
        file: install.yml
        apply:
          tags: [install]
      tags: [install]

    # Configuration phase
    - name: Include configuration tasks
      when: component_configure_enabled | default(true)
      ansible.builtin.include_tasks:
        file: configure.yml
        apply:
          tags: [configure]
      tags: [configure]

  always:
    # Finalization (always runs)
    - name: Include finalization
      ansible.builtin.include_tasks:
        file: finalize.yml
        apply:
          tags: [always]
      tags: [always]
```

## Teardown with "never" Tag

**Pattern**: Destructive operations must use `never` tag to prevent accidental execution.

```yaml
- name: Include teardown tasks
  ansible.builtin.include_tasks:
    file: teardown.yml
    apply:
      tags:
        - teardown
        - never
  tags:
    - teardown
    - never
```

**Usage**:
- `--tags setup`: Runs setup, skips teardown
- `--tags teardown`: Runs ONLY teardown (explicitly requested)
- No tags: Skips teardown (never tag prevents execution)

## Argument Specifications (REQUIRED)

**Pattern**: ALWAYS define argument_specs in `meta/argument_specs.yml` or `meta/main.yml` for role input validation.

### Why Use Argument Specs?

1. **Input Validation**: Ansible validates variable types and requirements before execution
2. **Documentation**: Auto-generates role documentation from specs
3. **IDE Support**: Better autocomplete and type checking
4. **Early Failure**: Catches configuration errors before tasks run
5. **Required by Best Practices**: Professional roles always document their interface

### File Location

**Option 1**: Dedicated file (recommended for complex roles)
```
roles/
  my_role/
    meta/
      argument_specs.yml  # ← Argument specs here
      main.yml            # Galaxy metadata
```

**Option 2**: Embedded in meta/main.yml (simple roles)
```yaml
# meta/main.yml
---
galaxy_info:
  author: Your Name
  description: Role description

argument_specs:
  main:
    short_description: Main entry point
    options:
      # Specs here
```

### Argument Spec Template

```yaml
---
# meta/argument_specs.yml
argument_specs:
  main:
    short_description: "Primary entry point for ROLE_NAME role"
    description:
      - "Detailed description of what this role does"
      - "Multiple lines for comprehensive documentation"

    options:
      # Required string variable
      component_platform:
        description: "Target platform for deployment"
        type: str
        required: true
        choices:
          - openshift
          - vcenter

      # Optional string with default
      component_namespace:
        description: "Kubernetes namespace or vCenter folder"
        type: str
        required: false
        default: "default"

      # Required list
      component_versions:
        description: "List of component versions to deploy"
        type: list
        elements: int
        required: true

      # Optional boolean
      component_validate_certs:
        description: "Validate SSL/TLS certificates"
        type: bool
        required: false
        default: false

      # Sensitive data (no default, required)
      component_password:
        description: "Authentication password"
        type: str
        required: true
        no_log: true  # Prevent logging of sensitive data
```

### Type Reference

| Type | Ansible Type | Example | Notes |
|------|--------------|---------|-------|
| `str` | String | `"value"` | Default for unspecified types |
| `int` | Integer | `42` | Whole numbers only |
| `float` | Float | `3.14` | Decimal numbers |
| `bool` | Boolean | `true` / `false` | Yes/no values |
| `list` | List | `[1, 2, 3]` | Use with `elements` |
| `dict` | Dictionary | `{key: value}` | Nested structures |
| `path` | File path | `"/var/log"` | Validates path format |

## Task File Organization

**Pattern**: Organize task files by lifecycle phase, not by functionality.

### Directory Structure

```
roles/
  component/
    tasks/
      main.yml               # Orchestrator with include_tasks
      pre-validate.yml       # Always runs first
      initialization.yml     # Setup prerequisites
      install-operator.yml   # Install phase
      install-platform.yml   # Install phase
      configure.yml          # Configuration phase
      teardown.yml           # Cleanup (never tag)
      finalization.yml       # Always runs last
```

### main.yml Orchestrator Pattern

```yaml
---
# tasks/main.yml
- name: Include pre-validation
  ansible.builtin.include_tasks:
    file: pre-validate.yml
    apply:
      tags: [always]
  tags: [always]

- name: Main execution block
  block:
    - name: Include initialization
      ansible.builtin.include_tasks:
        file: initialization.yml
        apply:
          tags: [always]
      tags: [always]

    - name: Include operator installation
      when: component_install_operator | default(true)
      ansible.builtin.include_tasks:
        file: install-operator.yml
        apply:
          tags: [install, operator]
      tags: [install, operator]

    - name: Include platform installation
      when: component_install_platform | default(true)
      ansible.builtin.include_tasks:
        file: install-platform.yml
        apply:
          tags: [install, platform]
      tags: [install, platform]

    - name: Include configuration
      when: component_configure | default(true)
      ansible.builtin.include_tasks:
        file: configure.yml
        apply:
          tags: [configure]
      tags: [configure]

  always:
    - name: Include finalization
      ansible.builtin.include_tasks:
        file: finalization.yml
        apply:
          tags: [always]
      tags: [always]

- name: Include teardown tasks
  ansible.builtin.include_tasks:
    file: teardown.yml
    apply:
      tags: [teardown, never]
  tags: [teardown, never]
```

## Running Roles with Tags

```bash
# Run full role (initialization + all phases + finalization)
ansible-playbook playbook.yml

# Run only setup phase (+ always-tagged tasks)
ansible-playbook playbook.yml --tags setup

# Run only installation (+ always-tagged tasks)
ansible-playbook playbook.yml --tags install

# Run multiple phases
ansible-playbook playbook.yml --tags "setup,install"

# Run teardown explicitly (+ always-tagged tasks)
ansible-playbook playbook.yml --tags teardown

# Skip specific phase
ansible-playbook playbook.yml --skip-tags configure
```

---

# Task Tagging Patterns

**Pattern**: ALWAYS tag tasks explicitly. Never leave tasks untagged.

## Why Tag All Tasks?

1. **Tag Inheritance**: Untagged tasks inherit tags from role invocation, causing unexpected execution
2. **Predictable Behavior**: Explicit tags make it clear when tasks run
3. **Filtered Execution**: Users can run specific subsets with `--tags`
4. **Documentation**: Tags serve as inline documentation of task purpose

## Tag Inheritance Bug

When a role is invoked with tags in the playbook:

```yaml
roles:
  - role: my_namespace.my_collection.vm_templates
    tags: [templates, setup]  # ← Role-level tags
```

And tasks inside the role are untagged:

```yaml
- name: Create templates  # ← NO TAGS
  ansible.builtin.debug:
    msg: "Creating..."
```

**What happens**: The untagged task inherits `[templates, setup]` from the role invocation, causing it to run with EITHER `--tags setup` OR `--tags templates`, even if that's not intended.

**Result**: Running `--tags setup` executes ALL untagged tasks, including those in `teardown` blocks if they lack explicit tags.

## Standard Tag Patterns

### Setup/Creation Tasks

Use BOTH functional and workflow tags:

```yaml
- name: Create VM templates
  tags:
    - templates  # Functional: what this creates
    - setup      # Workflow: part of initial setup
  ansible.builtin.command:
    cmd: govc vm.create ...
```

**Why both**: Allows running with `--tags setup` (all setup tasks) OR `--tags templates` (only template tasks).

### Teardown/Cleanup Tasks

Use `never` tag to prevent accidental execution:

```yaml
- name: Delete VM templates
  tags:
    - teardown   # Functional: what this removes
    - never      # Workflow: only run when explicitly requested
  block:
    - name: Confirm deletion
      ansible.builtin.pause:
        prompt: "Type DELETE to confirm"
```

**The `never` tag**: Prevents execution unless explicitly specified with `--tags teardown`.

### Summary/Reporting Tasks

Use `never` if they should only run with explicit tag:

```yaml
- name: Display creation summary
  tags:
    - templates  # Functional: related to templates
    - never      # Only show with explicit --tags templates
  ansible.builtin.debug:
    msg: "Created templates: {{ templates_created }}"
```

## Common Tag Combinations

| Task Type | Tags | Runs With |
|-----------|------|-----------|
| Setup task | `[templates, setup]` | `--tags setup` OR `--tags templates` |
| Teardown task | `[teardown, never]` | `--tags teardown` only |
| Summary | `[templates, never]` | `--tags templates` only |
| Validation | `[validation, setup]` | `--tags setup` OR `--tags validation` |

## Testing Tag Behavior

```bash
# List all tags in a playbook
ansible-playbook playbook.yml --list-tags

# List tasks that would run with specific tags
ansible-playbook playbook.yml --tags setup --list-tasks

# Verify no untagged tasks
grep -E "^- name:" roles/*/tasks/*.yml -A10 | grep -B1 "^  tags:" | grep "name:" | wc -l
```

## Anti-Patterns to Avoid

[ANTI-PATTERN] **Don't**: Leave tasks untagged
```yaml
- name: Some task
  ansible.builtin.debug: ...
```

[ANTI-PATTERN] **Don't**: Use only workflow tags without functional tags
```yaml
- name: Create templates
  tags: [setup]  # Missing 'templates' tag
```

[ANTI-PATTERN] **Don't**: Forget `never` on destructive operations
```yaml
- name: Delete all VMs
  tags: [teardown]  # Missing 'never' - could run accidentally!
```

[CORRECT] **Do**: Tag explicitly with both functional and workflow tags
```yaml
- name: Create templates
  tags: [templates, setup]

- name: Delete templates
  tags: [teardown, never]
```

## Tag Inheritance Caveat: The `never` Tag Can Be Overridden

**CRITICAL**: The `never` tag can be overridden by tag inheritance from playbook-level role invocation, causing destructive operations to run unexpectedly.

### The Problem: Tag Inheritance Overrides `never`

When a role is invoked with tags at the playbook level, those tags are **inherited** by ALL tasks in the role, including `include_tasks` statements:

```yaml
# Playbook
roles:
  - role: my_namespace.my_collection.vm_templates
    tags: [setup]  # ← These tags are inherited by ALL tasks in the role
```

Any `include_tasks` with `never` tag will inherit the role-level tags:

```yaml
# Role tasks file
- name: Include teardown tasks
  ansible.builtin.include_tasks:
    file: teardown.yml
    apply:
      tags: [teardown, never]
  tags: [teardown, never]
  # ← This task now has EFFECTIVE tags: [setup, teardown, never]
```

**Result**: Running `--tags setup` matches the inherited `setup` tag and executes teardown, despite the `never` tag!

### Tag Inheritance vs Tag Propagation

These are two separate mechanisms:

- **Tag Propagation**: Tags flowing from `include_tasks` to tasks INSIDE the included file
  - **Solved by**: Dual tag application pattern (task level + apply directive)

- **Tag Inheritance**: Tags flowing from playbook/role TO the `include_tasks` statement itself
  - **Not solved by**: Dual tag application
  - **Cause of `never` override bug**

### How the `never` Tag Actually Works

From Ansible documentation:
> The special `never` tag will prevent a task from running unless a tag is explicitly requested.

**Key limitation**: `never` only prevents execution when **NO matching tags are found**. If tag inheritance creates a match (e.g., inherited `setup` tag), `never` is overridden.

### Solution 1: Remove Role-Level Tags

**Never apply tags at role invocation level if the role contains `never`-tagged tasks:**

```yaml
# [ANTI-PATTERN] Don't:
roles:
  - role: my_role
    tags: [setup]  # ← Inherited by all tasks, overrides 'never'

# [CORRECT] Do:
roles:
  - role: my_role
    # No tags - let include_tasks control execution
```

**Why this works**: Without role-level tags, `include_tasks` only have their declared tags, allowing `never` to prevent execution unless `--tags teardown` is explicitly specified.

### Solution 2: Separate Playbooks + Runtime Conditional (Best Practice)

**CRITICAL**: Creating separate playbooks alone is NOT sufficient! You must also add a runtime conditional in the role to prevent teardown from executing during setup.

#### Step 1: Create Separate Playbooks

```yaml
# playbooks/setup-environment.yml (creation)
- name: Setup test environment
  hosts: vcenter_api
  roles:
    - role: my_role
      vars:
        my_role_operation: create  # ← Explicit operation mode
      tags: [setup]

# playbooks/teardown-environment.yml (destruction)
- name: Teardown test environment
  hosts: vcenter_api
  roles:
    - role: my_role
      vars:
        my_role_operation: teardown  # ← Signal teardown mode to role
      tags: [teardown]
```

#### Step 2: Add Conditional to Role

**CRITICAL**: Without this conditional, teardown will still run during setup due to tag inheritance!

```yaml
# roles/my_role/tasks/main.yml
- name: Include setup tasks
  ansible.builtin.include_tasks:
    file: setup.yml
    apply:
      tags: [setup]
  tags: [setup]
  when: my_role_operation | default('create') == 'create'

- name: Include teardown tasks
  ansible.builtin.include_tasks:
    file: teardown.yml
    apply:
      tags: [teardown, never]
  tags: [teardown, never]
  when: my_role_operation | default('create') == 'teardown'  # ← Essential!
```

**Why the conditional is required**:
- Tags alone don't prevent execution due to tag inheritance
- The `never` tag is overridden by inherited `setup` tag from role invocation
- Runtime conditional (`when:`) is the only reliable way to prevent execution
- Variable-based control works regardless of tag inheritance

**Usage**:
```bash
# Create resources (my_role_operation defaults to 'create')
ansible-playbook setup-environment.yml

# Destroy resources (my_role_operation set to 'teardown')
ansible-playbook teardown-environment.yml
```

**Why this is the complete solution**:
- [CORRECT] Complete separation of create vs destroy operations
- [CORRECT] Runtime conditional prevents tag inheritance issues
- [CORRECT] Clearer intent (separate playbook + explicit operation variable)
- [CORRECT] Prevents accidental destructive operations even with tag inheritance
- [CORRECT] Easier to add teardown-specific pre-validations
- [CORRECT] Works regardless of how tags are applied at playbook level

### Common Mistakes (Learn from These Failures)

#### [ANTI-PATTERN] Mistake 1: Relying Only on Dual Tag Application

**What was tried**:
```yaml
- name: Include teardown tasks
  ansible.builtin.include_tasks:
    file: teardown.yml
    apply:
      tags: [teardown, never]
  tags: [teardown, never]  # Dual tags applied correctly
```

**Why it failed**: Dual tag application only prevents tag PROPAGATION (include → included tasks), not tag INHERITANCE (playbook → role → include_tasks). When role has `tags: [setup]` at playbook level, that tag is inherited and overrides `never`.

#### [ANTI-PATTERN] Mistake 2: Creating Separate Playbooks Without Conditionals

**What was tried**:
```yaml
# playbooks/teardown.yml
roles:
  - role: my_role
    tags: [teardown]
```

**Why it failed**: The teardown include_tasks is STILL in the role's main.yml file. Running setup playbook with `tags: [setup]` causes tag inheritance, which overrides the `never` tag and executes teardown. The separate playbook provides an alternative way to run teardown, but doesn't PREVENT it from running during setup.

**The fix**: Add `when: my_role_operation == 'teardown'` conditional to the teardown include_tasks.

#### [ANTI-PATTERN] Mistake 3: Assuming `never` Tag Alone is Sufficient

**What was believed**: The `never` tag prevents execution unless explicitly requested with `--tags teardown`.

**Reality**: The `never` tag only works when NO matching tags are found. Tag inheritance from playbook/role level creates a match, overriding `never`.

**The fix**: Use runtime conditionals (`when:`) instead of relying solely on tags for critical execution control.

### Recommended Approach

For roles with destructive operations (teardown, cleanup, deletion):

1. **Use separate playbooks** for setup vs teardown (preferred)
2. **Add runtime conditionals** to teardown include_tasks based on operation variable
3. **Set operation variable** in playbook (e.g., `my_role_operation: teardown`)
4. **If using single playbook**: Remove role-level tags from playbook invocation
5. **Document the caveat** in role README/documentation
6. **Test thoroughly**: Use `--list-tasks` to verify teardown doesn't run with `--tags setup`

### Testing for the Bug

```bash
# Verify teardown doesn't run with setup tags
ansible-playbook playbook.yml --tags setup --list-tasks | grep -i teardown

# Should return nothing - if teardown tasks appear, you have the bug
```

### Key Lessons

1. **Tags are not execution controls** - They're filters. Use `when:` conditionals for critical execution logic.
2. **Tag inheritance is silent** - Playbook/role tags flow down to all tasks, including include_tasks.
3. **`never` is not foolproof** - It can be overridden by inherited tags.
4. **Dual tag application ≠ tag inheritance protection** - These solve different problems.
5. **Separate playbooks alone don't prevent execution** - You must also guard the include_tasks with a conditional.

---

# Idempotent Operations

## Idempotent External Tool Operations

**Pattern**: When using external CLI tools (govc, oc, curl, etc.) instead of native Ansible modules, implement idempotent behavior by checking, validating, and tagging objects.

### The Six-Step Pattern

External tools don't provide Ansible's idempotency guarantees. Follow this pattern to ensure safe, repeatable operations:

#### 1. List Existing Objects

Query for existing objects before attempting creation. Use project-specific metadata to filter when possible.

```yaml
- name: Check if object exists
  ansible.builtin.command:
    cmd: <tool> list <object-type> <filters>
  register: __object_check
  failed_when: false
  changed_when: false
```

#### 2. Validate Existing Objects

If object exists, verify it matches desired state (compare checksums, sizes, attributes).

```yaml
- name: Get local file attributes for comparison
  ansible.builtin.stat:
    path: "{{ local_file_path }}"
  register: __local_file_stat

- name: Set fact for validation
  ansible.builtin.set_fact:
    __object_matches: "{{ __object_check.rc == 0 and <comparison-logic> }}"
```

#### 3. Fail on Mismatch (Default Behavior)

If object exists but doesn't match, fail with detailed diagnostic information for manual review.

```yaml
- name: Fail if object exists but doesn't match desired state
  ansible.builtin.fail:
    msg: |
      Object already exists but doesn't match desired state.

      Object: {{ object_name }}
      Expected: {{ expected_attributes }}
      Found: {{ actual_attributes }}

      To force recreation, set: <role>_force_recreate: true
  when:
    - __object_check.rc == 0
    - not __object_matches
    - not <role>_force_recreate | default(false)
```

#### 4. Provide Override Option

Allow users to force deletion via variable (use with caution).

```yaml
# In defaults/main.yml
<role>_force_recreate: false  # Set to true to force deletion and recreation
```

#### 5. Validate Deletion

When deleting, verify object no longer exists.

```yaml
- name: Verify deletion succeeded
  ansible.builtin.command:
    cmd: <tool> get <object-name>
  register: __deletion_check
  failed_when: __deletion_check.rc == 0
  changed_when: false
```

#### 6. Add Metadata to Created Objects

Tag/annotate objects with creation metadata for future identification.

```yaml
- name: Create object with metadata
  ansible.builtin.command:
    cmd: |
      <tool> create <object>
        --annotation="created_by={{ role_name }}"
        --annotation="created_at={{ ansible_facts['date_time']['iso8601'] }}"
```

### Complete Example: govc VMDK Import

```yaml
- name: Check if VMDK exists in datastore
  ansible.builtin.command:
    cmd: >
      govc datastore.ls -l
      -dc={{ datacenter }}
      -ds={{ datastore }}
      {{ vmdk_name }}
  register: __vmdk_check
  failed_when: false
  changed_when: false

- name: Get local VMDK size
  ansible.builtin.stat:
    path: "{{ local_vmdk_path }}"
  register: __local_vmdk

- name: Validate existing VMDK size
  ansible.builtin.set_fact:
    __vmdk_matches: "{{ __vmdk_check.rc == 0 and (__vmdk_check.stdout_lines[0].split()[0] | int) == __local_vmdk.stat.size }}"

- name: Fail if VMDK exists but size mismatch
  ansible.builtin.fail:
    msg: |
      VMDK exists but size mismatch!
      Remote: {{ __vmdk_check.stdout_lines[0].split()[0] }} bytes
      Local: {{ __local_vmdk.stat.size }} bytes

      Set vm_templates_force_recreate: true to delete and re-upload
  when:
    - __vmdk_check.rc == 0
    - not __vmdk_matches
    - not vm_templates_force_recreate | default(false)

- name: Import VMDK (if doesn't exist or matches)
  ansible.builtin.command:
    cmd: >
      govc import.vmdk
      -dc={{ datacenter }}
      -ds={{ datastore }}
      {{ local_vmdk_path }}
      {{ vmdk_name }}
  when: __vmdk_check.rc != 0
```

### Why Use This Pattern?

1. **Idempotency**: Safe to run multiple times without duplicating resources
2. **Validation**: Ensures remote objects match local expectations
3. **Safety**: Fails instead of silently overwriting mismatched objects
4. **Flexibility**: Provides escape hatch for forced recreation
5. **Traceability**: Metadata helps identify objects created by automation

### Common Pitfalls to Avoid

[ANTI-PATTERN] **Don't**: Create without checking existence
[ANTI-PATTERN] **Don't**: Silently overwrite existing objects
[ANTI-PATTERN] **Don't**: Skip validation when objects exist
[ANTI-PATTERN] **Don't**: Forget to provide override option
[ANTI-PATTERN] **Don't**: Assume CLI tools are idempotent

[CORRECT] **Do**: Check, validate, fail safely, provide override, add metadata

### Applicable Tools

- `govc` (vCenter CLI)
- `oc` (OpenShift CLI)
- `kubectl` (Kubernetes CLI)
- `curl` (HTTP operations)
- `aws` (AWS CLI)
- `az` (Azure CLI)
- `gcloud` (Google Cloud CLI)

### When NOT to Use This Pattern

- Native Ansible modules already provide idempotency
- One-time operations that should never be repeated
- Read-only operations (no state change)

---

# SSH via Command Module (Anti-Pattern)

## Never Shell Out to SSH

**Pattern**: NEVER use `ansible.builtin.command` or `ansible.builtin.shell` to run
`ssh` for remote operations on hosts that have Python. Use Ansible's native connection
system instead.

This is a **hard stop** — the same [tier-list rule](ansible-automation-platform-patterns.md#module--collection-priority-order)
that applies to all command/shell usage applies here. SSH is not an "external tool"
like govc; it is literally what Ansible already does.

### The Anti-Pattern

```yaml
# BAD: Shelling out to ssh inside command module
- name: Restart dnsmasq
  ansible.builtin.command:
    cmd: >-
      ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null
      -i {{ ssh_key_path }}
      {{ ssh_user }}@{{ server_ip }}
      sudo systemctl restart dnsmasq
  delegate_to: localhost
  changed_when: true
```

### The Correct Pattern

```yaml
# GOOD: add_host + delegate_to + native module
- name: Add remote server to in-memory inventory
  ansible.builtin.add_host:
    name: remote_server
    ansible_host: "{{ server_ip }}"
    ansible_user: "{{ ssh_user }}"
    ansible_connection: ssh
    ansible_ssh_private_key_file: "{{ ssh_key_path }}"
    ansible_ssh_common_args: "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    ansible_become_exe: /usr/bin/sudo

- name: Restart dnsmasq
  ansible.builtin.systemd:
    name: dnsmasq
    state: restarted
  delegate_to: remote_server
  become: true
```

### Why This Matters

1. **Bypasses SSH multiplexing** — opens a new TCP connection per task instead of
   reusing Ansible's ControlPersist socket
2. **No privilege escalation** — must hardcode `sudo` in the command string instead
   of using `become: true` with configurable methods
3. **No error handling** — rc=255 (SSH failure) vs rc=1 (command failure) are
   indistinguishable; Ansible's native connection gives `unreachable` vs `failed`
4. **No idempotency** — `changed_when: true` is always a lie; native modules report
   actual change state
5. **No module benefits** — no diff mode, no check mode, no backup files, no
   structured return data
6. **Security** — SSH options hardcoded in task args instead of managed centrally by
   Ansible's connection plugin

### When SSH via Raw IS Justified

ESXi hosts have no Python interpreter. `ansible.builtin.raw` with `delegate_to` and
explicit connection vars is the correct approach for VMFS filesystem operations:

```yaml
- name: Delete ghost directory from VMFS
  ansible.builtin.raw: rm -rf /vmfs/volumes/{{ uuid }}/{{ name }}
  delegate_to: "{{ esxi_host }}"
  vars:
    ansible_connection: ssh
    ansible_user: root
    ansible_password: "{{ esxi_password }}"
```

This is justified because:
- ESXi has no Python (`raw` is the only option)
- VMFS operations cannot be done through vCenter APIs
- It is a documented escalation fallback (ghost-recovery L2/L3)

### Decision Checklist

Before using `ansible.builtin.command` with `ssh`:

1. Does the remote host have Python? → Use `add_host` + `delegate_to` + native module
2. Is there an Ansible module for the operation? → Use it (systemd, copy, replace, etc.)
3. Is `raw` the only option (no Python)? → Justified, but document why in the task name
4. Is this a one-off quick test? → Still use proper patterns; quick hacks become permanent

---

# Validation Patterns

## Use assert Over fail Module

**Pattern**: Use `ansible.builtin.assert` for validation instead of `when` + `fail`.
Always include **both** `fail_msg` and `success_msg` — be explicit about what passed, not just what failed.

### Why Use assert?

1. **Clearer Intent**: Assertions are explicitly for validation
2. **Better Output**: Shows exactly which condition failed
3. **Self-Documenting**: `success_msg` makes playbook output readable on success
4. **Multiple Conditions**: Test multiple requirements in one task

### Standard Pattern

```yaml
- name: Validate required variables
  ansible.builtin.assert:
    that:
      - component_platform is defined
      - component_platform in ['openshift', 'vcenter']
      - component_namespace is defined
      - component_namespace | length > 0
    fail_msg: "Required variables missing or invalid"
    success_msg: "All required variables validated: platform={{ component_platform }}"
```

### Anti-Pattern

[ANTI-PATTERN] **Don't**: Use when + fail
```yaml
- name: Check if platform is defined
  ansible.builtin.fail:
    msg: "component_platform must be defined"
  when: component_platform is not defined
```

[CORRECT] **Do**: Use assert with both messages
```yaml
- name: Validate platform
  ansible.builtin.assert:
    that:
      - component_platform is defined
      - component_platform in ['openshift', 'vcenter']
    fail_msg: "component_platform must be 'openshift' or 'vcenter'"
    success_msg: "Platform validated: {{ component_platform }}"
```

## Avoid set_fact with loop for Data Filtering

**Pattern**: Use Jinja2 filters (`selectattr`, `map`, `zip`) to build filtered subsets
of data. Never use `set_fact` + `loop` + `when` to conditionally accumulate items into
a list.

### Why This Is an Anti-Pattern

1. **Doesn't scale**: Each loop iteration creates a task execution — O(n) task overhead
2. **Hard to debug**: Variable grows across iterations, intermediate state is invisible
3. **Fragile**: Requires initializing the list before the loop and appending with `+`
4. **Slow**: Ansible task overhead per iteration dwarfs the actual data operation

### Anti-Pattern

[ANTI-PATTERN] **Don't**: Loop + set_fact to build a filtered list
```yaml
- name: Initialize list
  ansible.builtin.set_fact:
    my_filtered_items: []

- name: Build filtered list
  ansible.builtin.set_fact:
    my_filtered_items: "{{ my_filtered_items + [item] }}"
  loop: "{{ all_items }}"
  when: item.status == 'active'
```

[ANTI-PATTERN] **Don't**: Loop + set_fact to construct objects from registered results
```yaml
- name: Store details
  ansible.builtin.set_fact:
    my_details: "{{ my_details + [{'name': item.name, 'port': item.stdout | trim}] }}"
  loop: "{{ command_results.results }}"
```

[CORRECT] **Do**: Use Jinja2 filters in a single set_fact (no loop)
```yaml
- name: Build filtered list
  ansible.builtin.set_fact:
    my_filtered_items: >-
      {{ all_items | selectattr('status', 'equalto', 'active') | list }}
```

[CORRECT] **Do**: Use Jinja2 expressions to construct objects
```yaml
- name: Build details from results
  ansible.builtin.set_fact:
    my_details: >-
      {{ command_results.results | map('combine', {})
         | map('dict2items') | list }}
```

### When set_fact Is Acceptable

- **Single assignment** (no loop): `set_fact` to compute a derived value once
- **Conditional assignment** (when, no loop): `set_fact` gated by a condition to set a value
- **State tracking**: `set_fact` to record success/failure of a recovery step (e.g., `__ghost_l1_success`)

The key rule: if you need `loop` on a `set_fact`, replace it with Jinja2 filters.

## Always Use loop_control.loop_var

**Pattern**: Every `loop:` must include `loop_control.loop_var` with a descriptive name.
Never rely on the default `item` variable.

### Why?

1. **Prevents collisions**: Nested loops, included tasks, and `include_tasks` with loops
   all share the `item` namespace — inner loops silently overwrite the outer loop variable
2. **Self-documenting**: `esxi_host` is clearer than `item` in task output
3. **Future-proof**: Adding a parent loop later won't break existing code

### Standard Pattern

```yaml
- name: Rescan storage on all ESXi hosts
  community.vmware.vmware_host_scanhba:
    esxi_hostname: "{{ esxi_host }}"
    refresh_storage: true
  loop: "{{ esxi_hosts_list }}"
  loop_control:
    loop_var: esxi_host
```

### Anti-Pattern

```yaml
# item collides with parent loop in include_tasks context
- name: Rescan storage
  community.vmware.vmware_host_scanhba:
    esxi_hostname: "{{ item }}"
  loop: "{{ esxi_hosts_list }}"
```

### Jinja2 Templates Must Use the loop_var Name

Templates rendered in a loop context must reference the `loop_var` name, not `item`.
If a task uses `loop_var: rhel_ver`, the template must use `{{ rhel_ver }}`:

```yaml
# Task
- name: Write cloud-init user-data
  ansible.builtin.template:
    src: cloud-init-userdata.yml.j2
    dest: "/tmp/cloud-init-rhel{{ rhel_ver }}/user-data"
  loop: "{{ rhel_versions }}"
  loop_control:
    loop_var: rhel_ver
```

```jinja2
{# Template — use rhel_ver, NOT item #}
{% if rhel_ver | int == 8 %}
  - dnf install -y python39
{% else %}
  - dnf install -y python3
{% endif %}
```

### Naming Convention

Use a descriptive name that matches the loop content:
- List of hosts → `loop_var: host_entry`
- List of RHEL versions → `loop_var: rhel_ver`
- List of VMs → `loop_var: vm_info`
- Registered results → `loop_var: vm_result` or `loop_var: teardown_result`

## Use Handlers for Final User Output

**Pattern**: Use handlers to display final messages to users, keeping task output clean.

### Why Use Handlers for User Messages?

1. **Clean Output**: Messages appear at the end, not mixed with task output
2. **Guaranteed Visibility**: Users see important messages in predictable location
3. **No Duplication**: Handler only runs once even if triggered by multiple tasks
4. **Post-Play Context**: Users see messages after all work is done, easier to understand context
5. **Separation of Concerns**: Validation logic separate from user communication

### Standard Pattern

```yaml
# tasks/main.yml
- name: Validate configuration
  ansible.builtin.assert:
    that:
      - config_valid
    quiet: true
  notify: Display validation success

# handlers/main.yml
- name: Display validation success
  ansible.builtin.debug:
    msg:
      - "=========================================="
      - "✓ Configuration Validated Successfully"
      - "=========================================="
      - "All checks passed, ready to proceed"
```

---

# Key Takeaways

## Playbook Level
1. **Always use platform-specific inventory hosts** (openshift_api, vcenter_api)
2. **Use platform discriminator variable** for conditional logic
3. **Verify platform in pre_tasks** before running roles

## Role Level
1. **Always use dual tags** on `include_tasks` (task level + apply directive)
2. **Always tag matters** - Use for initialization, validation, and finalization
3. **Use block/always** for guaranteed cleanup/finalization
4. **Lifecycle phases** provide granular execution control
5. **Never tag teardown** - Prevent accidental destructive operations
6. **Always define argument_specs** - Document and validate role inputs
7. **Organize by phase** - Structure task files by lifecycle, not function

## Task Level
1. **Tag all tasks explicitly** - Never leave tasks untagged
2. **Use both functional and workflow tags** on tasks
3. **Implement idempotency** for external CLI tool operations
4. **Use assert for validation** instead of when + fail
5. **Use handlers for final output** to keep task output clean

## Overall Principles
- **Consistency**: Follow patterns across all playbooks and roles
- **Predictability**: Tag behavior should be explicit and documented
- **Safety**: Prevent accidental destructive operations
- **Clarity**: Code should be self-documenting through structure
- **Maintainability**: Organize by lifecycle phase, not by function

## ISO Building Patterns

## Core Architecture

ISO building follows a 6-phase pipeline:

1. **Inform** - Display configuration and validate inputs
2. **Install** - Ensure ISO tooling is available (genisoimage, syslinux)
3. **Prep** - Source ISO content (mount existing ISO, or create file structure)
4. **Customize** - Template kickstart/cloud-init files, bootloader configs
5. **Build** - Run genisoimage to create the ISO
6. **Post** - Clean up temp dirs, expose ISO path/URL

### Platform Dispatch Pattern

Use `first_found` query for platform-specific task inclusion:

```yaml
- name: Import platform-specific build tasks
  ansible.builtin.include_tasks: '{{ item }}'
  vars:
    params:
      files:
        - '{{ build_iso_type }}/build.yml'
  loop: "{{ query('first_found', params, errors='ignore') }}"
```

This allows clean separation per platform (rhel7, rhel8, vmware_esxi, nocloud) without conditionals.

## NoCloud ISO for Cloud-Init (Lightweight)

For injecting cloud-init into VMs that use the NoCloud datasource (KVM-based RHEL cloud images on vCenter):

### File Structure

A NoCloud ISO contains only two files at the root:

```
/user-data    # cloud-config YAML
/meta-data    # instance identity YAML
```

### meta-data Template

```yaml
instance-id: {{ vm_name }}
local-hostname: {{ vm_name }}
```

### user-data Template (cloud-config)

```yaml
#cloud-config
user: {{ ssh_user }}
password: {{ password }}
chpasswd: { expire: False }
ssh_pwauth: True
ssh_authorized_keys:
  - "{{ ssh_public_key }}"
packages:
  - open-vm-tools
  - openssh-server
runcmd:
  - subscription-manager register --username={{ rhsm_user }} --password={{ rhsm_pass }} --auto-attach
  - systemctl enable sshd
  - systemctl start sshd
  - echo "{{ ssh_user }} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/{{ ssh_user }}
  - chmod 0440 /etc/sudoers.d/{{ ssh_user }}
```

### Building the NoCloud ISO

The ISO must have volume ID `cidata` for cloud-init to detect it:

```yaml
- name: Generate NoCloud ISO via genisoimage
  ansible.builtin.command: >
    genisoimage
      -output {{ output_path }}/{{ vm_name }}-cidata.iso
      -volid cidata
      -joliet
      -rock
      {{ build_dir }}/user-data
      {{ build_dir }}/meta-data
```

**Volume ID `cidata` is mandatory** - cloud-init scans for this label to identify the NoCloud datasource.

### Running genisoimage Without Local Install

On systems where genisoimage isn't available (macOS, minimal containers), use podman:

```yaml
- name: Generate NoCloud ISO via podman
  ansible.builtin.command: >
    podman run --rm
    -v {{ build_dir }}:/data:Z
    registry.access.redhat.com/ubi9/ubi-minimal:latest
    bash -c "microdnf install -y genisoimage >/dev/null 2>&1 &&
    genisoimage -output /data/cidata.iso -volid cidata -joliet -rock /data/user-data /data/meta-data"
```

### Alternative: community.general.iso_create (Pure Python, No Binary Needed)

For macOS or environments without genisoimage, use `community.general.iso_create` (pycdlib):

```yaml
- name: Generate NoCloud ISO
  community.general.iso_create:
    src_files:
      - "{{ build_dir }}/user-data"
      - "{{ build_dir }}/meta-data"
    dest_iso: "{{ build_dir }}/cidata.iso"
    interchange_level: 4
    joliet: 3
    rock_ridge: "1.09"
    vol_ident: cidata
```

### Attaching to vCenter VMs

After creating the ISO, upload and attach as CD-ROM:

```yaml
# Upload to datastore
- name: Upload NoCloud ISO to datastore
  ansible.builtin.command: >
    govc datastore.upload
    -dc={{ datacenter }}
    -ds={{ datastore }}
    {{ local_path }}/cidata.iso
    cloud-init-isos/{{ vm_name }}-cidata.iso

# Add CD-ROM device
- name: Add CD-ROM device to VM
  ansible.builtin.command: >
    govc device.cdrom.add
    -dc={{ datacenter }}
    -vm "{{ vm_path }}"

# Insert ISO into CD-ROM
- name: Insert NoCloud ISO
  ansible.builtin.command: >
    govc device.cdrom.insert
    -dc={{ datacenter }}
    -vm "{{ vm_path }}"
    -ds={{ datastore }}
    cloud-init-isos/{{ vm_name }}-cidata.iso
```

Cloud-init reads the ISO on first boot and applies the user-data configuration.

## Full Kickstart ISO (Heavy - Baremetal/Full Install)

For full OS installation ISOs with embedded kickstart:

### Phase: Prep (Mount and Extract Source ISO)

```yaml
- name: Create temporary mount point
  ansible.builtin.tempfile:
    state: directory
    suffix: ansible_temp
  register: build_iso_temp_dir

- name: Mount source ISO
  ansible.builtin.mount:
    path: "{{ build_iso_temp_dir.path }}"
    src: "{{ build_iso_source }}"
    state: mounted
    fstype: iso9660
    opts: ro

- name: Copy ISO contents to build directory
  ansible.builtin.copy:
    src: "{{ build_iso_temp_dir.path }}/"
    dest: "{{ build_iso_build_dir }}/"
    remote_src: yes

- name: Unmount and cleanup
  ansible.builtin.mount:
    path: "{{ build_iso_temp_dir.path }}"
    src: "{{ build_iso_source }}"
    state: absent
```

### Phase: Customize (Kickstart + Bootloader)

```yaml
- name: Generate kickstart file
  ansible.builtin.template:
    src: "{{ build_iso_type }}/kickstart.cfg.j2"
    dest: "{{ build_iso_build_dir }}/ks.cfg"
```

Bootloader configs (isolinux.cfg, grub.cfg) inject:
- `inst.ks=cdrom:/ks.cfg` - kickstart location
- `ip={{ ip }}::{{ gateway }}:{{ netmask }}:{{ hostname }}:{{ interface }}:none` - static network
- `ifname={{ interface }}:{{ mac }}` - interface binding
- `nameserver={{ nameserver }}` - DNS

### Phase: Build (genisoimage for RHEL 8+)

```yaml
- name: Create custom RHEL 8 ISO
  ansible.builtin.command: >
    genisoimage
      -o {{ output_dir }}/{{ output_name }}
      -J
      -full-iso9660-filenames
      -rock
      -graft-points
      -V "{{ iso_volume_id }}"
      -eltorito-boot isolinux/isolinux.bin
      -eltorito-catalog isolinux/boot.cat
      -no-emul-boot
      -boot-load-size 4
      -boot-info-table
      -eltorito-alt-boot
      -efi-boot images/efiboot.img
      -no-emul-boot
      "{{ build_dir }}/"

- name: Make ISO UEFI-bootable
  ansible.builtin.command: isohybrid --uefi {{ output_dir }}/{{ output_name }}
```

### Volume ID Handling

Extract volume ID from source ISO for bootloader compatibility:

```yaml
- name: Get ISO volume ID
  ansible.builtin.command: isoinfo -d -i {{ build_iso_source }}
  register: isoinfo_output

- name: Parse volume ID
  ansible.builtin.set_fact:
    iso_volume_id: "{{ isoinfo_output.stdout | regex_search('Volume id: (.+)', '\\1') | first }}"
    # Bootloader-safe version replaces spaces with \x20
    iso_volume_id_bootloader_safe: "{{ iso_volume_id | regex_replace(' ', '\\\\x20') }}"
```

## Playbook Calling Pattern

Use `include_role` with a product loop for multi-host, multi-type builds:

```yaml
- name: Build custom ISOs
  hosts: iso_builder
  become: true
  tasks:
    - include_role:
        name: build_iso
      vars:
        build_iso_hostname_full: "{{ host_and_type.0 }}"
        build_iso_hostname: "{{ host_and_type.0.split('.')[0] }}"
        build_iso_type: "{{ host_and_type.1 }}"
      loop: "{{ build_iso_hosts | product(build_iso_types) | list }}"
      loop_control:
        loop_var: host_and_type
```

## Key Variables

```yaml
# Role inputs
build_iso_type: "rhel8"           # Platform type (rhel7, rhel8, vmware_esxi, nocloud)
build_iso_hostname: "myhost"       # Short hostname for output naming
build_iso_header: "| {{ build_iso_type }} for {{ build_iso_hostname }}"  # Task label

# Paths
build_iso_source: "/path/to/source.iso"
build_iso_build_dir: "{{ output_dir }}/build"
build_iso_output_name: "{{ build_iso_type }}-{{ build_iso_hostname }}.iso"

# Required packages
build_iso_packages:
  - syslinux
  - genisoimage

# Network config (for kickstart ISOs)
build_iso_networking:
  public:
    ipaddr: "{{ networks.public.ipaddr }}"
    gateway: "{{ networks.public.gateway }}"
    netmask: "{{ networks.public.subnet | ansible.utils.ipaddr('netmask') }}"
    interface: "{{ networks.public.name }}"
    mac: "{{ networks.public.mac }}"
```

## Important Notes

- **Volume ID `cidata`** is required for NoCloud cloud-init detection
- **isohybrid --uefi** is needed for RHEL 8+ ISOs to boot on UEFI systems
- **genisoimage** is the standard tool; `mkisofs` is an alias in some distros
- On macOS, use podman with a UBI container to run genisoimage, or use `community.general.iso_create` (pure Python)
- Always clean up build directories and temp mount points in post tasks
- Use `remote_src: yes` when copying mounted ISO contents
- The `first_found` query with `errors='ignore'` gracefully handles missing platform files
- Cross-host variable access uses `hostvars[hostname].variable` pattern