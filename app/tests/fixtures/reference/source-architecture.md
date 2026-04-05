# Developer Reviewed Source Architecture

- UserService is responsible for login and user identity workflows.
- OrderService owns order creation and order retrieval behavior.
- The login template delegates into UserService.
- Session state is used for authentication and user identity.
- Tables involved include users, orders, order_items, and products.

