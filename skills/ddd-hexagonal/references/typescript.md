# TypeScript Implementation (Prisma/Drizzle + Express/Fastify)

## Base Classes

```typescript
// src/shared/domain/base.ts
import { randomUUID } from "crypto";

export abstract class Entity<T = string> {
  constructor(public readonly id: T) {}

  equals(other: Entity<T>): boolean {
    return this.constructor === other.constructor && this.id === other.id;
  }
}

export abstract class ValueObject {
  abstract equals(other: ValueObject): boolean;
}

export abstract class DomainEvent {
  public readonly eventId: string = randomUUID();
  public readonly occurredAt: Date = new Date();
}
```

## Aggregate Root

```typescript
// src/ordering/domain/entities/order.ts
import { Entity, DomainEvent } from "@/shared/domain/base";
import { Money, Address, OrderLineItem } from "../value-objects";
import { OrderPlaced, OrderCancelled } from "../events";
import { EmptyOrderError, InvalidStateTransition } from "../exceptions";

export enum OrderStatus {
  DRAFT = "DRAFT",
  PLACED = "PLACED",
  CONFIRMED = "CONFIRMED",
  CANCELLED = "CANCELLED",
}

export class Order extends Entity {
  private _events: DomainEvent[] = [];

  private constructor(
    id: string,
    public readonly customerId: string,
    private _status: OrderStatus,
    private _items: OrderLineItem[] = [],
    private _shippingAddress: Address | null = null,
  ) {
    super(id);
  }

  static create(id: string, customerId: string): Order {
    return new Order(id, customerId, OrderStatus.DRAFT);
  }

  get status(): OrderStatus { return this._status; }
  get items(): readonly OrderLineItem[] { return this._items; }

  addItem(productId: string, name: string, price: Money, quantity: number): void {
    this._items.push(new OrderLineItem(productId, name, price, quantity));
  }

  place(shippingAddress: Address): void {
    if (this._items.length === 0) throw new EmptyOrderError();
    if (this._status !== OrderStatus.DRAFT) {
      throw new InvalidStateTransition(this._status, OrderStatus.PLACED);
    }
    this._shippingAddress = shippingAddress;
    this._status = OrderStatus.PLACED;
    this._events.push(new OrderPlaced(this.id, this.customerId, this.total));
  }

  cancel(reason: string): void {
    if (this._status === OrderStatus.CANCELLED) {
      throw new InvalidStateTransition(this._status, OrderStatus.CANCELLED);
    }
    this._status = OrderStatus.CANCELLED;
    this._events.push(new OrderCancelled(this.id, reason));
  }

  get total(): Money {
    const amount = this._items.reduce(
      (sum, item) => sum + item.unitPrice.amount * item.quantity, 0
    );
    const currency = this._items[0]?.unitPrice.currency ?? "USD";
    return new Money(amount, currency);
  }

  collectEvents(): DomainEvent[] {
    const events = [...this._events];
    this._events = [];
    return events;
  }
}
```

## Value Objects

```typescript
// src/ordering/domain/value-objects.ts
import { ValueObject } from "@/shared/domain/base";

export class Money extends ValueObject {
  constructor(
    public readonly amount: number,
    public readonly currency: string = "USD",
  ) {
    super();
    if (amount < 0) throw new Error("Money amount cannot be negative");
  }

  add(other: Money): Money {
    if (this.currency !== other.currency) throw new Error("Currency mismatch");
    return new Money(this.amount + other.amount, this.currency);
  }

  equals(other: ValueObject): boolean {
    return other instanceof Money
      && this.amount === other.amount
      && this.currency === other.currency;
  }
}

export class Address extends ValueObject {
  constructor(
    public readonly street: string,
    public readonly city: string,
    public readonly postalCode: string,
    public readonly country: string,
  ) { super(); }

  equals(other: ValueObject): boolean {
    return other instanceof Address
      && this.street === other.street
      && this.city === other.city
      && this.postalCode === other.postalCode
      && this.country === other.country;
  }
}

export class OrderLineItem extends ValueObject {
  constructor(
    public readonly productId: string,
    public readonly name: string,
    public readonly unitPrice: Money,
    public readonly quantity: number,
  ) {
    super();
    if (quantity <= 0) throw new Error("Quantity must be positive");
  }

  equals(other: ValueObject): boolean {
    return other instanceof OrderLineItem
      && this.productId === other.productId
      && this.unitPrice.equals(other.unitPrice)
      && this.quantity === other.quantity;
  }
}
```

## Domain Events

```typescript
// src/ordering/domain/events.ts
import { DomainEvent } from "@/shared/domain/base";
import { Money } from "./value-objects";

export class OrderPlaced extends DomainEvent {
  constructor(
    public readonly orderId: string,
    public readonly customerId: string,
    public readonly total: Money,
  ) { super(); }
}

export class OrderCancelled extends DomainEvent {
  constructor(
    public readonly orderId: string,
    public readonly reason: string,
  ) { super(); }
}
```

## Repository Port

```typescript
// src/ordering/domain/repositories.ts
import { Order } from "./entities/order";

export interface OrderRepository {
  findById(orderId: string): Promise<Order | null>;
  save(order: Order): Promise<void>;
  findByCustomer(customerId: string): Promise<Order[]>;
}
```

## CQRS Handlers

```typescript
// src/ordering/application/commands.ts
export interface PlaceOrderCommand {
  readonly customerId: string;
  readonly items: ReadonlyArray<{ productId: string; name: string; price: number; quantity: number }>;
  readonly street: string;
  readonly city: string;
  readonly postalCode: string;
  readonly country: string;
}

// src/ordering/application/ports.ts
import { DomainEvent } from "@/shared/domain/base";

export interface EventPublisher {
  publish(event: DomainEvent): Promise<void>;
}

export interface UnitOfWork {
  commit(): Promise<void>;
  rollback(): Promise<void>;
  execute<T>(fn: () => Promise<T>): Promise<T>;
}

// src/ordering/application/handlers/place-order.handler.ts
import { randomUUID } from "crypto";
import { Order } from "../../domain/entities/order";
import { Money, Address } from "../../domain/value-objects";
import { OrderRepository } from "../../domain/repositories";
import { PlaceOrderCommand } from "../commands";
import { EventPublisher, UnitOfWork } from "../ports";

export class PlaceOrderHandler {
  constructor(
    private readonly orderRepo: OrderRepository,
    private readonly eventPublisher: EventPublisher,
    private readonly uow: UnitOfWork,
  ) {}

  async handle(command: PlaceOrderCommand): Promise<string> {
    const order = Order.create(randomUUID(), command.customerId);
    for (const item of command.items) {
      order.addItem(item.productId, item.name, new Money(item.price), item.quantity);
    }
    const address = new Address(command.street, command.city, command.postalCode, command.country);
    order.place(address);

    await this.uow.execute(async () => {
      await this.orderRepo.save(order);
    });

    for (const event of order.collectEvents()) {
      await this.eventPublisher.publish(event);
    }
    return order.id;
  }
}
```

## Prisma Adapter

```typescript
// src/ordering/infrastructure/prisma-order.repository.ts
import { PrismaClient } from "@prisma/client";
import { Order } from "../domain/entities/order";
import { OrderRepository } from "../domain/repositories";
import { OrderMapper } from "./mappers";

export class PrismaOrderRepository implements OrderRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async findById(orderId: string): Promise<Order | null> {
    const row = await this.prisma.order.findUnique({
      where: { id: orderId },
      include: { items: true },
    });
    return row ? OrderMapper.toDomain(row) : null;
  }

  async save(order: Order): Promise<void> {
    const data = OrderMapper.toPrisma(order);
    await this.prisma.order.upsert({
      where: { id: order.id },
      create: data,
      update: data,
    });
  }

  async findByCustomer(customerId: string): Promise<Order[]> {
    const rows = await this.prisma.order.findMany({
      where: { customerId },
      include: { items: true },
    });
    return rows.map(OrderMapper.toDomain);
  }
}
```

## Composition Root

```typescript
// src/ordering/composition-root.ts
import { PrismaClient } from "@prisma/client";
import { PrismaOrderRepository } from "./infrastructure/prisma-order.repository";
import { RedisEventPublisher } from "./infrastructure/redis-event.publisher";
import { PrismaUnitOfWork } from "./infrastructure/prisma-unit-of-work";
import { PlaceOrderHandler } from "./application/handlers/place-order.handler";

export function createPlaceOrderHandler(prisma: PrismaClient): PlaceOrderHandler {
  return new PlaceOrderHandler(
    new PrismaOrderRepository(prisma),
    new RedisEventPublisher(),
    new PrismaUnitOfWork(prisma),
  );
}
```

## Testing

```typescript
// tests/unit/domain/order.test.ts
import { describe, it, expect } from "vitest";
import { Order, OrderStatus } from "@/ordering/domain/entities/order";
import { Money, Address } from "@/ordering/domain/value-objects";
import { EmptyOrderError } from "@/ordering/domain/exceptions";

describe("Order", () => {
  const address = new Address("123 Main", "Springfield", "62701", "US");

  it("emits OrderPlaced event when placed", () => {
    const order = Order.create("order-1", "customer-1");
    order.addItem("p1", "Widget", new Money(9.99), 2);

    order.place(address);

    expect(order.status).toBe(OrderStatus.PLACED);
    const events = order.collectEvents();
    expect(events).toHaveLength(1);
    expect(events[0]).toHaveProperty("orderId", "order-1");
  });

  it("throws on placing empty order", () => {
    const order = Order.create("order-1", "customer-1");
    expect(() => order.place(address)).toThrow(EmptyOrderError);
  });
});
```
