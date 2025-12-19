# FastAPI Clean Architecture Refactoring

This skill teaches how to transform bloated FastAPI handlers into a clean layered architecture with thin handlers, service classes, repositories, and domain exceptions.

## When to Use This Skill

Invoke this skill when:
- Refactoring FastAPI routers that contain business logic
- Handlers have try/except blocks catching generic exceptions
- Handlers directly access databases or ORMs
- You need to introduce proper separation of concerns
- Converting a monolithic FastAPI app to layered architecture

## Target Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Router Layer                        │
│   Thin handlers: receive request, call service, return   │
└─────────────────────────┬───────────────────────────────┘
                          │ Depends()
┌─────────────────────────▼───────────────────────────────┐
│                     Service Layer                        │
│   Business logic, validation, orchestration              │
│   Raises domain exceptions (never HTTPException)         │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                   Repository Layer                       │
│   Data access abstraction, ORM queries                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│               Exception Handlers (main.py)               │
│   Convert domain exceptions → HTTP responses             │
└─────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Responsibility | What It Should NOT Do |
|-------|---------------|----------------------|
| **Router** | Receive HTTP request, call service, return response | Business logic, DB access, try/except |
| **Service** | Business logic, validation, orchestration | HTTP concerns, direct DB queries |
| **Repository** | Data access, ORM operations | Business logic, HTTP concerns |
| **Exceptions** | Domain-specific error types | Contain HTTP status codes |
| **Exception Handlers** | Map domain exceptions to HTTP responses | Business logic |

## Code Smells to Identify

### 1. Handlers with try/except blocks

```python
# BAD: Handler catching exceptions
@router.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        # ... logic ...
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### 2. Handlers with direct database access

```python
# BAD: Handler querying database directly
@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### 3. Handlers containing business logic

```python
# BAD: Handler with validation and conditionals
@router.post("/orders")
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    if order.quantity > 100:
        raise HTTPException(status_code=400, detail="Max quantity is 100")

    total = order.quantity * order.unit_price
    if total > 10000:
        # apply discount
        total = total * 0.9

    # ... more logic ...
```

### 4. Generic exceptions for domain errors

```python
# BAD: Using ValueError for domain errors
def register_user(username: str):
    if username_exists(username):
        raise ValueError("Username already taken")  # Too generic
```

## Refactoring Steps

### Step 1: Create Domain Exceptions

Create a dedicated exceptions module with a base class and specific exceptions:

```python
# app/exceptions.py
class DomainException(Exception):
    """Base class for all domain exceptions."""
    pass


class EntityNotFoundError(DomainException):
    """Raised when a requested entity does not exist."""
    def __init__(self, entity: str, identifier: str | int):
        self.entity = entity
        self.identifier = identifier
        super().__init__(f"{entity} with id '{identifier}' not found")


class UsernameAlreadyExistsError(DomainException):
    """Raised when attempting to register with an existing username."""
    def __init__(self, username: str):
        self.username = username
        super().__init__(f"Username '{username}' is already registered")


class EmailAlreadyExistsError(DomainException):
    """Raised when attempting to register with an existing email."""
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Email '{email}' is already registered")


class InsufficientPermissionsError(DomainException):
    """Raised when user lacks required permissions."""
    def __init__(self, action: str):
        self.action = action
        super().__init__(f"Insufficient permissions to {action}")


class ValidationError(DomainException):
    """Raised for domain-level validation failures."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Validation error on '{field}': {message}")
```

### Step 2: Create Exception Handlers

Register global exception handlers that convert domain exceptions to HTTP responses:

```python
# app/exception_handlers.py
from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions import (
    DomainException,
    EntityNotFoundError,
    UsernameAlreadyExistsError,
    EmailAlreadyExistsError,
    InsufficientPermissionsError,
    ValidationError,
)


async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    """Default handler for unhandled domain exceptions."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "type": exc.__class__.__name__}
    )


async def not_found_handler(request: Request, exc: EntityNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "detail": str(exc),
            "type": "EntityNotFoundError",
            "entity": exc.entity,
            "identifier": exc.identifier
        }
    )


async def conflict_handler(request: Request, exc: UsernameAlreadyExistsError | EmailAlreadyExistsError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc), "type": exc.__class__.__name__}
    )


async def forbidden_handler(request: Request, exc: InsufficientPermissionsError) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"detail": str(exc), "type": "InsufficientPermissionsError"}
    )


async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": str(exc),
            "type": "ValidationError",
            "field": exc.field
        }
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(EntityNotFoundError, not_found_handler)
    app.add_exception_handler(UsernameAlreadyExistsError, conflict_handler)
    app.add_exception_handler(EmailAlreadyExistsError, conflict_handler)
    app.add_exception_handler(InsufficientPermissionsError, forbidden_handler)
    app.add_exception_handler(ValidationError, validation_handler)
    # Generic handler last (catches any DomainException subclass not handled above)
    app.add_exception_handler(DomainException, domain_exception_handler)
```

### Step 3: Create Repository Layer

Extract all data access to repository classes:

```python
# app/repositories/user_repository.py
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    """Data access layer for User entities."""

    def __init__(self, db: Session):
        self._db = db

    def find_by_id(self, user_id: int) -> User | None:
        return self._db.query(User).filter(User.id == user_id).first()

    def find_by_username(self, username: str) -> User | None:
        return self._db.query(User).filter(User.username == username).first()

    def find_by_email(self, email: str) -> User | None:
        return self._db.query(User).filter(User.email == email).first()

    def exists_by_username(self, username: str) -> bool:
        return self.find_by_username(username) is not None

    def exists_by_email(self, email: str) -> bool:
        return self.find_by_email(email) is not None

    def save(self, user: User) -> User:
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self._db.delete(user)
        self._db.commit()
```

### Step 4: Create Service Layer

Extract business logic to service classes that use repositories:

```python
# app/services/user_service.py
from passlib.context import CryptContext

from app.models import User
from app.repositories.user_repository import UserRepository
from app.exceptions import (
    UsernameAlreadyExistsError,
    EmailAlreadyExistsError,
    EntityNotFoundError,
)


class UserService:
    """Business logic for user operations."""

    def __init__(self, repository: UserRepository):
        self._repository = repository
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def get_by_id(self, user_id: int) -> User:
        user = self._repository.find_by_id(user_id)
        if not user:
            raise EntityNotFoundError("User", user_id)
        return user

    def register(self, username: str, email: str, password: str) -> User:
        if self._repository.exists_by_username(username):
            raise UsernameAlreadyExistsError(username)

        if self._repository.exists_by_email(email):
            raise EmailAlreadyExistsError(email)

        user = User(
            username=username,
            email=email,
            hashed_password=self._pwd_context.hash(password)
        )
        return self._repository.save(user)

    def update_email(self, user_id: int, new_email: str) -> User:
        user = self.get_by_id(user_id)

        if self._repository.exists_by_email(new_email):
            raise EmailAlreadyExistsError(new_email)

        user.email = new_email
        return self._repository.save(user)
```

### Step 5: Create Dependency Injection

Set up FastAPI dependencies for wiring:

```python
# app/dependencies.py
from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_user_service(
    repository: UserRepository = Depends(get_user_repository)
) -> UserService:
    return UserService(repository)
```

### Step 6: Create Thin Handlers

Refactor handlers to only delegate to services:

```python
# app/routers/users.py
from fastapi import APIRouter, Depends

from app.schemas import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService
from app.dependencies import get_user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register_user(
    user: UserCreate,
    service: UserService = Depends(get_user_service)
):
    return service.register(user.username, user.email, user.password)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service)
):
    return service.get_by_id(user_id)


@router.patch("/{user_id}/email", response_model=UserResponse)
def update_email(
    user_id: int,
    update: UserUpdate,
    service: UserService = Depends(get_user_service)
):
    return service.update_email(user_id, update.email)
```

### Step 7: Wire Everything in main.py

```python
# app/main.py
from fastapi import FastAPI

from app.routers import users, orders
from app.exception_handlers import register_exception_handlers

app = FastAPI(title="Clean Architecture API")

# Register exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(users.router)
app.include_router(orders.router)
```

## Complete Before/After Example

### BEFORE: Bloated Handler

```python
# BAD: Everything in one place
@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Direct DB access in handler
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        # HTTP concern mixed with business logic
        raise HTTPException(status_code=400, detail="Username already registered")

    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Business logic in handler
    hashed_password = pwd_context.hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )

    # Direct DB manipulation
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
```

### AFTER: Clean Architecture

**exceptions.py:**
```python
class DomainException(Exception):
    pass

class UsernameAlreadyExistsError(DomainException):
    def __init__(self, username: str):
        super().__init__(f"Username '{username}' is already registered")

class EmailAlreadyExistsError(DomainException):
    def __init__(self, email: str):
        super().__init__(f"Email '{email}' is already registered")
```

**exception_handlers.py:**
```python
from fastapi import Request
from fastapi.responses import JSONResponse
from app.exceptions import DomainException

async def domain_exception_handler(request: Request, exc: DomainException):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

def register_exception_handlers(app):
    app.add_exception_handler(DomainException, domain_exception_handler)
```

**repository.py:**
```python
from sqlalchemy.orm import Session
from app.models import User

class UserRepository:
    def __init__(self, db: Session):
        self._db = db

    def exists_by_username(self, username: str) -> bool:
        return self._db.query(User).filter(User.username == username).first() is not None

    def exists_by_email(self, email: str) -> bool:
        return self._db.query(User).filter(User.email == email).first() is not None

    def save(self, user: User) -> User:
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user
```

**service.py:**
```python
from passlib.context import CryptContext
from app.models import User
from app.repositories.user_repository import UserRepository
from app.exceptions import UsernameAlreadyExistsError, EmailAlreadyExistsError

class UserService:
    def __init__(self, repository: UserRepository):
        self._repository = repository
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def register(self, username: str, email: str, password: str) -> User:
        if self._repository.exists_by_username(username):
            raise UsernameAlreadyExistsError(username)

        if self._repository.exists_by_email(email):
            raise EmailAlreadyExistsError(email)

        user = User(
            username=username,
            email=email,
            hashed_password=self._pwd_context.hash(password)
        )
        return self._repository.save(user)
```

**router.py:**
```python
from fastapi import APIRouter, Depends
from app.schemas import UserCreate, UserResponse
from app.services.user_service import UserService
from app.dependencies import get_user_service

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/register", response_model=UserResponse, status_code=201)
def register_user(user: UserCreate, service: UserService = Depends(get_user_service)):
    return service.register(user.username, user.email, user.password)
```

**main.py:**
```python
from fastapi import FastAPI
from app.routers.users import router
from app.exception_handlers import register_exception_handlers

app = FastAPI()
register_exception_handlers(app)
app.include_router(router)
```

## Edge Case: Handler Coordinating Multiple Services

When a handler needs to coordinate multiple services, keep it thin but allow orchestration:

```python
@router.post("/onboard", response_model=OnboardingResponse, status_code=201)
def onboard_user(
    data: OnboardingRequest,
    user_service: UserService = Depends(get_user_service),
    billing_service: BillingService = Depends(get_billing_service),
    email_service: EmailService = Depends(get_email_service)
):
    # Orchestration is OK in handlers when coordinating services
    user = user_service.register(data.username, data.email, data.password)
    billing_service.create_trial(user.id)
    email_service.send_welcome(user.email)
    return OnboardingResponse(user_id=user.id)
```

For complex orchestration with transactions, create an **application service**:

```python
# app/services/onboarding_service.py
class OnboardingService:
    def __init__(
        self,
        user_service: UserService,
        billing_service: BillingService,
        email_service: EmailService
    ):
        self._user_service = user_service
        self._billing_service = billing_service
        self._email_service = email_service

    def onboard(self, username: str, email: str, password: str) -> User:
        user = self._user_service.register(username, email, password)
        self._billing_service.create_trial(user.id)
        self._email_service.send_welcome(user.email)
        return user
```

## Refactoring Checklist

Use this checklist to verify the refactor is complete:

### Domain Exceptions
- [ ] Created `exceptions.py` with `DomainException` base class
- [ ] Replaced all `ValueError`, `Exception` raises with domain-specific exceptions
- [ ] Domain exceptions do NOT contain HTTP status codes
- [ ] Each exception has a meaningful message

### Exception Handlers
- [ ] Created `exception_handlers.py`
- [ ] Registered handlers in `main.py` via `register_exception_handlers(app)`
- [ ] Handlers map domain exceptions to appropriate HTTP status codes
- [ ] Handlers return consistent JSON error format

### Repository Layer
- [ ] Created repository class for each entity
- [ ] All database queries moved from handlers to repositories
- [ ] Repository methods are focused (single responsibility)
- [ ] Repository receives `Session` via constructor

### Service Layer
- [ ] Created service class for each domain area
- [ ] All business logic moved from handlers to services
- [ ] Services raise domain exceptions (never `HTTPException`)
- [ ] Services receive repositories via constructor
- [ ] Services do NOT import FastAPI modules

### Router/Handler Layer
- [ ] Handlers only call services and return responses
- [ ] No `try/except` blocks in handlers
- [ ] No direct database access in handlers
- [ ] No business logic in handlers
- [ ] Dependencies injected via `Depends()`

### Dependency Injection
- [ ] Created `dependencies.py` with factory functions
- [ ] Repository factories receive `db: Session = Depends(get_db)`
- [ ] Service factories receive repositories via `Depends()`

### Final Verification
- [ ] All tests pass
- [ ] No `HTTPException` raised outside of exception handlers
- [ ] No ORM imports in router files
- [ ] Handler functions are under 10 lines
- [ ] Service methods have single responsibility

## Directory Structure

After refactoring, your project should look like:

```
app/
├── __init__.py
├── main.py                 # App factory, register handlers
├── database.py             # DB session management
├── exceptions.py           # Domain exceptions
├── exception_handlers.py   # HTTP error mapping
├── dependencies.py         # Dependency injection factories
├── models/
│   ├── __init__.py
│   └── user.py
├── schemas/
│   ├── __init__.py
│   └── user.py
├── repositories/
│   ├── __init__.py
│   └── user_repository.py
├── services/
│   ├── __init__.py
│   └── user_service.py
└── routers/
    ├── __init__.py
    └── users.py
```
