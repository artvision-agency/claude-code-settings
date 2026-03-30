# CQRS — Command/Query Separation

## Overview

Separate write operations (commands) from read operations (queries).

```
Commands (write)                    Queries (read)
    │                                   │
    ▼                                   ▼
CommandHandler                     QueryHandler
    │                                   │
    ▼                                   ▼
Domain Model ──events──►           Read Model / View
    │                                   │
    ▼                                   ▼
Write DB                           Read DB (can be same)
```

**Start simple.** Most projects need only command/query DTOs + handlers sharing the same DB. Add separate read models only when read performance demands it.

## Commands (Write Side)

### Command DTO
Immutable data carrier representing intent.

```
immutable class PlaceOrderCommand:
    customerId: String
    items: List<{productId, name, price, quantity}>
    street: String
    city: String
    postalCode: String
    country: String
```

**Rules:**
- Immutable (frozen/readonly)
- Flat structure with primitive types (no domain objects)
- One command per write operation
- Named as imperative: `PlaceOrder`, `CancelOrder`, `AddItem`

### Command Handler
Orchestrates domain logic for one command.

```
class PlaceOrderHandler:
    constructor(orderRepo, eventPublisher, unitOfWork)

    handle(command: PlaceOrderCommand) -> OrderId:
        // 1. Create domain objects
        order = Order.create(newId(), command.customerId)
        for item in command.items:
            order.addItem(item.productId, item.name, Money(item.price), item.quantity)

        // 2. Execute domain logic
        address = Address(command.street, command.city, command.postalCode, command.country)
        order.place(address)

        // 3. Persist within transaction
        with unitOfWork:
            orderRepo.save(order)
            unitOfWork.commit()

        // 4. Publish events AFTER commit
        for event in order.collectEvents():
            eventPublisher.publish(event)

        return order.id
```

**Rules:**
- Constructor injection of all dependencies (ports only)
- Single `handle()` method
- Wrap persistence in UnitOfWork
- Publish events AFTER successful commit
- Return minimum needed (ID, status), not full aggregate

## Queries (Read Side)

### Query DTO

```
immutable class GetOrderQuery:
    orderId: String

immutable class ListCustomerOrdersQuery:
    customerId: String
    status: String? = null
    page: Int = 1
    pageSize: Int = 20
```

### Query Handler

```
class GetOrderHandler:
    constructor(orderRepo)

    handle(query: GetOrderQuery) -> OrderResponse:
        order = orderRepo.findById(query.orderId)
        if not order: throw OrderNotFound(query.orderId)
        return OrderResponse.fromDomain(order)
```

**Note:** For simple reads, query handlers can bypass the domain model and read directly from DB/view for performance. This is acceptable — CQRS separates the paths intentionally.

## Application-Level Ports

```
interface EventPublisher:
    publish(event: DomainEvent) -> void

interface UnitOfWork:
    commit() -> void
    rollback() -> void
    // Context manager / disposable pattern
```

## Event Publishing Flow

```
1. Handler creates/modifies aggregate
2. Aggregate collects events internally
3. Handler persists aggregate (within UoW)
4. UoW commits transaction
5. Handler calls collectEvents() on aggregate
6. Handler publishes events via EventPublisher
7. If commit fails → no events published (correct!)
```

**Never publish events inside the transaction.** If the TX rolls back, events should not be published.
