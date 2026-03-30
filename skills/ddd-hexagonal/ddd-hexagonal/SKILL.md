---
name: ddd-hexagonal
description: >
  Domain-Driven Design + Hexagonal Architecture (Ports & Adapters) + CQRS.
  Language-agnostic patterns with implementations for Python and TypeScript.
  Use when designing domain models, bounded contexts, aggregates, repositories,
  or refactoring to clean layered architecture.
---

# DDD + Hexagonal Architecture

Hexagonal architecture keeps the domain layer pure and independent of frameworks, databases, and external services. Combined with DDD tactical patterns, it produces a codebase where business rules are testable in isolation and infrastructure is swappable.

## When to Use (and When NOT to)

| Use When | Skip When |
|----------|-----------|
| Complex business domain with many rules | Simple CRUD, few business rules |
| Long-lived system (years of maintenance) | Prototype, MVP, throwaway code |
| Multiple entry points (API, CLI, events, bots) | Single entry point, simple script |
| Need to swap infrastructure (DB, broker) | Fixed infrastructure, unlikely to change |
| High test coverage required | Quick scripts, internal tools |

**Start simple. Evolve complexity only when needed.**

## The Dependency Rule

Dependencies point **inward only**. Outer layers depend on inner layers, never the reverse.

```
Infrastructure → Application → Domain
   (adapters)     (use cases)    (core)
```

**Validation:** "Create your application to work without either a UI or a database" — Alistair Cockburn. If you can run your domain logic from tests with no infrastructure, your boundaries are correct.

## Quick Decision Trees

### "Where does this code go?"

```
├─ Pure business logic, no I/O           → domain/
├─ Orchestrates domain + has side effects → application/
├─ Talks to external systems              → infrastructure/
├─ Defines HOW to interact (interface)    → port (domain or application)
└─ Implements a port                      → adapter (infrastructure)
```

### "Entity or Value Object?"

```
├─ Has unique identity that persists      → Entity
├─ Defined only by its attributes         → Value Object
├─ "Is this THE same thing?"              → Entity (identity comparison)
└─ "Does this have the same value?"       → Value Object (structural equality)
```

### "Same Aggregate or separate?"

```
├─ Must be consistent together in one TX  → Same aggregate
├─ Can be eventually consistent           → Separate aggregates
├─ Referenced by ID only                  → Separate aggregates
└─ >10 entities in aggregate              → Split it
```

**Rule:** One aggregate per transaction. Cross-aggregate consistency via domain events.

## Directory Structure

```
src/
├── domain/                    # Core business logic (ZERO external dependencies)
│   ├── {aggregate}/
│   │   ├── entities           # Aggregate root + child entities
│   │   ├── value_objects      # Immutable value types
│   │   ├── events             # Domain events (past tense: OrderPlaced)
│   │   ├── repositories       # Repository interface (DRIVEN PORT)
│   │   ├── services           # Domain services (stateless cross-entity logic)
│   │   └── exceptions         # Domain-specific errors
│   └── shared/
│       └── base               # Entity, ValueObject, DomainEvent base classes
├── application/               # Use cases / orchestration
│   ├── {use-case}/
│   │   ├── commands           # Command DTOs (write operations)
│   │   ├── queries            # Query DTOs (read operations)
│   │   ├── handlers           # Use case implementation
│   │   └── ports              # Application-level port interfaces
│   └── shared/
│       └── unit_of_work       # Transaction abstraction
├── infrastructure/            # Adapters (external concerns)
│   ├── persistence/           # Database adapters (implements repository ports)
│   ├── messaging/             # Message broker adapters
│   ├── http/                  # REST/GraphQL controllers (DRIVING adapter)
│   └── config/
│       └── composition_root   # Dependency injection wiring
└── main                       # Bootstrap / entry point
```

## DDD Building Blocks

| Pattern | Purpose | Layer | Key Rule |
|---------|---------|-------|----------|
| **Entity** | Identity + behavior | Domain | Equality by ID, enforce own invariants |
| **Value Object** | Immutable data + validation | Domain | Equality by value, frozen/readonly |
| **Aggregate** | Consistency boundary | Domain | Only root is referenced externally |
| **Domain Event** | Record of state change | Domain | Past tense naming (`OrderPlaced`) |
| **Repository** | Persistence abstraction | Domain (port) | One per aggregate, not per table |
| **Domain Service** | Cross-entity logic | Domain | Stateless, no side effects |
| **Application Service** | Use case orchestration | Application | Coordinates domain + infra ports |
| **Port** | Interface contract | Domain/Application | Abstract, no implementation details |
| **Adapter** | Port implementation | Infrastructure | Converts external ↔ domain formats |

## Anti-Patterns (CRITICAL)

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| **Anemic Domain Model** | Entities are data bags, all logic in services | Move behavior INTO entities |
| **Leaking Infrastructure** | Domain imports DB/HTTP/framework libs | Domain has ZERO external deps |
| **Skipping Ports** | Controller → Repository directly | Always go through application layer |
| **God Aggregate** | Too many entities, slow transactions | Split into smaller aggregates, use events |
| **Repository per Table** | Breaks aggregate boundaries | One repository per AGGREGATE |
| **ORM as Domain Entity** | ORM model used in business logic | Separate domain entity + mapper |
| **Events Inside TX** | Publishing before commit succeeds | Publish AFTER unit of work commits |
| **Cross-Aggregate TX** | Multiple aggregates in one transaction | Use domain events (eventual consistency) |
| **Over-engineering VOs** | Every string wrapped as Value Object | Apply VOs where validation/composition exists |
| **Premature CQRS** | Adding complexity before needed | Start simple read/write, evolve when needed |

## Implementation Order

1. **Discover the Domain** — Event Storming, conversations with domain experts
2. **Model the Domain** — Entities, value objects, aggregates (no infrastructure)
3. **Define Ports** — Repository interfaces, external service interfaces
4. **Implement Use Cases** — Application services coordinating domain
5. **Add Adapters last** — HTTP, database, messaging implementations
6. **Write tests per layer** — Domain (pure unit), Application (fakes), Infrastructure (integration)

## Reference Documentation

| File | Content |
|------|---------|
| [references/LAYERS.md](references/LAYERS.md) | Layer rules, responsibilities, dependency matrix |
| [references/DDD-TACTICAL.md](references/DDD-TACTICAL.md) | Entities, VOs, aggregates, events — pseudocode |
| [references/HEXAGONAL.md](references/HEXAGONAL.md) | Ports & adapters patterns, naming conventions |
| [references/CQRS.md](references/CQRS.md) | Command/query separation, event publishing |
| [references/TESTING.md](references/TESTING.md) | Testing strategy per layer |
| [references/python.md](references/python.md) | Python + SQLAlchemy + FastAPI implementation |
| [references/typescript.md](references/typescript.md) | TypeScript + Prisma/Drizzle implementation |

## Sources

- Robert C. Martin — [The Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) (2012)
- Alistair Cockburn — [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) (2005)
- Eric Evans — Domain-Driven Design: Tackling Complexity in the Heart of Software (2003)
- Vaughn Vernon — Implementing Domain-Driven Design (2013)
