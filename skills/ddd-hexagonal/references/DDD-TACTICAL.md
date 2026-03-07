# DDD Tactical Patterns (Language-Agnostic)

All examples in pseudocode. See `python.md` or `typescript.md` for language-specific implementations.

## Entity

Identity-based equality. Encapsulates behavior and enforces invariants.

```
class Order extends Entity:
    id: OrderId
    customerId: CustomerId
    status: OrderStatus = DRAFT
    items: List<OrderLineItem> = []
    events: List<DomainEvent> = []

    static create(id, customerId) -> Order:
        return new Order(id, customerId, DRAFT)

    addItem(productId, name, price, quantity):
        item = new OrderLineItem(productId, name, price, quantity)
        this.items.append(item)

    place(shippingAddress):
        if items.isEmpty(): throw EmptyOrderError
        if status != DRAFT: throw InvalidStateTransition(status, PLACED)
        this.shippingAddress = shippingAddress
        this.status = PLACED
        this.events.append(OrderPlaced(id, customerId, total))

    cancel(reason):
        if status in [SHIPPED, DELIVERED]: throw InvalidStateTransition
        this.status = CANCELLED
        this.events.append(OrderCancelled(id, reason))

    collectEvents() -> List<DomainEvent>:
        result = copy(events)
        events.clear()
        return result
```

**Rules:**
- Factory method (`create`) instead of raw constructor
- All state changes through behavior methods
- Invariants enforced inside the entity
- Domain events collected, not published immediately

## Value Object

Equality by value. Immutable. Self-validating.

```
immutable class Money:
    amount: Decimal
    currency: String = "USD"

    validate():
        if amount < 0: throw "Money cannot be negative"

    add(other: Money) -> Money:
        if currency != other.currency: throw "Currency mismatch"
        return new Money(amount + other.amount, currency)

immutable class Address:
    street: String
    city: String
    postalCode: String
    country: String

immutable class Email:
    value: String

    validate():
        if not contains(value, "@"): throw "Invalid email"
```

**Rules:**
- Always immutable (frozen/readonly)
- Validation in constructor
- Operator overloads where meaningful (Money.add)
- No identity — two Moneys with same amount+currency are equal
- Apply where there are validation rules or composite values
- NOT every string needs to be a VO

## Aggregate Root

Consistency boundary. External access only through the root.

```
class Customer (AggregateRoot):
    id: CustomerId
    email: Email
    addresses: List<Address> = []  // internal, managed by root

    addAddress(address: Address):
        if addresses.length >= 5: throw "Maximum 5 addresses"
        addresses.append(address)

    // External code references Customer by ID only
    // Never: customer.addresses[0].modify()
```

**Aggregate Design Rules (Vaughn Vernon):**
1. Model true invariants in consistency boundaries
2. Design small aggregates (~70% should be root + value objects only)
3. Reference other aggregates by **ID only**
4. Use eventual consistency outside the boundary

## Domain Event

Record of something that happened. Named in past tense.

```
class OrderPlaced extends DomainEvent:
    orderId: String
    customerId: String
    total: Money
    occurredAt: DateTime = now()
    eventId: UUID = newUUID()

class OrderCancelled extends DomainEvent:
    orderId: String
    reason: String
```

**Rules:**
- Past tense naming: `OrderPlaced`, `PaymentProcessed`, `ItemShipped`
- Include only data needed by consumers (not full aggregate)
- Auto-generated eventId and timestamp
- Published AFTER transaction commits

## Repository (Port)

Abstract interface in domain layer. One per aggregate.

```
interface OrderRepository:
    findById(id: OrderId) -> Order?
    save(order: Order) -> void
    findByCustomer(customerId: CustomerId) -> List<Order>
```

**Rules:**
- Async methods for all operations
- Return domain entities, not ORM models
- One repository per aggregate root
- No implementation details in signature (no session, no query objects)
- Implementation lives in infrastructure layer

## Domain Service

Stateless logic that doesn't belong to a single entity.

```
class PricingService:
    calculateDiscount(customer: Customer, order: Order) -> Money:
        if customer.isVIP() and order.total > Money(100):
            return order.total * 0.1
        return Money(0)
```

**Use when:**
- Logic involves multiple aggregates
- Logic doesn't naturally belong to one entity
- Stateless computation

## Domain Exception

Specific, meaningful errors.

```
class OrderingError extends DomainError: pass

class EmptyOrderError extends OrderingError:
    message = "Cannot place an order with no items"

class InvalidStateTransition extends OrderingError:
    fromStatus: OrderStatus
    toStatus: OrderStatus
    message = "Cannot transition from {fromStatus} to {toStatus}"
```
