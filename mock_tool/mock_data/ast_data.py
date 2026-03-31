"""Pre-built AST data for sample ColdFusion app."""

from core.models import (
    ASTComponent, ASTFunction, ASTArgument, ASTQuery,
    ASTScopeWrite, ASTConditional, ASTFunctionCall
)


def get_user_service_ast() -> ASTComponent:
    return ASTComponent(
        name="UserService",
        file="UserService.cfc",
        type="component",
        extends="BaseService",
        properties=[
            {"name": "dsn", "type": "string", "scope": "variables", "value": "application.datasource"}
        ],
        functions=[
            ASTFunction(
                name="authenticate",
                access="public",
                return_type="struct",
                arguments=[
                    ASTArgument("email", "string", required=True),
                    ASTArgument("password", "string", required=True),
                ],
                queries=[
                    ASTQuery(
                        name="qUser",
                        sql="SELECT id, email, password_hash, role, failed_attempts, locked_until FROM users WHERE email = ?",
                        tables=["users"],
                        operation="SELECT",
                        params=[{"value": "arguments.email", "type": "cf_sql_varchar"}],
                    ),
                    ASTQuery(
                        name="(inline)",
                        sql="UPDATE users SET failed_attempts = failed_attempts + 1, locked_until = CASE WHEN failed_attempts >= 2 THEN ? ELSE locked_until END WHERE id = ?",
                        tables=["users"],
                        operation="UPDATE",
                        params=[
                            {"value": "dateAdd('n', 30, now())", "type": "cf_sql_timestamp"},
                            {"value": "qUser.id", "type": "cf_sql_integer"},
                        ],
                    ),
                    ASTQuery(
                        name="(inline)",
                        sql="UPDATE users SET failed_attempts = 0, last_login = ? WHERE id = ?",
                        tables=["users"],
                        operation="UPDATE",
                        params=[
                            {"value": "now()", "type": "cf_sql_timestamp"},
                            {"value": "qUser.id", "type": "cf_sql_integer"},
                        ],
                    ),
                ],
                scope_writes=[
                    ASTScopeWrite("session", "userId", "qUser.id"),
                    ASTScopeWrite("session", "userRole", "qUser.role"),
                    ASTScopeWrite("session", "userEmail", "qUser.email"),
                ],
                conditionals=[
                    ASTConditional("qUser.recordCount EQ 0", "throw", "InvalidCredentials: User not found"),
                    ASTConditional("qUser.locked_until GT now()", "throw", "AccountLocked: Account is locked"),
                    ASTConditional("NOT hashVerify(password, password_hash)", "throw", "InvalidCredentials: Invalid password"),
                ],
                function_calls=[
                    ASTFunctionCall("hashVerify", ["arguments.password", "qUser.password_hash"]),
                ],
                returns={"type": "struct", "keys": ["id", "email", "role"]},
            ),
            ASTFunction(
                name="getUserById",
                access="public",
                return_type="query",
                arguments=[
                    ASTArgument("userId", "numeric", required=True),
                ],
                queries=[
                    ASTQuery(
                        name="qUser",
                        sql="SELECT id, email, first_name, last_name, role, created_at FROM users WHERE id = ?",
                        tables=["users"],
                        operation="SELECT",
                        params=[{"value": "arguments.userId", "type": "cf_sql_integer"}],
                    ),
                ],
                returns={"type": "query", "columns": ["id", "email", "first_name", "last_name", "role", "created_at"]},
            ),
            ASTFunction(
                name="updateProfile",
                access="public",
                return_type="void",
                arguments=[
                    ASTArgument("userId", "numeric", required=True),
                    ASTArgument("firstName", "string", required=True),
                    ASTArgument("lastName", "string", required=True),
                    ASTArgument("email", "string", required=True),
                ],
                queries=[
                    ASTQuery(
                        name="qExisting",
                        sql="SELECT id FROM users WHERE email = ? AND id != ?",
                        tables=["users"],
                        operation="SELECT",
                        params=[
                            {"value": "arguments.email", "type": "cf_sql_varchar"},
                            {"value": "arguments.userId", "type": "cf_sql_integer"},
                        ],
                    ),
                    ASTQuery(
                        name="(inline)",
                        sql="UPDATE users SET first_name = ?, last_name = ?, email = ?, updated_at = ? WHERE id = ?",
                        tables=["users"],
                        operation="UPDATE",
                        params=[
                            {"value": "arguments.firstName", "type": "cf_sql_varchar"},
                            {"value": "arguments.lastName", "type": "cf_sql_varchar"},
                            {"value": "arguments.email", "type": "cf_sql_varchar"},
                            {"value": "now()", "type": "cf_sql_timestamp"},
                            {"value": "arguments.userId", "type": "cf_sql_integer"},
                        ],
                    ),
                ],
                scope_writes=[
                    ASTScopeWrite("session", "userEmail", "arguments.email"),
                ],
                conditionals=[
                    ASTConditional("qExisting.recordCount GT 0", "throw", "DuplicateEmail: Email already in use"),
                    ASTConditional("arguments.email NEQ session.userEmail", "set", "Update session email"),
                ],
            ),
        ],
    )


def get_login_ast() -> ASTComponent:
    return ASTComponent(
        name="login",
        file="login.cfm",
        type="template",
        functions=[
            ASTFunction(
                name="(page_logic)",
                access="public",
                return_type="void",
                conditionals=[
                    ASTConditional(
                        "structKeyExists(form, 'email') AND structKeyExists(form, 'password')",
                        "process_form",
                        "Form submission handler"
                    ),
                ],
                function_calls=[
                    ASTFunctionCall("createObject", ["component", "UserService"]),
                    ASTFunctionCall("userService.authenticate", ["form.email", "form.password"]),
                ],
            ),
        ],
    )


def get_order_service_ast() -> ASTComponent:
    return ASTComponent(
        name="OrderService",
        file="OrderService.cfc",
        type="component",
        extends="BaseService",
        properties=[
            {"name": "dsn", "type": "string", "scope": "variables", "value": "application.datasource"}
        ],
        functions=[
            ASTFunction(
                name="createOrder",
                access="public",
                return_type="numeric",
                arguments=[
                    ASTArgument("userId", "numeric", required=True),
                    ASTArgument("items", "array", required=True),
                ],
                queries=[
                    ASTQuery(
                        name="qProduct",
                        sql="SELECT price, stock_quantity FROM products WHERE id = ?",
                        tables=["products"],
                        operation="SELECT",
                        params=[{"value": "item.productId", "type": "cf_sql_integer"}],
                    ),
                    ASTQuery(
                        name="qOrder",
                        sql="INSERT INTO orders (user_id, total, status, created_at) VALUES (?, ?, 'pending', ?)",
                        tables=["orders"],
                        operation="INSERT",
                        params=[
                            {"value": "arguments.userId", "type": "cf_sql_integer"},
                            {"value": "orderTotal", "type": "cf_sql_decimal"},
                            {"value": "now()", "type": "cf_sql_timestamp"},
                        ],
                    ),
                    ASTQuery(
                        name="(inline_items)",
                        sql="INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                        tables=["order_items"],
                        operation="INSERT",
                    ),
                    ASTQuery(
                        name="(inline_stock)",
                        sql="UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?",
                        tables=["products"],
                        operation="UPDATE",
                    ),
                ],
                conditionals=[
                    ASTConditional("qProduct.stock_quantity LT item.quantity", "throw", "InsufficientStock"),
                    ASTConditional("orderTotal GT 10000", "set", "Apply 5% bulk discount"),
                ],
                returns={"type": "numeric", "description": "orderId"},
            ),
            ASTFunction(
                name="getOrdersByUser",
                access="public",
                return_type="query",
                arguments=[
                    ASTArgument("userId", "numeric", required=True),
                ],
                queries=[
                    ASTQuery(
                        name="qOrders",
                        sql="SELECT o.id, o.total, o.status, o.created_at, COUNT(oi.id) as item_count FROM orders o LEFT JOIN order_items oi ON o.id = oi.order_id WHERE o.user_id = ? GROUP BY o.id, o.total, o.status, o.created_at ORDER BY o.created_at DESC",
                        tables=["orders", "order_items"],
                        operation="SELECT",
                        params=[{"value": "arguments.userId", "type": "cf_sql_integer"}],
                    ),
                ],
                returns={"type": "query"},
            ),
            ASTFunction(
                name="cancelOrder",
                access="public",
                return_type="void",
                arguments=[
                    ASTArgument("orderId", "numeric", required=True),
                    ASTArgument("userId", "numeric", required=True),
                ],
                queries=[
                    ASTQuery(
                        name="qOrder",
                        sql="SELECT id, status, user_id FROM orders WHERE id = ?",
                        tables=["orders"],
                        operation="SELECT",
                    ),
                    ASTQuery(
                        name="qItems",
                        sql="SELECT product_id, quantity FROM order_items WHERE order_id = ?",
                        tables=["order_items"],
                        operation="SELECT",
                    ),
                    ASTQuery(
                        name="(inline_restore)",
                        sql="UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?",
                        tables=["products"],
                        operation="UPDATE",
                    ),
                    ASTQuery(
                        name="(inline_cancel)",
                        sql="UPDATE orders SET status = 'cancelled' WHERE id = ?",
                        tables=["orders"],
                        operation="UPDATE",
                    ),
                ],
                conditionals=[
                    ASTConditional("qOrder.recordCount EQ 0", "throw", "OrderNotFound"),
                    ASTConditional("qOrder.user_id NEQ arguments.userId", "throw", "Unauthorized"),
                    ASTConditional("qOrder.status NEQ 'pending'", "throw", "InvalidState: Only pending orders can be cancelled"),
                ],
            ),
        ],
    )


ALL_ASTS = {
    "UserService": get_user_service_ast,
    "login": get_login_ast,
    "OrderService": get_order_service_ast,
}
