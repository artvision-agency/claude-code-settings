# Python Implementation (SQLAlchemy + FastAPI)

## Base Classes

```python
# src/shared/domain/base.py
from __future__ import annotations
import uuid
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class DomainEvent:
    def __init__(self) -> None:
        self.event_id: str = str(uuid.uuid4())
        self.occurred_at: datetime = datetime.now(timezone.utc)


class Entity(ABC):
    id: Any

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass(frozen=True)
class ValueObject(ABC):
    """Frozen dataclass = immutable + structural equality."""
    pass
```

## Aggregate Root

```python
# src/ordering/domain/entities.py
from dataclasses import dataclass, field
from enum import Enum
from typing import List
from src.shared.domain.base import Entity, DomainEvent
from src.ordering.domain.value_objects import Money, Address, OrderLineItem
from src.ordering.domain.events import OrderPlaced, OrderCancelled
from src.ordering.domain.exceptions import EmptyOrderError, InvalidStateTransition


class OrderStatus(Enum):
    DRAFT = "DRAFT"
    PLACED = "PLACED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


@dataclass
class Order(Entity):
    id: str
    customer_id: str
    status: OrderStatus
    items: List[OrderLineItem] = field(default_factory=list)
    shipping_address: Address | None = None
    _events: List[DomainEvent] = field(default_factory=list, repr=False)

    @classmethod
    def create(cls, order_id: str, customer_id: str) -> Order:
        return cls(id=order_id, customer_id=customer_id, status=OrderStatus.DRAFT)

    def add_item(self, product_id: str, name: str, price: Money, quantity: int) -> None:
        self.items.append(OrderLineItem(product_id=product_id, name=name, unit_price=price, quantity=quantity))

    def place(self, shipping_address: Address) -> None:
        if not self.items:
            raise EmptyOrderError("Cannot place an order with no items")
        if self.status != OrderStatus.DRAFT:
            raise InvalidStateTransition(self.status, OrderStatus.PLACED)
        self.shipping_address = shipping_address
        self.status = OrderStatus.PLACED
        self._events.append(OrderPlaced(order_id=self.id, customer_id=self.customer_id, total=self.total))

    def cancel(self, reason: str) -> None:
        if self.status == OrderStatus.CANCELLED:
            raise InvalidStateTransition(self.status, OrderStatus.CANCELLED)
        self.status = OrderStatus.CANCELLED
        self._events.append(OrderCancelled(order_id=self.id, reason=reason))

    @property
    def total(self) -> Money:
        amount = sum(item.unit_price.amount * item.quantity for item in self.items)
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
class OrderCancelled(DomainEvent):
    order_id: str
    reason: str

    def __post_init__(self) -> None:
        super().__init__()
```

## Repository Port

```python
# src/ordering/domain/repositories.py
from abc import ABC, abstractmethod
from typing import Optional
from src.ordering.domain.entities import Order


class OrderRepository(ABC):
    @abstractmethod
    async def find_by_id(self, order_id: str) -> Optional[Order]: ...

    @abstractmethod
    async def save(self, order: Order) -> None: ...

    @abstractmethod
    async def find_by_customer(self, customer_id: str) -> list[Order]: ...
```

## CQRS Handlers

```python
# src/ordering/application/commands.py
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PlaceOrderCommand:
    customer_id: str
    items: list[dict]
    street: str
    city: str
    postal_code: str
    country: str


# src/ordering/application/command_handlers.py
import uuid
from src.ordering.domain.entities import Order
from src.ordering.domain.value_objects import Money, Address
from src.ordering.domain.repositories import OrderRepository
from src.ordering.application.commands import PlaceOrderCommand
from src.ordering.application.ports import EventPublisher, UnitOfWork


class PlaceOrderHandler:
    def __init__(self, order_repo: OrderRepository, event_publisher: EventPublisher, uow: UnitOfWork) -> None:
        self._order_repo = order_repo
        self._event_publisher = event_publisher
        self._uow = uow

    async def handle(self, command: PlaceOrderCommand) -> str:
        order = Order.create(order_id=str(uuid.uuid4()), customer_id=command.customer_id)
        for item in command.items:
            order.add_item(
                product_id=item["product_id"], name=item["name"],
                price=Money(amount=item["price"]), quantity=item["quantity"],
            )
        address = Address(street=command.street, city=command.city, postal_code=command.postal_code, country=command.country)
        order.place(address)

        async with self._uow:
            await self._order_repo.save(order)
            await self._uow.commit()

        for event in order.collect_events():
            await self._event_publisher.publish(event)
        return order.id
```

## Infrastructure Adapter

```python
# src/ordering/infrastructure/sqlalchemy_repositories.py
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.ordering.domain.entities import Order
from src.ordering.domain.repositories import OrderRepository
from src.ordering.infrastructure.orm_models import OrderModel
from src.ordering.infrastructure.mappers import OrderMapper


class SqlAlchemyOrderRepository(OrderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, order_id: str) -> Optional[Order]:
        stmt = select(OrderModel).where(OrderModel.id == order_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return OrderMapper.to_domain(row) if row else None

    async def save(self, order: Order) -> None:
        model = OrderMapper.to_model(order)
        await self._session.merge(model)
        await self._session.flush()
```

## Composition Root

```python
# src/ordering/composition_root.py
from sqlalchemy.ext.asyncio import AsyncSession
from src.ordering.infrastructure.sqlalchemy_repositories import SqlAlchemyOrderRepository
from src.ordering.infrastructure.event_publisher import RedisEventPublisher
from src.ordering.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from src.ordering.application.command_handlers import PlaceOrderHandler


def create_place_order_handler(session: AsyncSession) -> PlaceOrderHandler:
    return PlaceOrderHandler(
        order_repo=SqlAlchemyOrderRepository(session),
        event_publisher=RedisEventPublisher(),
        uow=SqlAlchemyUnitOfWork(session),
    )
```

## FastAPI Route

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
async def place_order(request: PlaceOrderRequest, session: AsyncSession = Depends(get_session)):
    handler = create_place_order_handler(session)
    order_id = await handler.handle(PlaceOrderCommand(
        customer_id=request.customer_id,
        items=[item.dict() for item in request.items],
        street=request.street, city=request.city,
        postal_code=request.postal_code, country=request.country,
    ))
    return OrderResponse(order_id=order_id, status="PLACED")
```

## Testing

```python
# tests/unit/domain/test_order.py
import pytest
from decimal import Decimal
from src.ordering.domain.entities import Order, OrderStatus
from src.ordering.domain.value_objects import Money, Address
from src.ordering.domain.exceptions import EmptyOrderError


class TestOrder:
    def test_place_order_emits_event(self):
        order = Order.create("order-1", "customer-1")
        order.add_item("prod-1", "Widget", Money(Decimal("9.99")), 2)
        order.place(Address("123 Main St", "Springfield", "62701", "US"))

        assert order.status == OrderStatus.PLACED
        events = order.collect_events()
        assert len(events) == 1
        assert events[0].order_id == "order-1"

    def test_cannot_place_empty_order(self):
        order = Order.create("order-1", "customer-1")
        with pytest.raises(EmptyOrderError):
            order.place(Address("st", "city", "zip", "US"))
```
