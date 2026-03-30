# Testing Strategy per Layer

## Test Pyramid

```
         ╱╲
        ╱E2E╲          Few — slow, brittle
       ╱──────╲
      ╱Integr. ╲       Medium — real DB, real adapters
     ╱──────────╲
    ╱   Unit     ╲     Many — fast, isolated, no I/O
   ╱──────────────╲
```

## Domain Layer Tests (Unit)

**No mocks, no database, no I/O.** Pure business logic.

### What to Test
- Aggregate invariants: valid and invalid state transitions
- Value Object validation: valid construction + rejection of invalid input
- Domain event emission: correct events after state changes
- Domain services: stateless business logic
- Edge cases: boundary values, null/empty inputs

### Pattern

```
test "placing order emits OrderPlaced event":
    order = Order.create("order-1", "customer-1")
    order.addItem("prod-1", "Widget", Money(9.99), 2)

    order.place(Address("123 Main", "Springfield", "62701", "US"))

    assert order.status == PLACED
    events = order.collectEvents()
    assert events.length == 1
    assert events[0] is OrderPlaced
    assert events[0].orderId == "order-1"

test "cannot place empty order":
    order = Order.create("order-1", "customer-1")

    assertThrows EmptyOrderError:
        order.place(someAddress)

test "Money rejects negative amount":
    assertThrows ValueError:
        Money(-1)

test "Money addition requires same currency":
    assertThrows ValueError:
        Money(10, "USD").add(Money(5, "EUR"))
```

## Application Layer Tests (Unit)

**Use fake implementations of ports.** Verify handler orchestration.

### Fakes

```
class FakeOrderRepository implements OrderRepository:
    saved: List<Order> = []

    save(order): saved.append(order)
    findById(id): return saved.find(o => o.id == id)
    findByCustomer(cid): return saved.filter(o => o.customerId == cid)

class FakeEventPublisher implements EventPublisher:
    published: List<DomainEvent> = []

    publish(event): published.append(event)

class FakeUnitOfWork implements UnitOfWork:
    commit(): pass
    rollback(): pass
```

### Pattern

```
test "PlaceOrderHandler saves order and publishes event":
    repo = FakeOrderRepository()
    publisher = FakeEventPublisher()
    uow = FakeUnitOfWork()
    handler = PlaceOrderHandler(repo, publisher, uow)

    orderId = handler.handle(PlaceOrderCommand(
        customerId = "cust-1",
        items = [{productId: "p1", name: "Widget", price: 10.00, quantity: 1}],
        street = "123 Main", city = "Town", postalCode = "12345", country = "US"
    ))

    assert repo.saved.length == 1
    assert repo.saved[0].id == orderId
    assert publisher.published.length == 1
    assert publisher.published[0] is OrderPlaced
```

## Infrastructure Layer Tests (Integration)

**Use real database** (SQLite in-memory or test container).

### What to Test
- Repository CRUD operations
- Mapper round-trips: domain → ORM → domain preserves all data
- UnitOfWork commit and rollback behavior
- External API client error handling

### Pattern

```
test "repository round-trip preserves order data":
    // Setup real DB (SQLite in-memory)
    session = createTestSession()
    repo = SqlOrderRepository(session)

    // Create and save
    order = Order.create("order-1", "customer-1")
    order.addItem("p1", "Widget", Money(9.99), 2)
    repo.save(order)
    session.commit()

    // Reload and verify
    loaded = repo.findById("order-1")
    assert loaded != null
    assert loaded.items.length == 1
    assert loaded.items[0].unitPrice == Money(9.99)
```

## E2E / API Tests

**Use test client** (FastAPI TestClient, supertest, etc.).

```
test "POST /orders returns 201 with order ID":
    response = client.post("/orders", json = {
        customerId: "cust-1",
        items: [{productId: "p1", name: "Widget", price: 10, quantity: 1}],
        street: "123 Main", city: "Town", postalCode: "12345", country: "US"
    })

    assert response.status == 201
    assert response.json.orderId != null
```

## Coverage Targets

| Layer | Target | Rationale |
|-------|--------|-----------|
| Domain | 90%+ | Core business logic, must be bulletproof |
| Application | 80%+ | Orchestration, verify correct wiring |
| Infrastructure | 60%+ | Integration, harder to test, less logic |
| E2E | Key flows | Happy path + critical error paths |
