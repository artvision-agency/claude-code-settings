---
name: ddd-hexagonal-python
description: Domain-Driven Design with Hexagonal (Ports & Adapters) architecture patterns in Python
---

# DDD + Hexagonal Architecture in Python

## Overview

Hexagonal architecture (Ports & Adapters) keeps the domain layer pure and independent of frameworks, databases, and external services. Combined with DDD tactical patterns, it produces a codebase where business rules are testable in isolation and infrastructure is swappable.

## Directory Structure Conventions

```
src/
  bounded_context_name/       # e.g., "ordering", "catalog", "delivery"
    domain/
      __init__.py
      entities.py             # Aggregate roots and entities
      value_objects.py        # Immutable value types
      events.py               # Domain events
      exceptions.py           # Domain-specific exceptions
      repositories.py         # Port interfaces (ABCs)
      services.py             # Domain services (stateless logic)
    application/
      __init__.py
      commands.py             # Command DTOs
      queries.py              # Query DTOs
      command_handlers.py     # Write-side use cases
      query_handlers.py       # Read-side use cases
      ports.py                # Application-level port interfaces
    infrastructure/
      __init__.py
      sqlalchemy_repositories.py  # Adapter implementing repository ports
      orm_models.py               # SQLAlchemy ORM models
      mappers.py                  # Domain <-> ORM mapping
      event_publisher.py          # Adapter for publishing events
    api/
      __init__.py
      routes.py               # FastAPI/Flask routes (driving adapter)
      schemas.py              # Pydantic request/response schemas
tests/
  unit/
    domain/
    application/
  integration/
    infrastructure/
  e2e/
```

## Entity and ValueObject Base Classes

```python
# src/shared/domain/base.py
from __future__ import annotations
import uuid
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class DomainEvent:
    """Base class for all domain events."""

    def __init__(self) -> None:
        self.event_id: str = str(uuid.uuid4())
        self.occurred_at: datetime = datetime.now(timezone.utc)


class Entity(ABC):
    """Base class for entities with identity."""

    id: Any

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass(frozen=True)
class ValueObject(ABC):
    """
    Base class for value objects.
    Frozen dataclass ensures immutability and provides __eq__ / __hash__
    based on all fields automatically.
    """
    pass
```

## Aggregate Root with Domain Events

```python
# src/ordering/domain/entities.py
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List
from src.shared.domain.base import Entity, DomainEvent
from src.ordering.domain.value_objects import Money, Address, OrderLineItem
from src.ordering.domain.events import (
    OrderPlaced,
    OrderConfirmed,
    OrderCancelled,
)
from src.ordering.domain.exceptions import (
    OrderAlreadyCancelled,
    EmptyOrderError,
    InvalidStateTransition,
)


class OrderStatus(Enum):
    DRAFT = "DRAFT"
    PLACED = "PLACED"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


@dataclass
class Order(Entity):
    """Aggregate root for the Order aggregate."""

    id: str
    customer_id: str
    status: OrderStatus
    items: List[OrderLineItem] = field(default_factory=list)
    shipping_address: Address | None = None
    _events: List[DomainEvent] = field(default_factory=list, repr=False)

    @classmethod
    def create(cls, order_id: str, customer_id: str) -> Order:
        return cls(
            id=order_id,
            customer_id=customer_id,
            status=OrderStatus.DRAFT,
        )

    def add_item(self, product_id: str, name: str, price: Money, quantity: int) -> None:
        item = OrderLineItem(
            product_id=product_id,
            name=name,
            unit_price=price,
            quantity=quantity,
        )
        self.items.append(item)

    def place(self, shipping_address: Address) -> None:
        if not self.items:
            raise EmptyOrderError("Cannot place an order with no items")
        if self.status != OrderStatus.DRAFT:
            raise InvalidStateTransition(self.status, OrderStatus.PLACED)

        self.shipping_address = shipping_address
        self.status = OrderStatus.PLACED
        self._events.append(
            OrderPlaced(order_id=self.id, customer_id=self.customer_id, total=self.total)
        )

    def confirm(self) -> None:
        if self.status != OrderStatus.PLACED:
            raise InvalidStateTransition(self.status, OrderStatus.CONFIRMED)
        self.status = OrderStatus.CONFIRMED
        self._events.append(OrderConfirmed(order_id=self.id))

    def cancel(self, reason: str) -> None:
        if self.status == OrderStatus.CANCELLED:
            raise OrderAlreadyCancelled(self.id)
        if self.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            raise InvalidStateTransition(self.status, OrderStatus.CANCELLED)
        self.status = OrderStatus.CANCELLED
        self._events.append(OrderCancelled(order_id=self.id, reason=reason))

    @property
    def total(self) -> Money:
        amount = sum(
            item.unit_price.amount * item.quantity for item in self.items
        )
        currency = self.items[0].unit_price.currency if self.items else "USD"
        return Money(amount=amount, currency=currency)

    def collect_events(self) -> List[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events
```

## Value Objects

```python
# src/ordering/domain/value_objects.py
from dataclasses import dataclass
from decimal import Decimal
from src.shared.domain.base import ValueObject


@dataclass(frozen=True)
class Money(ValueObject):
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(amount=self.amount + other.amount, currency=self.currency)


@dataclass(frozen=True)
class Address(ValueObject):
    street: str
    city: str
    postal_code: str
    country: str


@dataclass(frozen=True)
class OrderLineItem(ValueObject):
    product_id: str
    name: str
    unit_price: Money
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
```

## Domain Events

```python
# src/ordering/domain/events.py
from dataclasses import dataclass
from decimal import Decimal
from src.shared.domain.base import DomainEvent
from src.ordering.domain.value_objects import Money


@dataclass
class OrderPlaced(DomainEvent):
    order_id: str
    customer_id: str
    total: Money

    def __post_init__(self) -> None:
        super().__init__()


@dataclass
class OrderConfirmed(DomainEvent):
    order_id: str

    def __post_init__(self) -> None:
        super().__init__()


@dataclass
class OrderCancelled(DomainEvent):
    order_id: str
    reason: str

    def __post_init__(self) -> None:
        super().__init__()
```

## Repository Pattern (Port + Adapter)

The port is an abstract interface in the domain layer:

```python
# src/ordering/domain/repositories.py
from abc import ABC, abstractmethod
from typing import Optional
from src.ordering.domain.entities import Order


class OrderRepository(ABC):
    """Port: defines what the domain needs from persistence."""

    @abstractmethod
    async def find_by_id(self, order_id: str) -> Optional[Order]:
        ...

    @abstractmethod
    async def save(self, order: Order) -> None:
        ...

    @abstractmethod
    async def find_by_customer(self, customer_id: str) -> list[Order]:
        ...
```

The adapter lives in the infrastructure layer:

```python
# src/ordering/infrastructure/sqlalchemy_repositories.py
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.ordering.domain.entities import Order, OrderStatus
from src.ordering.domain.repositories import OrderRepository
from src.ordering.infrastructure.orm_models import OrderModel, OrderItemModel
from src.ordering.infrastructure.mappers import OrderMapper


class SqlAlchemyOrderRepository(OrderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, order_id: str) -> Optional[Order]:
        stmt = select(OrderModel).where(OrderModel.id == order_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return OrderMapper.to_domain(row)

    async def save(self, order: Order) -> None:
        model = OrderMapper.to_model(order)
        merged = await self._session.merge(model)
        await self._session.flush()

    async def find_by_customer(self, customer_id: str) -> list[Order]:
        stmt = select(OrderModel).where(OrderModel.customer_id == customer_id)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [OrderMapper.to_domain(row) for row in rows]
```

## Application Services and CQRS

Commands and queries are simple dataclasses. Handlers orchestrate the domain:

```python
# src/ordering/application/commands.py
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PlaceOrderCommand:
    customer_id: str
    items: list[dict]  # [{"product_id": ..., "name": ..., "price": ..., "quantity": ...}]
    street: str
    city: str
    postal_code: str
    country: str


@dataclass(frozen=True)
class CancelOrderCommand:
    order_id: str
    reason: str
```

```python
# src/ordering/application/command_handlers.py
import uuid
from src.ordering.domain.entities import Order
from src.ordering.domain.value_objects import Money, Address
from src.ordering.domain.repositories import OrderRepository
from src.ordering.application.commands import PlaceOrderCommand, CancelOrderCommand
from src.ordering.application.ports import EventPublisher, UnitOfWork


class PlaceOrderHandler:
    def __init__(
        self,
        order_repo: OrderRepository,
        event_publisher: EventPublisher,
        uow: UnitOfWork,
    ) -> None:
        self._order_repo = order_repo
        self._event_publisher = event_publisher
        self._uow = uow

    async def handle(self, command: PlaceOrderCommand) -> str:
        order = Order.create(
            order_id=str(uuid.uuid4()),
            customer_id=command.customer_id,
        )

        for item in command.items:
            order.add_item(
                product_id=item["product_id"],
                name=item["name"],
                price=Money(amount=item["price"]),
                quantity=item["quantity"],
            )

        address = Address(
            street=command.street,
            city=command.city,
            postal_code=command.postal_code,
            country=command.country,
        )
        order.place(address)

        async with self._uow:
            await self._order_repo.save(order)
            await self._uow.commit()

        events = order.collect_events()
        for event in events:
            await self._event_publisher.publish(event)

        return order.id
```

## Application-Level Ports

```python
# src/ordering/application/ports.py
from abc import ABC, abstractmethod
from src.shared.domain.base import DomainEvent


class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        ...


class UnitOfWork(ABC):
    @abstractmethod
    async def commit(self) -> None:
        ...

    @abstractmethod
    async def rollback(self) -> None:
        ...

    @abstractmethod
    async def __aenter__(self) -> "UnitOfWork":
        ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        ...
```

## Dependency Injection Without Frameworks

Use a simple composition root:

```python
# src/ordering/composition_root.py
from sqlalchemy.ext.asyncio import AsyncSession
from src.ordering.domain.repositories import OrderRepository
from src.ordering.infrastructure.sqlalchemy_repositories import SqlAlchemyOrderRepository
from src.ordering.infrastructure.event_publisher import RedisEventPublisher
from src.ordering.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from src.ordering.application.command_handlers import PlaceOrderHandler


def create_place_order_handler(session: AsyncSession) -> PlaceOrderHandler:
    order_repo: OrderRepository = SqlAlchemyOrderRepository(session)
    event_publisher = RedisEventPublisher()
    uow = SqlAlchemyUnitOfWork(session)
    return PlaceOrderHandler(
        order_repo=order_repo,
        event_publisher=event_publisher,
        uow=uow,
    )
```

Wire it from the API layer:

```python
# src/ordering/api/routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.ordering.api.schemas import PlaceOrderRequest, OrderResponse
from src.ordering.application.commands import PlaceOrderCommand
from src.ordering.composition_root import create_place_order_handler
from src.shared.infrastructure.database import get_session

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse)
async def place_order(
    request: PlaceOrderRequest,
    session: AsyncSession = Depends(get_session),
):
    handler = create_place_order_handler(session)
    order_id = await handler.handle(
        PlaceOrderCommand(
            customer_id=request.customer_id,
            items=[item.dict() for item in request.items],
            street=request.street,
            city=request.city,
            postal_code=request.postal_code,
            country=request.country,
        )
    )
    return OrderResponse(order_id=order_id, status="PLACED")
```

## Testing DDD Layers in Isolation

### Unit Testing the Domain (no dependencies)

```python
# tests/unit/domain/test_order.py
import pytest
from decimal import Decimal
from src.ordering.domain.entities import Order, OrderStatus
from src.ordering.domain.value_objects import Money, Address
from src.ordering.domain.exceptions import EmptyOrderError, InvalidStateTransition


class TestOrder:
    def test_place_order_emits_event(self):
        order = Order.create("order-1", "customer-1")
        order.add_item("prod-1", "Widget", Money(Decimal("9.99")), 2)
        address = Address("123 Main St", "Springfield", "62701", "US")

        order.place(address)

        assert order.status == OrderStatus.PLACED
        events = order.collect_events()
        assert len(events) == 1
        assert events[0].order_id == "order-1"

    def test_cannot_place_empty_order(self):
        order = Order.create("order-1", "customer-1")
        address = Address("123 Main St", "Springfield", "62701", "US")

        with pytest.raises(EmptyOrderError):
            order.place(address)

    def test_cannot_cancel_delivered_order(self):
        order = Order.create("order-1", "customer-1")
        order.add_item("prod-1", "Widget", Money(Decimal("9.99")), 1)
        order.place(Address("st", "city", "zip", "US"))
        order.confirm()
        order.status = OrderStatus.DELIVERED  # simulate progression

        with pytest.raises(InvalidStateTransition):
            order.cancel("changed mind")
```

### Unit Testing Application Handlers (with fakes)

```python
# tests/unit/application/test_place_order.py
import pytest
from decimal import Decimal
from src.ordering.application.commands import PlaceOrderCommand
from src.ordering.application.command_handlers import PlaceOrderHandler


class FakeOrderRepository:
    def __init__(self):
        self.saved = []

    async def find_by_id(self, order_id):
        return next((o for o in self.saved if o.id == order_id), None)

    async def save(self, order):
        self.saved.append(order)

    async def find_by_customer(self, customer_id):
        return [o for o in self.saved if o.customer_id == customer_id]


class FakeEventPublisher:
    def __init__(self):
        self.published = []

    async def publish(self, event):
        self.published.append(event)


class FakeUnitOfWork:
    async def commit(self): pass
    async def rollback(self): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass


@pytest.mark.asyncio
async def test_place_order_saves_and_publishes():
    repo = FakeOrderRepository()
    publisher = FakeEventPublisher()
    uow = FakeUnitOfWork()
    handler = PlaceOrderHandler(repo, publisher, uow)

    order_id = await handler.handle(PlaceOrderCommand(
        customer_id="cust-1",
        items=[{"product_id": "p1", "name": "Widget", "price": Decimal("10.00"), "quantity": 1}],
        street="123 Main", city="Town", postal_code="12345", country="US",
    ))

    assert len(repo.saved) == 1
    assert repo.saved[0].id == order_id
    assert len(publisher.published) == 1
```

## Anti-Patterns to Avoid

1. **Anemic domain model** -- Do not put all logic in application services. Entities and aggregates should enforce their own invariants.

2. **Leaking infrastructure into the domain** -- The domain layer must never import SQLAlchemy, Redis, or framework-specific modules. Only pure Python and standard library.

3. **Skipping the port interface** -- Always define an ABC in the domain or application layer. Do not let handlers depend directly on concrete adapters.

4. **Giant aggregates** -- Keep aggregates small. If an aggregate grows beyond 3-4 entities, consider splitting into separate bounded contexts.

5. **Using ORM models as domain entities** -- SQLAlchemy models belong in infrastructure. Map them to/from domain entities via explicit mapper functions.

6. **Publishing events inside the transaction** -- Publish domain events after the unit of work commits. If the transaction rolls back, events should not be published.

7. **Circular dependencies between bounded contexts** -- Contexts communicate through domain events or explicit anti-corruption layers, never by importing each other's domain models directly.

8. **Over-engineering value objects** -- Not every string needs to be a value object. Apply value objects where there are validation rules or composite values (Money, Address, Email).
