---
name: aiogram-patterns
description: Build Telegram bots with Python aiogram 3.x framework. Use when developing Telegram bots with handlers, routers, FSM, middleware, inline keyboards, callback queries, i18n, error handling, and dependency injection.
---

# Aiogram 3.x Patterns

Comprehensive guide for building Telegram bots using the aiogram 3.x framework in Python, covering routers, handlers, FSM, middleware, filters, inline keyboards, callback queries, i18n, error handling, dependency injection, and testing.

## When to Use This Skill

- Creating new Telegram bots with Python
- Adding commands, handlers, or features to existing aiogram bots
- Implementing conversation flows with FSM (Finite State Machine)
- Building inline keyboards and handling callback queries
- Adding middleware for logging, throttling, or authentication
- Implementing i18n (internationalization) for multi-language bots
- Writing tests for aiogram handlers and middleware
- Structuring large bot projects with routers

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | [aiogram 3.x](https://docs.aiogram.dev/) |
| Language | Python 3.10+ |
| Async | asyncio |
| State Management | FSM (MemoryStorage / RedisStorage) |
| i18n | aiogram_i18n or fluent-compiler |
| Testing | pytest + pytest-asyncio |

## Project Structure

```
my_bot/
    __init__.py
    __main__.py
    config.py
    bot.py
    handlers/
        __init__.py
        start.py
        admin.py
        user.py
    keyboards/
        __init__.py
        inline.py
        reply.py
    middlewares/
        __init__.py
        throttling.py
        auth.py
        i18n.py
    states/
        __init__.py
        registration.py
    filters/
        __init__.py
        admin.py
    services/
        __init__.py
        user_service.py
    locales/
        en/
        ru/
    tests/
        __init__.py
        test_handlers.py
        test_middlewares.py
        conftest.py
```

## Quick Start

```python
# bot.py
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

async def main():
    bot = Bot(
        token="YOUR_BOT_TOKEN",
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Include routers
    dp.include_router(router)

    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

## Router Setup and Handler Registration

### Basic Router

```python
# handlers/start.py
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router(name="start")

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        f"Hello, <b>{message.from_user.full_name}</b>! Welcome to the bot."
    )

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/settings - Bot settings"
    )
```

### Nested Routers

```python
# handlers/__init__.py
from aiogram import Router

from .start import router as start_router
from .admin import router as admin_router
from .user import router as user_router

def setup_routers() -> Router:
    """Create and configure the root router with sub-routers."""
    root_router = Router(name="root")

    # Order matters: first registered router gets priority
    root_router.include_router(admin_router)
    root_router.include_router(start_router)
    root_router.include_router(user_router)

    return root_router
```

### Registering Routers in Dispatcher

```python
# bot.py
from aiogram import Bot, Dispatcher
from handlers import setup_routers
from middlewares.throttling import ThrottlingMiddleware

async def main():
    bot = Bot(token="YOUR_BOT_TOKEN")
    dp = Dispatcher()

    # Setup routers
    main_router = setup_routers()
    dp.include_router(main_router)

    # Register middleware on dispatcher level
    dp.message.middleware(ThrottlingMiddleware())

    await dp.start_polling(bot)
```

## FSM (Finite State Machine)

### Defining States

```python
# states/registration.py
from aiogram.fsm.state import State, StatesGroup

class RegistrationForm(StatesGroup):
    name = State()
    age = State()
    email = State()
    confirm = State()
```

### FSM Handlers

```python
# handlers/registration.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from states.registration import RegistrationForm
from keyboards.inline import get_confirm_keyboard

router = Router(name="registration")

@router.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext) -> None:
    """Start registration flow."""
    await state.set_state(RegistrationForm.name)
    await message.answer("Let's start registration. What is your name?")

@router.message(RegistrationForm.name)
async def process_name(message: Message, state: FSMContext) -> None:
    """Process name input."""
    if len(message.text) < 2:
        await message.answer("Name must be at least 2 characters. Try again:")
        return

    await state.update_data(name=message.text)
    await state.set_state(RegistrationForm.age)
    await message.answer("Great! Now enter your age:")

@router.message(RegistrationForm.age)
async def process_age(message: Message, state: FSMContext) -> None:
    """Process age input."""
    if not message.text.isdigit() or not (13 <= int(message.text) <= 120):
        await message.answer("Please enter a valid age (13-120):")
        return

    await state.update_data(age=int(message.text))
    await state.set_state(RegistrationForm.email)
    await message.answer("Enter your email address:")

@router.message(RegistrationForm.email)
async def process_email(message: Message, state: FSMContext) -> None:
    """Process email input."""
    if "@" not in message.text or "." not in message.text:
        await message.answer("Please enter a valid email address:")
        return

    await state.update_data(email=message.text)
    data = await state.get_data()

    await state.set_state(RegistrationForm.confirm)
    await message.answer(
        f"Please confirm your data:\n\n"
        f"Name: {data['name']}\n"
        f"Age: {data['age']}\n"
        f"Email: {data['email']}",
        reply_markup=get_confirm_keyboard(),
    )

@router.callback_query(RegistrationForm.confirm, F.data == "confirm_yes")
async def process_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Confirm registration."""
    data = await state.get_data()
    # Save user data to database here
    await state.clear()
    await callback.message.edit_text(
        f"Registration complete! Welcome, {data['name']}!"
    )
    await callback.answer()

@router.callback_query(RegistrationForm.confirm, F.data == "confirm_no")
async def process_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel registration."""
    await state.clear()
    await callback.message.edit_text("Registration cancelled.")
    await callback.answer()
```

### FSM Storage Configuration

```python
# For development (in-memory, data lost on restart)
from aiogram.fsm.storage.memory import MemoryStorage
dp = Dispatcher(storage=MemoryStorage())

# For production (Redis-backed, persistent)
from aiogram.fsm.storage.redis import RedisStorage
storage = RedisStorage.from_url("redis://localhost:6379/0")
dp = Dispatcher(storage=storage)
```

## Middleware

### Outer Middleware (runs for every update, even if no handler matches)

```python
# middlewares/logging.py
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        logger.info("Update received: %s", event.__class__.__name__)
        try:
            result = await handler(event, data)
            logger.info("Update handled successfully")
            return result
        except Exception as e:
            logger.exception("Error handling update: %s", e)
            raise
```

### Inner Middleware (runs only when a handler matches)

```python
# middlewares/throttling.py
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
import time

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self.user_last_message: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id
        current_time = time.monotonic()

        last_time = self.user_last_message.get(user_id, 0)
        if current_time - last_time < self.rate_limit:
            # Throttled: silently ignore or send a warning
            return None

        self.user_last_message[user_id] = current_time
        return await handler(event, data)
```

### Auth Middleware

```python
# middlewares/auth.py
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message

class AuthMiddleware(BaseMiddleware):
    def __init__(self, admin_ids: list[int]):
        self.admin_ids = admin_ids

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        # Inject is_admin flag into handler data
        data["is_admin"] = event.from_user.id in self.admin_ids
        return await handler(event, data)
```

### Registering Middleware

```python
# Outer middleware (on dispatcher or router)
dp.message.outer_middleware(LoggingMiddleware())

# Inner middleware (on router)
router.message.middleware(ThrottlingMiddleware(rate_limit=1.0))

# Middleware on specific router only
admin_router.message.middleware(AuthMiddleware(admin_ids=[123456789]))
```

## Callback Queries and Inline Keyboards

### Building Inline Keyboards

```python
# keyboards/inline.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Simple confirm/cancel keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Confirm", callback_data="confirm_yes"),
        InlineKeyboardButton(text="Cancel", callback_data="confirm_no"),
    )
    return builder.as_markup()

def get_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard with multiple rows."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Profile", callback_data="menu:profile"),
        InlineKeyboardButton(text="Settings", callback_data="menu:settings"),
    )
    builder.row(
        InlineKeyboardButton(text="Help", callback_data="menu:help"),
    )
    builder.row(
        InlineKeyboardButton(
            text="Visit Website",
            url="https://example.com",
        ),
    )
    return builder.as_markup()

def get_pagination_keyboard(
    page: int, total_pages: int, prefix: str = "page"
) -> InlineKeyboardMarkup:
    """Pagination keyboard."""
    builder = InlineKeyboardBuilder()
    buttons = []

    if page > 1:
        buttons.append(
            InlineKeyboardButton(text="<< Prev", callback_data=f"{prefix}:{page - 1}")
        )

    buttons.append(
        InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
    )

    if page < total_pages:
        buttons.append(
            InlineKeyboardButton(text="Next >>", callback_data=f"{prefix}:{page + 1}")
        )

    builder.row(*buttons)
    return builder.as_markup()
```

### Handling Callback Queries

```python
# handlers/menu.py
from aiogram import Router, F
from aiogram.types import CallbackQuery

router = Router(name="menu")

@router.callback_query(F.data == "menu:profile")
async def show_profile(callback: CallbackQuery) -> None:
    """Handle profile button press."""
    user = callback.from_user
    await callback.message.edit_text(
        f"Your profile:\n\n"
        f"ID: {user.id}\n"
        f"Name: {user.full_name}\n"
        f"Username: @{user.username or 'not set'}"
    )
    await callback.answer()

@router.callback_query(F.data == "menu:settings")
async def show_settings(callback: CallbackQuery) -> None:
    """Handle settings button press."""
    await callback.message.edit_text("Settings menu (coming soon)")
    await callback.answer()

@router.callback_query(F.data.startswith("page:"))
async def handle_pagination(callback: CallbackQuery) -> None:
    """Handle pagination buttons."""
    page = int(callback.data.split(":")[1])
    # Fetch data for the requested page
    await callback.message.edit_text(
        f"Showing page {page}",
        reply_markup=get_pagination_keyboard(page, total_pages=10),
    )
    await callback.answer()

# Always answer callback queries to remove the loading indicator
@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    """Handle no-op callbacks (e.g., page indicator)."""
    await callback.answer()
```

### Callback Data Factory (Typed Callbacks)

```python
from aiogram.filters.callback_data import CallbackData

class ItemCallback(CallbackData, prefix="item"):
    action: str
    item_id: int

class CategoryCallback(CallbackData, prefix="cat"):
    category_id: int
    page: int = 1

# Building keyboard with factory
def get_items_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.row(
            InlineKeyboardButton(
                text=item["name"],
                callback_data=ItemCallback(
                    action="view", item_id=item["id"]
                ).pack(),
            ),
            InlineKeyboardButton(
                text="Delete",
                callback_data=ItemCallback(
                    action="delete", item_id=item["id"]
                ).pack(),
            ),
        )
    return builder.as_markup()

# Handling typed callbacks
@router.callback_query(ItemCallback.filter(F.action == "view"))
async def view_item(
    callback: CallbackQuery, callback_data: ItemCallback
) -> None:
    item_id = callback_data.item_id
    await callback.message.edit_text(f"Viewing item #{item_id}")
    await callback.answer()

@router.callback_query(ItemCallback.filter(F.action == "delete"))
async def delete_item(
    callback: CallbackQuery, callback_data: ItemCallback
) -> None:
    item_id = callback_data.item_id
    # Delete item from database
    await callback.message.edit_text(f"Item #{item_id} deleted.")
    await callback.answer("Deleted!")
```

## Message Filters

### Built-in Filters

```python
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ContentType

router = Router()

# Command filters
@router.message(CommandStart())
async def start(message: Message): ...

@router.message(Command("help", "info"))  # Multiple commands
async def help_cmd(message: Message): ...

# Content type filters
@router.message(F.photo)
async def handle_photo(message: Message): ...

@router.message(F.document)
async def handle_document(message: Message): ...

@router.message(F.sticker)
async def handle_sticker(message: Message): ...

@router.message(F.location)
async def handle_location(message: Message): ...

# Text filters
@router.message(F.text == "Hello")
async def exact_match(message: Message): ...

@router.message(F.text.startswith("!"))
async def starts_with_bang(message: Message): ...

@router.message(F.text.lower().contains("help"))
async def contains_help(message: Message): ...

@router.message(F.text.regexp(r"^\d{4}-\d{2}-\d{2}$"))
async def date_pattern(message: Message): ...

# Chat type filters
@router.message(F.chat.type == "private")
async def private_only(message: Message): ...

@router.message(F.chat.type.in_({"group", "supergroup"}))
async def groups_only(message: Message): ...
```

### Custom Filters

```python
# filters/admin.py
from aiogram.filters import BaseFilter
from aiogram.types import Message

class IsAdminFilter(BaseFilter):
    def __init__(self, admin_ids: list[int]):
        self.admin_ids = admin_ids

    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in self.admin_ids

# Usage
admin_filter = IsAdminFilter(admin_ids=[123456789, 987654321])

@router.message(Command("ban"), admin_filter)
async def ban_user(message: Message): ...
```

### Combining Filters

```python
from aiogram import F

# AND: multiple arguments (all must match)
@router.message(Command("secret"), F.chat.type == "private")
async def secret_command(message: Message): ...

# OR: use the | operator
@router.message(F.text == "yes" | F.text == "da")
async def affirmative(message: Message): ...

# NOT: use the ~ operator
@router.message(~F.from_user.is_bot)
async def not_from_bot(message: Message): ...
```

## Error Handling

### Global Error Handler

```python
from aiogram import Router
from aiogram.types import ErrorEvent
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.error()
async def global_error_handler(event: ErrorEvent) -> None:
    """Handle all unhandled exceptions."""
    logger.error(
        "Unhandled exception: %s\nUpdate: %s",
        event.exception,
        event.update,
        exc_info=event.exception,
    )

    # Try to notify the user
    update = event.update
    if update.message:
        await update.message.answer(
            "An error occurred. Please try again later."
        )
    elif update.callback_query:
        await update.callback_query.answer(
            "An error occurred. Please try again.", show_alert=True
        )
```

### Specific Error Handlers

```python
from aiogram.types import ErrorEvent
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

@router.error(exception=TelegramBadRequest)
async def handle_bad_request(event: ErrorEvent) -> None:
    """Handle Telegram API bad request errors."""
    logger.warning("Bad request: %s", event.exception)

@router.error(exception=TelegramForbiddenError)
async def handle_forbidden(event: ErrorEvent) -> None:
    """Handle cases where bot is blocked by user."""
    logger.info("Bot blocked by user: %s", event.exception)
```

### Error Handling in Handlers

```python
from aiogram.exceptions import TelegramBadRequest

@router.message(Command("delete"))
async def delete_message(message: Message) -> None:
    try:
        await message.delete()
        await message.answer("Message deleted.")
    except TelegramBadRequest as e:
        if "message can't be deleted" in str(e):
            await message.answer("Cannot delete that message.")
        else:
            raise
```

## Bot Commands with BotCommand

```python
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

async def set_bot_commands(bot: Bot) -> None:
    """Register bot commands visible in Telegram UI."""
    # Default commands for all users
    default_commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show help"),
        BotCommand(command="settings", description="Bot settings"),
    ]
    await bot.set_my_commands(
        default_commands, scope=BotCommandScopeDefault()
    )

    # Admin-only commands (visible only to specific user)
    admin_commands = default_commands + [
        BotCommand(command="stats", description="Show statistics"),
        BotCommand(command="broadcast", description="Send broadcast"),
        BotCommand(command="ban", description="Ban a user"),
    ]
    for admin_id in ADMIN_IDS:
        await bot.set_my_commands(
            admin_commands,
            scope=BotCommandScopeChat(chat_id=admin_id),
        )

# Call during startup
async def on_startup(bot: Bot) -> None:
    await set_bot_commands(bot)

dp.startup.register(on_startup)
```

## Dependency Injection

Aiogram 3 supports passing extra data through the dispatcher/router to handlers.

### Injecting Services

```python
# bot.py
from services.user_service import UserService
from services.db import Database

async def main():
    bot = Bot(token="YOUR_TOKEN")
    dp = Dispatcher()

    # Create shared resources
    db = Database(dsn="postgresql://localhost/mybot")
    await db.connect()

    user_service = UserService(db)

    # Pass dependencies via dispatcher workflow_data
    dp["user_service"] = user_service
    dp["db"] = db

    dp.include_router(main_router)

    try:
        await dp.start_polling(bot)
    finally:
        await db.disconnect()
```

### Using Injected Dependencies in Handlers

```python
# handlers/user.py
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from services.user_service import UserService

router = Router()

@router.message(Command("profile"))
async def show_profile(
    message: Message,
    user_service: UserService,  # Automatically injected by name
) -> None:
    user = await user_service.get_user(message.from_user.id)
    if user:
        await message.answer(
            f"Name: {user.name}\nEmail: {user.email}"
        )
    else:
        await message.answer("Profile not found. Use /register first.")
```

### Middleware-Based Injection

```python
# middlewares/db_session.py
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_factory() as session:
            data["session"] = session
            return await handler(event, data)

# Usage in handler
@router.message(Command("users"))
async def list_users(message: Message, session: AsyncSession) -> None:
    users = await session.execute(select(User))
    # ...
```

## i18n Patterns

### Using aiogram's built-in i18n with gettext

```python
# middlewares/i18n.py
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
import gettext
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "locales"

def get_translator(locale: str) -> gettext.GNUTranslations:
    """Load translations for the given locale."""
    try:
        return gettext.translation(
            "messages",
            localedir=str(LOCALES_DIR),
            languages=[locale],
        )
    except FileNotFoundError:
        return gettext.translation(
            "messages",
            localedir=str(LOCALES_DIR),
            languages=["en"],
        )

class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user: User = data.get("event_from_user")
        locale = user.language_code if user else "en"
        translator = get_translator(locale or "en")
        data["_"] = translator.gettext
        return await handler(event, data)

# Register middleware
dp.message.outer_middleware(I18nMiddleware())
dp.callback_query.outer_middleware(I18nMiddleware())
```

### Using i18n in Handlers

```python
from typing import Callable

@router.message(CommandStart())
async def cmd_start(message: Message, _: Callable[[str], str]) -> None:
    await message.answer(_("Welcome to the bot!"))

@router.message(Command("help"))
async def cmd_help(message: Message, _: Callable[[str], str]) -> None:
    await message.answer(
        _("Available commands:\n"
          "/start - Start the bot\n"
          "/help - Show help\n"
          "/lang - Change language")
    )
```

### Language Selection with Inline Keyboard

```python
@router.message(Command("lang"))
async def cmd_language(message: Message, _: Callable[[str], str]) -> None:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="English", callback_data="lang:en"),
        InlineKeyboardButton(text="Russian", callback_data="lang:ru"),
    )
    await message.answer(
        _("Choose your language:"),
        reply_markup=builder.as_markup(),
    )

@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery) -> None:
    lang = callback.data.split(":")[1]
    # Save language preference to database
    await callback.message.edit_text(f"Language set to: {lang}")
    await callback.answer()
```

## Testing Aiogram Handlers

### Test Setup with pytest

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram import Bot
from aiogram.types import (
    Chat,
    Message,
    Update,
    User,
    CallbackQuery,
)

@pytest.fixture
def bot():
    """Create a mock bot."""
    mock_bot = AsyncMock(spec=Bot)
    mock_bot.id = 123456789
    return mock_bot

@pytest.fixture
def user():
    """Create a test user."""
    return User(
        id=12345,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser",
        language_code="en",
    )

@pytest.fixture
def chat():
    """Create a test chat."""
    return Chat(
        id=12345,
        type="private",
    )

@pytest.fixture
def message(user, chat, bot):
    """Create a test message."""
    msg = MagicMock(spec=Message)
    msg.from_user = user
    msg.chat = chat
    msg.text = "/start"
    msg.answer = AsyncMock()
    msg.reply = AsyncMock()
    msg.delete = AsyncMock()
    msg.edit_text = AsyncMock()
    msg.bot = bot
    return msg

@pytest.fixture
def callback_query(user, message):
    """Create a test callback query."""
    cb = MagicMock(spec=CallbackQuery)
    cb.from_user = user
    cb.message = message
    cb.data = ""
    cb.answer = AsyncMock()
    return cb
```

### Testing Handlers

```python
# tests/test_handlers.py
import pytest
from unittest.mock import AsyncMock
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from handlers.start import cmd_start, cmd_help
from handlers.registration import (
    cmd_register,
    process_name,
    process_age,
)
from states.registration import RegistrationForm

@pytest.mark.asyncio
async def test_cmd_start(message):
    """Test /start command handler."""
    await cmd_start(message)
    message.answer.assert_called_once()
    call_text = message.answer.call_args[0][0]
    assert "Welcome" in call_text

@pytest.mark.asyncio
async def test_cmd_help(message):
    """Test /help command handler."""
    await cmd_help(message)
    message.answer.assert_called_once()
    call_text = message.answer.call_args[0][0]
    assert "/start" in call_text
    assert "/help" in call_text

@pytest.fixture
async def fsm_context():
    """Create FSM context for testing."""
    storage = MemoryStorage()
    state = FSMContext(
        storage=storage,
        key=StorageKey(
            bot_id=123,
            chat_id=456,
            user_id=789,
        ),
    )
    return state

@pytest.mark.asyncio
async def test_registration_flow(message, fsm_context):
    """Test the registration FSM flow."""
    # Start registration
    await cmd_register(message, state=fsm_context)
    message.answer.assert_called_once()
    current_state = await fsm_context.get_state()
    assert current_state == RegistrationForm.name

    # Enter name
    message.text = "John"
    message.answer.reset_mock()
    await process_name(message, state=fsm_context)
    current_state = await fsm_context.get_state()
    assert current_state == RegistrationForm.age

    # Enter age
    message.text = "25"
    message.answer.reset_mock()
    await process_age(message, state=fsm_context)
    current_state = await fsm_context.get_state()
    assert current_state == RegistrationForm.email

    # Verify stored data
    data = await fsm_context.get_data()
    assert data["name"] == "John"
    assert data["age"] == 25

@pytest.mark.asyncio
async def test_invalid_age_stays_in_state(message, fsm_context):
    """Test that invalid age input keeps the user in the age state."""
    await fsm_context.set_state(RegistrationForm.age)
    message.text = "abc"
    await process_age(message, state=fsm_context)

    current_state = await fsm_context.get_state()
    assert current_state == RegistrationForm.age
    message.answer.assert_called_once()
    assert "valid age" in message.answer.call_args[0][0]
```

### Testing Callback Queries

```python
# tests/test_callbacks.py
import pytest
from handlers.menu import show_profile

@pytest.mark.asyncio
async def test_show_profile(callback_query):
    """Test profile callback handler."""
    callback_query.data = "menu:profile"
    await show_profile(callback_query)
    callback_query.message.edit_text.assert_called_once()
    callback_query.answer.assert_called_once()
    text = callback_query.message.edit_text.call_args[0][0]
    assert "profile" in text.lower()
```

### Testing Middleware

```python
# tests/test_middlewares.py
import pytest
import time
from unittest.mock import AsyncMock, MagicMock
from middlewares.throttling import ThrottlingMiddleware

@pytest.mark.asyncio
async def test_throttling_allows_first_message():
    """Test that the first message passes through."""
    middleware = ThrottlingMiddleware(rate_limit=1.0)
    handler = AsyncMock()
    event = MagicMock()
    event.from_user.id = 123
    data = {}

    await middleware(handler, event, data)
    handler.assert_called_once()

@pytest.mark.asyncio
async def test_throttling_blocks_rapid_messages():
    """Test that rapid messages are blocked."""
    middleware = ThrottlingMiddleware(rate_limit=1.0)
    handler = AsyncMock()
    event = MagicMock()
    event.from_user.id = 123
    data = {}

    # First message passes
    await middleware(handler, event, data)
    assert handler.call_count == 1

    # Second rapid message is blocked
    await middleware(handler, event, data)
    assert handler.call_count == 1  # Still 1, second call was blocked
```

## Common Patterns

### Sending Messages with Media

```python
from aiogram.types import FSInputFile, URLInputFile, BufferedInputFile

# Send local file
@router.message(Command("photo"))
async def send_photo(message: Message) -> None:
    photo = FSInputFile("images/welcome.png")
    await message.answer_photo(photo, caption="Welcome!")

# Send from URL
@router.message(Command("url_photo"))
async def send_url_photo(message: Message) -> None:
    photo = URLInputFile("https://example.com/image.png")
    await message.answer_photo(photo)

# Send from bytes
@router.message(Command("generated"))
async def send_generated(message: Message) -> None:
    content = generate_image_bytes()
    photo = BufferedInputFile(content, filename="generated.png")
    await message.answer_photo(photo)
```

### Webhook Mode

```python
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

WEBHOOK_URL = "https://your-domain.com/webhook"
WEBHOOK_PATH = "/webhook"

async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH)

async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook()

def main():
    bot = Bot(token="YOUR_TOKEN")
    dp = Dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    web.run_app(app, host="0.0.0.0", port=8080)
```

### Graceful Shutdown

```python
async def on_shutdown(bot: Bot, db: Database) -> None:
    """Cleanup on shutdown."""
    await bot.delete_webhook()
    await db.disconnect()

dp.shutdown.register(on_shutdown)
```

## Best Practices Summary

1. **Use Routers** to organize handlers by feature or domain
2. **Use FSM** for multi-step conversations; always validate input at each state
3. **Use typed CallbackData** factories instead of raw string parsing
4. **Register middleware** at the appropriate level (dispatcher vs. router)
5. **Handle errors globally** with an error handler on the router
6. **Set bot commands** on startup for better UX in the Telegram menu
7. **Inject dependencies** through dispatcher workflow_data or middleware
8. **Always answer callback queries** to remove the loading spinner
9. **Use InlineKeyboardBuilder** for dynamic keyboards
10. **Test handlers** with mocked Message/CallbackQuery objects and FSMContext
11. **Use RedisStorage** in production for FSM state persistence
12. **Use i18n middleware** for multi-language support from the start

## Resources

- **aiogram 3.x docs**: https://docs.aiogram.dev/en/latest/
- **aiogram GitHub**: https://github.com/aiogram/aiogram
- **Telegram Bot API**: https://core.telegram.org/bots/api
- **pytest-asyncio**: https://github.com/pytest-dev/pytest-asyncio
