"""Pre-built architecture decisions for sample app."""


def get_architecture() -> dict:
    return {
        "serviceGroups": [
            {
                "name": "users-service",
                "modules": ["UserService", "login"],
                "sharedTables": ["users"],
                "reason": "Tight coupling: login.cfm directly invokes UserService.authenticate. Shared users table. Session management is co-located.",
                "targetStack": {
                    "frontend": {
                        "adapter": "react",
                        "components": ["LoginPage", "ProfilePage"],
                    },
                    "backend": {
                        "adapter": "go",
                        "components": ["UserHandler", "AuthMiddleware", "UserStore"],
                    },
                },
            },
            {
                "name": "orders-service",
                "modules": ["OrderService"],
                "sharedTables": ["orders", "order_items", "products"],
                "reason": "Self-contained order lifecycle (create, list, cancel) with transactional inventory management. No direct dependency on UserService at the code level — userId passed as parameter.",
                "targetStack": {
                    "frontend": {
                        "adapter": "react",
                        "components": ["OrderListPage", "OrderDetailPage", "CreateOrderPage"],
                    },
                    "backend": {
                        "adapter": "go",
                        "components": ["OrderHandler", "OrderStore", "InventoryStore"],
                    },
                },
            },
        ],
        "apiContracts": [
            {
                "service": "users-service",
                "endpoints": [
                    {
                        "path": "POST /api/auth/login",
                        "request": {"email": "string", "password": "string"},
                        "response": {"token": "string", "user": {"id": "int", "email": "string", "role": "string"}},
                        "source": "UserService.authenticate",
                    },
                    {
                        "path": "GET /api/users/:id",
                        "request": {},
                        "response": {"id": "int", "email": "string", "firstName": "string", "lastName": "string", "role": "string"},
                        "source": "UserService.getUserById",
                    },
                    {
                        "path": "PUT /api/users/:id/profile",
                        "request": {"firstName": "string", "lastName": "string", "email": "string"},
                        "response": {"success": "bool"},
                        "source": "UserService.updateProfile",
                    },
                ],
            },
            {
                "service": "orders-service",
                "endpoints": [
                    {
                        "path": "POST /api/orders",
                        "request": {"items": [{"productId": "int", "quantity": "int"}]},
                        "response": {"orderId": "int", "total": "decimal", "status": "string"},
                        "source": "OrderService.createOrder",
                    },
                    {
                        "path": "GET /api/orders",
                        "request": {},
                        "response": [{"id": "int", "total": "decimal", "status": "string", "itemCount": "int"}],
                        "source": "OrderService.getOrdersByUser",
                    },
                    {
                        "path": "POST /api/orders/:id/cancel",
                        "request": {},
                        "response": {"success": "bool"},
                        "source": "OrderService.cancelOrder",
                    },
                ],
            },
        ],
        "componentRouting": [
            {"source": "UserService.authenticate", "target": "UserHandler.Login", "stackLayer": "backend", "agent": "logic"},
            {"source": "UserService.getUserById", "target": "UserHandler.GetUser", "stackLayer": "backend", "agent": "logic"},
            {"source": "UserService.updateProfile", "target": "UserHandler.UpdateProfile", "stackLayer": "backend", "agent": "logic"},
            {"source": "login.cfm", "target": "LoginPage.tsx", "stackLayer": "frontend", "agent": "ui"},
            {"source": "OrderService.createOrder", "target": "OrderHandler.Create", "stackLayer": "backend", "agent": "logic"},
            {"source": "OrderService.getOrdersByUser", "target": "OrderHandler.List", "stackLayer": "backend", "agent": "logic"},
            {"source": "OrderService.cancelOrder", "target": "OrderHandler.Cancel", "stackLayer": "backend", "agent": "logic"},
        ],
        "dataMapping": {
            "session.userId": "JWT claim: sub",
            "session.userRole": "JWT claim: role",
            "session.userEmail": "JWT claim: email",
            "application.datasource": "Environment variable: DATABASE_URL",
        },
    }


def get_blueprint_index_md() -> str:
    """Top-level summary — the only file reviewers read first."""
    return """# Architecture Blueprint — Legacy CRM Migration

## Executive Summary

The legacy ColdFusion application consists of 3 modules (UserService, OrderService, login page) that should be migrated to **2 service groups**: a Users Service and an Orders Service. Target stack: React (frontend) + Go with Chi router (backend). Session-based auth maps to JWT. All database queries are parameterized — low SQL injection risk in the new system.

Estimated effort: Medium. The codebase is well-structured with clear separation of concerns.

---

## Service Boundaries (Overview)

| Service | Modules | Shared Tables | Rationale | Detail |
|---------|---------|---------------|-----------|--------|
| **users-service** | UserService, login | users | Auth + session management co-located | [users-service.md](services/users-service.md) |
| **orders-service** | OrderService | orders, order_items, products | Self-contained order lifecycle | [orders-service.md](services/orders-service.md) |

```mermaid
flowchart LR
    subgraph "users-service"
        US["UserService.cfc"] --> Login["login.cfm"]
    end
    subgraph "orders-service"
        OS["OrderService.cfc"]
    end
    users-service -->|"userId (JWT)"| orders-service
```

---

## Migration Order

| Phase | Service Group | Risk | Rationale | Review Doc |
|-------|--------------|------|-----------|------------|
| 1 | users-service | Low | Foundation — auth must work before orders can validate users | [users-service.md](services/users-service.md) |
| 2 | orders-service | Medium | Transactional complexity (stock management) | [orders-service.md](services/orders-service.md) |

---

## Cross-Cutting Concerns

See [cross-cutting.md](cross-cutting.md) for:
- State mapping (session → JWT)
- Data migration strategy
- Risk register
- Infrastructure recommendations

---

## AI Confidence Summary

| Section | Confidence | Flagged Items |
|---------|-----------|---------------|
| Service boundaries | 95% | — |
| API contracts | 93% | — |
| Component routing | 91% | — |
| State mapping | 88% | hashVerify compatibility needs verification |
| Migration order | 90% | — |

---

## Review Checklist

- [ ] [users-service.md](services/users-service.md) — Auth, login, profile management
- [ ] [orders-service.md](services/orders-service.md) — Order lifecycle, inventory
- [ ] [cross-cutting.md](cross-cutting.md) — State mapping, risks, infrastructure
"""


def get_service_blueprint_md(service_name: str) -> str:
    """Per-service-group architecture doc — reviewable independently."""
    blueprints = {
        "users-service": """# Users Service — Architecture

**Modules:** UserService.cfc, login.cfm
**Shared Tables:** users
**Migration Phase:** 1 (foundation — must be migrated first)

---

## Why These Modules Are Grouped

Tight coupling: `login.cfm` directly invokes `UserService.authenticate()`. Both modules share the `users` table and session state (`session.userId`, `session.userRole`, `session.userEmail`). Splitting them into separate services would create a synchronous cross-service dependency for every login request.

---

## API Contracts

| Endpoint | Method | Request | Response | Source |
|----------|--------|---------|----------|--------|
| `/api/auth/login` | POST | `{email, password}` | `{token, user}` | UserService.authenticate |
| `/api/users/:id` | GET | — | `{id, email, firstName, lastName, role}` | UserService.getUserById |
| `/api/users/:id/profile` | PUT | `{firstName, lastName, email}` | `{success}` | UserService.updateProfile |

---

## Component Routing

| Legacy Component | Target Component | Stack Layer | Agent |
|-----------------|-----------------|-------------|-------|
| UserService.authenticate | UserHandler.Login | backend (Go) | logic |
| UserService.getUserById | UserHandler.GetUser | backend (Go) | logic |
| UserService.updateProfile | UserHandler.UpdateProfile | backend (Go) | logic |
| login.cfm | LoginPage.tsx | frontend (React) | ui |

---

## Business Rules Preserved

| Rule | Source Function | Detail |
|------|----------------|--------|
| User Authentication | authenticate() | Validates credentials against stored hash, establishes session |
| Account Lockout | authenticate() | After 3 failed attempts, locks account for 30 minutes |
| Failed Attempt Tracking | authenticate() | Increments counter on failure, resets on success |
| Duplicate Email Check | updateProfile() | Prevents email change to an already-used email |
| Session Email Sync | updateProfile() | Updates session email when profile email changes |

---

## Data Access

| Table | Operations | Modules | Parameterized |
|-------|-----------|---------|---------------|
| users | SELECT, UPDATE | UserService (all 3 functions) | Yes |

---

## Risks Specific to This Service

| Risk | Impact | Mitigation |
|------|--------|------------|
| hashVerify() behavior difference | High — broken auth | Verify bcrypt compatibility between CF and Go |
| Session → JWT migration | Medium — existing sessions invalidated | Plan cutover window or dual-auth period |

---

## Approval

- [ ] API contracts reviewed
- [ ] Business rules verified by original developers
- [ ] Component routing confirmed
- [ ] Risks acknowledged
""",
        "orders-service": """# Orders Service — Architecture

**Modules:** OrderService.cfc
**Shared Tables:** orders, order_items, products
**Migration Phase:** 2 (depends on users-service for auth)

---

## Why This Is a Separate Service

Self-contained order lifecycle: create, list, and cancel operations are fully encapsulated in `OrderService.cfc`. The only dependency on users is `userId`, passed as a parameter — no code-level import of UserService. In the modern stack, `userId` comes from the JWT token.

---

## API Contracts

| Endpoint | Method | Request | Response | Source |
|----------|--------|---------|----------|--------|
| `/api/orders` | POST | `{items: [{productId, quantity}]}` | `{orderId, total, status}` | OrderService.createOrder |
| `/api/orders` | GET | — | `[{id, total, status, itemCount}]` | OrderService.getOrdersByUser |
| `/api/orders/:id/cancel` | POST | — | `{success}` | OrderService.cancelOrder |

---

## Component Routing

| Legacy Component | Target Component | Stack Layer | Agent |
|-----------------|-----------------|-------------|-------|
| OrderService.createOrder | OrderHandler.Create | backend (Go) | logic |
| OrderService.getOrdersByUser | OrderHandler.List | backend (Go) | logic |
| OrderService.cancelOrder | OrderHandler.Cancel | backend (Go) | logic |

---

## Business Rules Preserved

| Rule | Source Function | Detail |
|------|----------------|--------|
| Stock Validation | createOrder() | Checks available stock before accepting each line item |
| Bulk Discount | createOrder() | 5% discount applied when order total exceeds $10,000 |
| Transactional Order Creation | createOrder() | Order insert + line items + stock deduction in single transaction |
| Ownership Validation | cancelOrder() | Only the user who placed the order can cancel it |
| Status Guard | cancelOrder() | Only orders in "pending" status can be cancelled |
| Stock Restoration | cancelOrder() | Cancelled order items restore inventory stock (transactional) |

---

## Data Access

| Table | Operations | Functions | Parameterized |
|-------|-----------|-----------|---------------|
| products | SELECT, UPDATE | createOrder, cancelOrder | Yes |
| orders | INSERT, SELECT, UPDATE | createOrder, getOrdersByUser, cancelOrder | Yes |
| order_items | INSERT, SELECT | createOrder, cancelOrder | Yes |

---

## Risks Specific to This Service

| Risk | Impact | Mitigation |
|------|--------|------------|
| Transaction semantics | Medium — inventory inconsistency | Ensure Go DB transactions match CF cftransaction behavior |
| Bulk discount logic | Low — revenue impact | Unit test the 5% threshold ($10,000) explicitly |
| Concurrent cancellation race | Low — stock count drift | Original CF code has same issue; consider row-level locking in Go |

---

## Approval

- [ ] API contracts reviewed
- [ ] Business rules verified (especially bulk discount threshold)
- [ ] Transactional boundaries confirmed
- [ ] Risks acknowledged
""",
    }
    return blueprints.get(service_name, f"# {service_name}\n\nNo blueprint generated.\n")


def get_cross_cutting_md() -> str:
    """Cross-cutting concerns that span all services."""
    return """# Cross-Cutting Concerns

## State Mapping

| Legacy State | Modern Equivalent | Notes |
|-------------|-------------------|-------|
| `session.userId` | JWT claim: `sub` | Set during login, read by all services |
| `session.userRole` | JWT claim: `role` | Used for authorization checks |
| `session.userEmail` | JWT claim: `email` | Updated when profile email changes (requires JWT re-issue) |
| `application.datasource` | Env var: `DATABASE_URL` | Per-service database connection |

### Migration Strategy

ColdFusion uses server-side session state. The modern stack uses stateless JWT tokens. During the migration:

1. Users-service issues JWTs on login (replaces `session.*` writes)
2. All services extract user identity from JWT (replaces `session.*` reads)
3. Profile email changes require JWT re-issue (no server-side session to update)

---

## Data Migration

| Legacy Table | Owning Service | Shared? | Notes |
|-------------|---------------|---------|-------|
| users | users-service | No | Primary user data |
| orders | orders-service | No | Order records |
| order_items | orders-service | No | Order line items |
| products | orders-service | No | Product catalog + inventory |

No shared tables between services — clean separation.

---

## Risk Register

| Risk | Impact | Mitigation | Owner |
|------|--------|------------|-------|
| hashVerify() behavior difference | High — broken auth | Verify bcrypt compatibility between CF and Go implementations | users-service team |
| Transaction semantics | Medium — inventory inconsistency | Ensure Go DB transactions match CF cftransaction behavior | orders-service team |
| Bulk discount logic | Low — revenue impact | Unit test the 5% threshold ($10,000) explicitly | orders-service team |
| Session → JWT migration | Medium — existing sessions invalidated | Plan a cutover window or dual-auth period | users-service team |
| Concurrent cancellation race | Low — stock count drift | Consider row-level locking in Go implementation | orders-service team |

---

## Infrastructure Recommendations

| Concern | Recommendation |
|---------|---------------|
| API Gateway | Single gateway routing to both services, handles CORS + rate limiting |
| Auth Middleware | Shared Go middleware package for JWT validation (used by both services) |
| Database | Separate databases per service (clean ownership), or shared DB with schema-level isolation |
| CI/CD | Independent deploy pipelines per service |
| Monitoring | Per-service health endpoints, shared Grafana dashboards |

---

## Approval

- [ ] State mapping reviewed
- [ ] Data ownership confirmed
- [ ] Risk mitigations accepted
- [ ] Infrastructure approach agreed
"""
