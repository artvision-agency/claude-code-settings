# Layer Rules & Responsibilities

## Layer Dependency Matrix

| Layer | Can Import | Cannot Import |
|-------|-----------|---------------|
| **Domain** | Standard library only | Application, Infrastructure, Frameworks |
| **Application** | Domain | Infrastructure, Frameworks |
| **Infrastructure** | Domain, Application | — (outermost) |
| **API / Presentation** | Application | Domain directly, Infrastructure directly |

## Layer Responsibilities

### Domain Layer
- Entities with behavior (enforce own invariants)
- Value Objects (immutable, self-validating)
- Domain Events (record state changes)
- Repository interfaces (ABCs/interfaces — NOT implementations)
- Domain Services (stateless cross-entity logic)
- Domain Exceptions

**Rules:**
- ZERO framework/library imports (no ORM, no HTTP, no DB)
- Only standard library and other domain modules
- All business rules live here
- No `set*()` methods — use behavior methods (`order.place()`, not `order.setStatus()`)

### Application Layer
- Command/Query DTOs (immutable data carriers)
- Command Handlers (write-side use cases)
- Query Handlers (read-side use cases)
- Application-level port interfaces (EventPublisher, UnitOfWork)

**Rules:**
- Orchestrates domain, does NOT contain business logic
- Depends only on domain layer ports
- Defines transaction boundaries (UnitOfWork)
- No direct infrastructure access

### Infrastructure Layer
- Repository implementations (adapters for domain ports)
- ORM models (separate from domain entities)
- Mappers (domain ↔ ORM conversion)
- External API clients
- Message broker adapters
- Composition Root (DI wiring)

**Rules:**
- Implements port interfaces defined in domain/application
- ORM models are NOT domain entities
- Mapper functions convert between ORM and domain
- Contains all framework-specific code

## Violation Detection

| Violation | How to Detect | Severity |
|-----------|--------------|----------|
| Framework import in domain | `import sqlalchemy/prisma/typeorm` in domain/ | Critical |
| Infrastructure import in domain | `import infrastructure/` in domain/ | Critical |
| Direct DB access in application | SQL/ORM calls in application/ | High |
| Business logic in controller | if/switch on domain state in API layer | High |
| Business logic in repository | Validation/rules in infrastructure/ | Medium |
| Missing port abstraction | Handler depends on concrete adapter | Medium |

## Checklist

### Domain Layer ✓
- [ ] No framework imports
- [ ] Entities have behavior, not just data
- [ ] Value Objects for domain concepts (Money, Email, Address)
- [ ] Repository INTERFACES defined here
- [ ] Domain Events for side effects
- [ ] No `set*()` methods

### Application Layer ✓
- [ ] Use Cases orchestrate, don't decide
- [ ] DTOs for input/output
- [ ] No business logic (if/switch on domain state)
- [ ] Transaction boundaries managed here
- [ ] No HTTP/CLI concerns

### Infrastructure Layer ✓
- [ ] Implements domain interfaces
- [ ] No business logic in repositories
- [ ] External service adapters
- [ ] ORM models separate from entities
- [ ] Explicit mappers (to_domain / to_model)
