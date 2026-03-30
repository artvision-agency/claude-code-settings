---
name: solid-dry-kiss
description: >
  SOLID, DRY, KISS, YAGNI — принципы чистого кода с примерами на TypeScript и Python.
  Use when: code review, refactoring, architecture decisions, new feature design,
  or when code smells indicate principle violations.
---

# SOLID / DRY / KISS / YAGNI

Фундаментальные принципы проектирования. Не догма — инструмент принятия решений.

## Когда применять

| Применяй | Не перегибай |
|----------|-------------|
| Долгоживущий код (месяцы+) | Одноразовый скрипт, прототип |
| Команда > 1 человека | Личный хак на вечер |
| Код меняется часто | Стабильный legacy, не трогай |
| Сложная бизнес-логика | Простой CRUD |

## SOLID

### S — Single Responsibility Principle

Класс/модуль имеет одну причину для изменения.

**Нарушение:**
```typescript
class UserService {
  createUser(data: UserDto) { /* ... */ }
  sendWelcomeEmail(user: User) { /* ... */ }
  generateReport(users: User[]) { /* ... */ }
}
```

**Исправление:**
```typescript
class UserService {
  createUser(data: UserDto) { /* ... */ }
}
class EmailService {
  sendWelcomeEmail(user: User) { /* ... */ }
}
class ReportService {
  generateReport(users: User[]) { /* ... */ }
}
```

**Тест:** "Этот класс делает X **и** Y" → нарушение. Союз "и" = два ответственности.

### O — Open/Closed Principle

Открыт для расширения, закрыт для модификации.

**Нарушение:**
```typescript
function calculateDiscount(type: string, price: number) {
  if (type === 'vip') return price * 0.2
  if (type === 'student') return price * 0.1
  // каждый новый тип = правка этой функции
  return 0
}
```

**Исправление:**
```typescript
interface DiscountStrategy {
  calculate(price: number): number
}

class VipDiscount implements DiscountStrategy {
  calculate(price: number) { return price * 0.2 }
}

function calculateDiscount(strategy: DiscountStrategy, price: number) {
  return strategy.calculate(price)
}
```

**Тест:** "Чтобы добавить новое поведение, я правлю существующий код" → нарушение.

### L — Liskov Substitution Principle

Подтип можно использовать вместо базового типа без поломок.

**Нарушение:**
```python
class Rectangle:
    def set_width(self, w): self.width = w
    def set_height(self, h): self.height = h
    def area(self): return self.width * self.height

class Square(Rectangle):
    def set_width(self, w):
        self.width = w
        self.height = w  # неожиданный побочный эффект
```

**Исправление:** Не наследовать Square от Rectangle. Использовать общий интерфейс `Shape` с методом `area()`.

**Тест:** Подставь подтип в любой код, использующий базовый тип. Поведение не должно сломаться.

### I — Interface Segregation Principle

Много маленьких интерфейсов лучше одного большого.

**Нарушение:**
```typescript
interface Worker {
  work(): void
  eat(): void
  sleep(): void
}
// Робот не ест и не спит
class Robot implements Worker {
  work() { /* ok */ }
  eat() { throw new Error('robots dont eat') }  // ← проблема
  sleep() { throw new Error('robots dont sleep') }
}
```

**Исправление:**
```typescript
interface Workable { work(): void }
interface Feedable { eat(): void }
interface Sleepable { sleep(): void }

class Robot implements Workable {
  work() { /* ok */ }
}
```

**Тест:** Класс реализует интерфейс, но выбрасывает `NotImplemented` в каком-то методе → нарушение.

### D — Dependency Inversion Principle

Зависимости — на абстракции, не на конкретные реализации.

**Нарушение:**
```python
class OrderService:
    def __init__(self):
        self.db = PostgresDatabase()  # жёсткая привязка
```

**Исправление:**
```python
class OrderService:
    def __init__(self, db: DatabasePort):  # абстракция
        self.db = db
```

**Тест:** "Могу ли я протестировать этот класс без реальной БД/сети/файлов?" Нет → нарушение.

## DRY — Don't Repeat Yourself

Каждое знание имеет одно авторитетное представление в системе.

**Важно:** DRY — про знания, не про код. Два одинаковых куска кода, меняющихся по разным причинам — это НЕ дублирование.

**Реальное дублирование (исправлять):**
```typescript
// В 5 местах проекта:
const TAX_RATE = 0.13
const total = price * (1 + TAX_RATE)
```
→ Вынести в одно место: `calculateTotalWithTax(price)`.

**Ложное дублирование (НЕ трогать):**
```typescript
// UserValidator и OrderValidator похожи, но меняются по разным причинам
// Объединять их — ошибка, они разойдутся со временем
```

**Правило трёх:** Дублирование допустимо до 2 раз. На 3-й раз — выноси.

## KISS — Keep It Simple, Stupid

Простое решение > сложное, пока простое работает.

**Нарушение:**
```typescript
// "Элегантный" однострочник, который никто не поймёт через неделю
const result = data.reduce((acc, x) => ({...acc, [x.key]: [...(acc[x.key] || []), x]}), {})
```

**Исправление:**
```typescript
const result: Record<string, Item[]> = {}
for (const x of data) {
  if (!result[x.key]) result[x.key] = []
  result[x.key].push(x)
}
```

**Тест:** "Новый разработчик поймёт это за 30 секунд?" Нет → упрости.

## YAGNI — You Aren't Gonna Need It

Не пиши код для будущих требований. Пиши для текущих.

**Нарушение:**
```typescript
// "А вдруг понадобится поддержка MongoDB"
interface DatabaseAdapter { /* 20 методов */ }
class PostgresAdapter implements DatabaseAdapter { /* ... */ }
// MongoDB никто никогда не попросит
```

**Исправление:** Просто используй Postgres напрямую. Абстракция — когда реально нужен второй адаптер.

**Тест:** "Есть ли конкретное требование для этого?" Нет → не делай.

## Чеклист при code review

| Проверка | Принцип |
|----------|---------|
| Класс делает слишком много? | SRP |
| Для нового поведения правим старый код? | OCP |
| Подтип ломает контракт родителя? | LSP |
| Класс реализует ненужные методы? | ISP |
| Жёсткая зависимость на конкретику? | DIP |
| Одна и та же логика в 3+ местах? | DRY |
| Код сложнее чем нужно? | KISS |
| Код для несуществующих требований? | YAGNI |

## Баланс принципов

Принципы конфликтуют. Приоритет:

1. **KISS** — простота важнее всего
2. **YAGNI** — не делай лишнего
3. **DRY** — но только для реального дублирования знаний
4. **SOLID** — когда сложность оправдана

> Три строки копипасты лучше преждевременной абстракции.
