# Hexagonal Architecture (Ports & Adapters)

## Overview

```
                    ┌─────────────────────┐
                    │   PRIMARY ACTORS     │
                    │  (Users, External)   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   DRIVING ADAPTERS   │
                    │  (Controllers, CLI,  │
                    │   Message Consumers) │
                    └──────────┬──────────┘
                               │
              ┌────────────────▼────────────────┐
              │          DRIVING PORTS           │
              │       (Input Interfaces)         │
              └────────────────┬────────────────┘
                               │
              ┌────────────────▼────────────────┐
              │        APPLICATION CORE          │
              │  ┌────────────────────────────┐ │
              │  │     APPLICATION LAYER       │ │
              │  │    (Use Cases, Services)    │ │
              │  └─────────────┬──────────────┘ │
              │                │                 │
              │  ┌─────────────▼──────────────┐ │
              │  │       DOMAIN LAYER          │ │
              │  │  (Entities, Value Objects)  │ │
              │  └────────────────────────────┘ │
              └────────────────┬────────────────┘
                               │
              ┌────────────────▼────────────────┐
              │          DRIVEN PORTS            │
              │      (Output Interfaces)         │
              └────────────────┬────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   DRIVEN ADAPTERS    │
                    │  (Repositories, APIs │
                    │   Message Publishers)│
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  SECONDARY ACTORS    │
                    │  (DB, APIs, Queues)  │
                    └─────────────────────┘
```

**Core Rule:** Application Core defines Ports. Adapters implement or use them.

## Ports

### Driving Ports (Input)
How the outside world interacts with our application.

```
interface CreateOrderUseCase:
    execute(command: CreateOrderCommand) -> OrderId
```

- Defined in application layer
- Implemented by application services (handlers)
- Called by driving adapters (controllers)

### Driven Ports (Output)
What our application needs from the outside world.

```
interface OrderRepository:
    save(order: Order) -> void
    findById(id: OrderId) -> Order?

interface PaymentGateway:
    charge(amount: Money, customerId: String) -> PaymentResult

interface EventPublisher:
    publish(event: DomainEvent) -> void
```

- Defined in domain or application layer
- Implemented by infrastructure adapters
- Used by application services

## Adapters

### Driving Adapters
Convert external input into application calls.

```
// HTTP Controller (driving adapter)
class OrderController:
    useCase: CreateOrderUseCase  // depends on PORT, not implementation

    handlePost(request):
        command = CreateOrderCommand.fromRequest(request)
        orderId = useCase.execute(command)
        return Response(201, {orderId})
```

**Types:** REST controllers, GraphQL resolvers, CLI commands, message consumers, scheduled jobs, bot handlers

### Driven Adapters
Implement driven ports with real infrastructure.

```
// PostgreSQL adapter (implements repository port)
class PostgresOrderRepository implements OrderRepository:
    save(order):
        model = OrderMapper.toModel(order)
        db.merge(model)

    findById(id):
        model = db.find(OrderModel, id)
        return model ? OrderMapper.toDomain(model) : null
```

**Types:** Database repositories, HTTP API clients, message publishers, email senders, file storage

### Test Adapters (Fakes)
In-memory implementations for testing.

```
class FakeOrderRepository implements OrderRepository:
    storage: Map<OrderId, Order> = {}

    save(order): storage[order.id] = order
    findById(id): return storage[id]
```

## Composition Root

Wire ports to adapters in one place. No service locator.

```
function createPlaceOrderHandler(session):
    return PlaceOrderHandler(
        orderRepo = PostgresOrderRepository(session),
        eventPublisher = RedisEventPublisher(),
        unitOfWork = DatabaseUnitOfWork(session)
    )
```

Called from the entry point (main, app factory, DI container setup).

## Naming Conventions

| Concept | Naming Pattern | Example |
|---------|---------------|---------|
| Driving port | `{Action}UseCase` | `CreateOrderUseCase` |
| Driven port | `{Domain}Repository`, `{Service}Gateway` | `OrderRepository`, `PaymentGateway` |
| Driving adapter | `{Protocol}{Domain}Controller` | `HttpOrderController` |
| Driven adapter | `{Tech}{Domain}Repository` | `PostgresOrderRepository` |
| Fake adapter | `Fake{Port}` or `InMemory{Port}` | `FakeOrderRepository` |

## Checklist

### Driving Port ✓
- [ ] Interface in application layer
- [ ] Uses domain/application types only
- [ ] No framework types in signature
- [ ] Single responsibility

### Driven Port ✓
- [ ] Interface in domain/application layer
- [ ] No implementation details in signature
- [ ] Uses domain types for return values
- [ ] Can have multiple adapters (real + fake)

### Adapter ✓
- [ ] Implements port interface
- [ ] No business logic
- [ ] Converts between external and domain formats
- [ ] Easily replaceable
