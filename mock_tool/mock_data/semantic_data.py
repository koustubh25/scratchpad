"""Pre-built semantic models for sample ColdFusion app."""


def get_user_service_semantics() -> dict:
    return {
        "module": "UserService",
        "source": "UserService.cfc",
        "functions": [
            {
                "name": "authenticate",
                "signature": {
                    "inputs": [
                        {"name": "email", "type": "string", "required": True},
                        {"name": "password", "type": "string", "required": True},
                    ],
                    "outputs": {"type": "struct", "keys": ["id", "email", "role"]},
                },
                "businessRule": {
                    "name": "User Authentication",
                    "description": "Validates user credentials against stored password hash, enforces account lockout after 3 failed attempts (30-minute lock), resets failure count on success, and establishes user session",
                    "source": "ai",
                    "confidence": 91,
                },
                "dataAccess": [
                    {
                        "table": "users",
                        "operation": "SELECT",
                        "columns": ["id", "email", "password_hash", "role", "failed_attempts", "locked_until"],
                        "filter": "email = ?",
                        "parameterized": True,
                    },
                    {
                        "table": "users",
                        "operation": "UPDATE",
                        "purpose": "Increment failed attempts + lock account if threshold reached",
                        "parameterized": True,
                    },
                    {
                        "table": "users",
                        "operation": "UPDATE",
                        "purpose": "Reset failed attempts + update last_login on success",
                        "parameterized": True,
                    },
                ],
                "stateWrites": [
                    {"scope": "session", "key": "userId"},
                    {"scope": "session", "key": "userRole"},
                    {"scope": "session", "key": "userEmail"},
                ],
                "controlFlow": [
                    {"condition": "no user found", "action": "throw InvalidCredentials"},
                    {"condition": "account locked (locked_until > now)", "action": "throw AccountLocked"},
                    {"condition": "password mismatch", "action": "increment failures + throw InvalidCredentials"},
                    {"condition": "failures >= 3", "action": "lock account for 30 minutes"},
                ],
                "calls": ["hashVerify"],
                "calledBy": ["login.cfm"],
            },
            {
                "name": "getUserById",
                "signature": {
                    "inputs": [{"name": "userId", "type": "numeric", "required": True}],
                    "outputs": {"type": "query", "columns": ["id", "email", "first_name", "last_name", "role", "created_at"]},
                },
                "businessRule": {
                    "name": "User Lookup",
                    "description": "Retrieves a single user record by primary key",
                    "source": "deterministic",
                    "confidence": 99,
                },
                "dataAccess": [
                    {
                        "table": "users",
                        "operation": "SELECT",
                        "columns": ["id", "email", "first_name", "last_name", "role", "created_at"],
                        "filter": "id = ?",
                        "parameterized": True,
                    },
                ],
                "stateWrites": [],
                "controlFlow": [],
                "calls": [],
                "calledBy": [],
            },
            {
                "name": "updateProfile",
                "signature": {
                    "inputs": [
                        {"name": "userId", "type": "numeric", "required": True},
                        {"name": "firstName", "type": "string", "required": True},
                        {"name": "lastName", "type": "string", "required": True},
                        {"name": "email", "type": "string", "required": True},
                    ],
                    "outputs": {"type": "void"},
                },
                "businessRule": {
                    "name": "Profile Update",
                    "description": "Updates user profile fields with duplicate email validation. Syncs session email if changed.",
                    "source": "ai",
                    "confidence": 88,
                },
                "dataAccess": [
                    {
                        "table": "users",
                        "operation": "SELECT",
                        "purpose": "Check for duplicate email (excluding current user)",
                        "parameterized": True,
                    },
                    {
                        "table": "users",
                        "operation": "UPDATE",
                        "purpose": "Update profile fields + updated_at timestamp",
                        "parameterized": True,
                    },
                ],
                "stateWrites": [
                    {"scope": "session", "key": "userEmail", "condition": "only if email changed"},
                ],
                "controlFlow": [
                    {"condition": "email already used by another user", "action": "throw DuplicateEmail"},
                    {"condition": "email changed", "action": "update session.userEmail"},
                ],
                "calls": [],
                "calledBy": [],
            },
        ],
        "dependencies": [],
        "tables": ["users"],
        "complexity": "medium",
    }


def get_login_semantics() -> dict:
    return {
        "module": "login",
        "source": "login.cfm",
        "functions": [
            {
                "name": "(page_logic)",
                "signature": {
                    "inputs": [
                        {"name": "form.email", "type": "string", "required": True},
                        {"name": "form.password", "type": "string", "required": True},
                    ],
                    "outputs": {"type": "redirect_or_page"},
                },
                "businessRule": {
                    "name": "Login Form Handler",
                    "description": "Processes login form submission. On success, redirects to dashboard. On failure, displays error message (different messages for invalid credentials vs locked account).",
                    "source": "ai",
                    "confidence": 94,
                },
                "dataAccess": [],
                "stateWrites": [],
                "controlFlow": [
                    {"condition": "form submitted", "action": "call UserService.authenticate"},
                    {"condition": "InvalidCredentials caught", "action": "display 'Invalid email or password'"},
                    {"condition": "AccountLocked caught", "action": "display lockout message"},
                    {"condition": "auth success", "action": "redirect to /dashboard.cfm"},
                ],
                "calls": ["UserService.authenticate"],
                "calledBy": [],
            },
        ],
        "dependencies": ["UserService"],
        "tables": [],
        "complexity": "low",
        "uiElements": {
            "form": {"action": "/login.cfm", "method": "post", "fields": ["email", "password"]},
            "links": ["/forgot-password.cfm", "/register.cfm"],
            "errorDisplay": "conditional banner",
        },
    }


def get_order_service_semantics() -> dict:
    return {
        "module": "OrderService",
        "source": "OrderService.cfc",
        "functions": [
            {
                "name": "createOrder",
                "signature": {
                    "inputs": [
                        {"name": "userId", "type": "numeric", "required": True},
                        {"name": "items", "type": "array", "required": True},
                    ],
                    "outputs": {"type": "numeric", "description": "new order ID"},
                },
                "businessRule": {
                    "name": "Order Creation",
                    "description": "Creates a new order with stock validation, bulk discount (5% over $10,000), inventory deduction, and transactional integrity",
                    "source": "ai",
                    "confidence": 87,
                },
                "dataAccess": [
                    {"table": "products", "operation": "SELECT", "purpose": "Check price and stock for each item", "parameterized": True},
                    {"table": "orders", "operation": "INSERT", "purpose": "Create order record", "parameterized": True},
                    {"table": "order_items", "operation": "INSERT", "purpose": "Create line items", "parameterized": True},
                    {"table": "products", "operation": "UPDATE", "purpose": "Deduct stock quantity", "parameterized": True},
                ],
                "stateWrites": [],
                "controlFlow": [
                    {"condition": "insufficient stock for any item", "action": "throw InsufficientStock"},
                    {"condition": "order total > $10,000", "action": "apply 5% discount"},
                ],
                "calls": [],
                "calledBy": [],
                "transactional": True,
            },
            {
                "name": "getOrdersByUser",
                "signature": {
                    "inputs": [{"name": "userId", "type": "numeric", "required": True}],
                    "outputs": {"type": "query", "columns": ["id", "total", "status", "created_at", "item_count"]},
                },
                "businessRule": {
                    "name": "Order History",
                    "description": "Retrieves all orders for a user with item count, sorted by most recent",
                    "source": "deterministic",
                    "confidence": 98,
                },
                "dataAccess": [
                    {"table": "orders", "operation": "SELECT", "purpose": "Fetch orders with item count via LEFT JOIN", "parameterized": True},
                ],
                "stateWrites": [],
                "controlFlow": [],
                "calls": [],
                "calledBy": [],
            },
            {
                "name": "cancelOrder",
                "signature": {
                    "inputs": [
                        {"name": "orderId", "type": "numeric", "required": True},
                        {"name": "userId", "type": "numeric", "required": True},
                    ],
                    "outputs": {"type": "void"},
                },
                "businessRule": {
                    "name": "Order Cancellation",
                    "description": "Cancels a pending order with ownership validation, restores inventory stock, and updates order status. Only pending orders can be cancelled.",
                    "source": "ai",
                    "confidence": 90,
                },
                "dataAccess": [
                    {"table": "orders", "operation": "SELECT", "purpose": "Verify order exists and check status/ownership", "parameterized": True},
                    {"table": "order_items", "operation": "SELECT", "purpose": "Get items for stock restoration", "parameterized": True},
                    {"table": "products", "operation": "UPDATE", "purpose": "Restore stock quantities", "parameterized": True},
                    {"table": "orders", "operation": "UPDATE", "purpose": "Set status to 'cancelled'", "parameterized": True},
                ],
                "stateWrites": [],
                "controlFlow": [
                    {"condition": "order not found", "action": "throw OrderNotFound"},
                    {"condition": "order belongs to different user", "action": "throw Unauthorized"},
                    {"condition": "order not in 'pending' status", "action": "throw InvalidState"},
                ],
                "calls": [],
                "calledBy": [],
                "transactional": True,
            },
        ],
        "dependencies": [],
        "tables": ["orders", "order_items", "products"],
        "complexity": "high",
    }


ALL_SEMANTICS = {
    "UserService": get_user_service_semantics,
    "login": get_login_semantics,
    "OrderService": get_order_service_semantics,
}
