# Netflix Conductor to Temporal Python Migration Guide

## Introduction

This guide provides comprehensive instructions for migrating Netflix Conductor JSON workflow definitions to production-ready Temporal Python projects.

**Use this guide when:**
- You have a Conductor JSON workflow definition file
- You want to migrate from Conductor's declarative JSON DSL to Temporal's code-first Python approach
- You need a complete, tested, and documented Temporal project as output

**What this migration produces:**
- Complete Python project with workflows, activities, and worker
- Comprehensive unit and integration tests
- Type-safe code with mypy strict validation
- Full documentation and setup instructions
- End-to-end validated working implementation

---

## Quick Start (TL;DR)

For experienced users who understand both Conductor and Temporal:

1. **Ensure prerequisites**: Python 3.11+, Temporal CLI, UV, jq
2. **Validate Conductor JSON**: `jq empty workflow.json`
3. **Follow migration phases**: Analyze → Generate → Validate → Test
4. **Key mappings**: SIMPLE→Activity, FORK_JOIN→asyncio.gather, SWITCH→if/elif, DO_WHILE→while
5. **Run end-to-end**: Start dev server → Start worker → Execute workflow → Validate
6. **Success criteria**: All tests pass, mypy strict passes, workflow executes successfully

---

## Documentation Structure

This guide is organized into specialized documents for different aspects of the migration process:

### 📚 [Architecture Reference](./conductor-architecture.md)
**Understanding Conductor vs Temporal**

Learn the fundamental architectural differences between Conductor and Temporal, and how to map Conductor concepts to Temporal implementations.

**Topics covered:**
- Core architectural shifts (JSON DSL → Python code)
- Task type mappings (SIMPLE, HTTP, FORK_JOIN, SWITCH, etc.)
- Control flow pattern translations with code examples
- Data passing from JSONPath to Python
- Key differences in determinism, state persistence, and error handling

**Use this when:**
- You're new to Temporal and need to understand the conceptual differences
- You need a reference for how specific Conductor task types map to Temporal
- You're translating complex control flow patterns

---

### 🛠️ [Migration Guide](./conductor-migration-guide.md)
**Step-by-Step Migration Instructions**

Complete, phase-by-phase instructions for migrating a Conductor workflow to Temporal.

**Topics covered:**
- **Prerequisites**: Required tools and setup
- **Phase 1: Analysis & Setup**: Parse Conductor JSON and create project structure
- **Phase 2: Code Generation**: Generate activities, workflows, worker, and starter
- **Phase 3: Testing**: Create comprehensive test suite and validate code
- **Phase 4: Deployment**: End-to-end testing and documentation

**Use this when:**
- You're actively performing a migration
- You need detailed step-by-step instructions for each phase
- You want verification commands and common issues for each step

---

### ✅ [Quality Assurance](./conductor-quality-assurance.md)
**Testing, Validation, and Success Criteria**

Standards and procedures for ensuring your migration meets production-quality requirements.

**Topics covered:**
- Validation procedures (syntax, type checking, tests)
- Migration success criteria and quality gates
- Code quality standards and best practices
- Testing standards (activity tests, workflow tests, integration tests)
- Performance standards and documentation requirements

**Use this when:**
- You need to verify your migration meets quality standards
- You're defining test coverage requirements
- You want to establish quality gates for your project

---

### 🔧 [Troubleshooting Guide](./conductor-troubleshooting.md)
**Solutions to Common Issues**

Comprehensive troubleshooting reference with solutions from real migrations.

**Topics covered:**
- Common migration issues (JSON parsing, timeouts, type errors, etc.)
- **Critical documented pitfalls** with tested solutions:
  - Test dependency not found
  - Workflow sandbox violations (CRITICAL)
  - Incorrect test environment API
  - Wrong RetryPolicy import
- Quick diagnostic checklist
- Next steps after migration
- Reference migration script template

**Use this when:**
- Your migration is failing and you need to diagnose the issue
- You encounter workflow sandbox violations or test failures
- You want to avoid common pitfalls encountered in real migrations
- You need guidance on production readiness and optimization

---

## Getting Started

### First-Time Users
1. Start with the [Architecture Reference](./conductor-architecture.md) to understand the conceptual differences
2. Review prerequisites in the [Migration Guide](./conductor-migration-guide.md)
3. Follow the phase-by-phase instructions in the [Migration Guide](./conductor-migration-guide.md)
4. Use the [Quality Assurance](./conductor-quality-assurance.md) checklist to verify your migration
5. Refer to [Troubleshooting](./conductor-troubleshooting.md) if you encounter issues

### Experienced Users
1. Validate your Conductor JSON: `jq empty workflow.json`
2. Jump directly to [Migration Guide](./conductor-migration-guide.md) Phase 1
3. Use [Troubleshooting](./conductor-troubleshooting.md) Quick Diagnostic Checklist if issues arise
4. Verify completion with [Quality Assurance](./conductor-quality-assurance.md) checklist

---

## Migration Overview

```
┌─────────────────────┐
│  Conductor JSON     │
│  workflow.json      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Phase 1: Analysis  │
│  Parse & Understand │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Phase 2: Generate  │
│  Activities,        │
│  Workflow, Worker   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Phase 3: Testing   │
│  Unit & Integration │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Phase 4: Deploy    │
│  E2E Test & Docs    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Production-Ready   │
│  Temporal Project   │
└─────────────────────┘
```

---

## Key Migration Concepts

### Architectural Shift
**Conductor**: Declarative JSON DSL with external state management
**Temporal**: Imperative Python code with automatic event sourcing

### Control Flow Translation
- **SIMPLE** → Activity function with `@activity.defn`
- **FORK_JOIN** → `asyncio.gather()` for parallel execution
- **SWITCH** → Python `if/elif/else` statements
- **DO_WHILE** → Python `while` loop
- **HTTP** → Activity with httpx client

### Data Passing
- `${workflow.input.field}` → `input.field`
- `${task_ref.output}` → `result_variable`
- JSONPath expressions → Python object access

---

## Success Criteria

Your migration is complete when:

✅ All Python files pass syntax validation
✅ `mypy --strict` passes with no errors
✅ All unit tests pass
✅ End-to-end workflow executes successfully
✅ Documentation is complete
✅ Code follows quality standards

See [Quality Assurance](./conductor-quality-assurance.md) for detailed criteria.

---

## Additional Resources

- **Temporal Documentation**: https://docs.temporal.io/
- **Temporal Python SDK**: https://github.com/temporalio/sdk-python
- **Temporal Samples**: https://github.com/temporalio/samples-python
- **Conductor Documentation**: https://conductor.netflix.com/
- **Community Support**: https://temporal.io/slack

---

## Quick Links

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [Architecture Reference](./conductor-architecture.md) | Understand concepts and mappings | Learning, reference during translation |
| [Migration Guide](./conductor-migration-guide.md) | Step-by-step instructions | Active migration, detailed procedures |
| [Quality Assurance](./conductor-quality-assurance.md) | Standards and validation | Verifying quality, defining requirements |
| [Troubleshooting](./conductor-troubleshooting.md) | Issue resolution | Debugging, avoiding pitfalls |

---

**Ready to begin your migration? Start with the [Architecture Reference](./conductor-architecture.md) or jump straight into the [Migration Guide](./conductor-migration-guide.md)!**
