<cfcomponent displayname="OrderService" extends="BaseService" output="false">

    <cfset variables.dsn = application.datasource>

    <cffunction name="createOrder" access="public" returntype="numeric">
        <cfargument name="userId" type="numeric" required="true">
        <cfargument name="items" type="array" required="true">

        <cfset var orderTotal = 0>

        <cfloop array="#arguments.items#" index="item">
            <cfquery name="qProduct" datasource="#variables.dsn#">
                SELECT price, stock_quantity FROM products
                WHERE id = <cfqueryparam cfsqltype="cf_sql_integer" value="#item.productId#">
            </cfquery>

            <cfif qProduct.stock_quantity LT item.quantity>
                <cfthrow type="InsufficientStock"
                         message="Not enough stock for product #item.productId#">
            </cfif>

            <cfset orderTotal = orderTotal + (qProduct.price * item.quantity)>
        </cfloop>

        <cfif orderTotal GT 10000>
            <cfset orderTotal = orderTotal * 0.95>
        </cfif>

        <cftransaction>
            <cfquery name="qOrder" datasource="#variables.dsn#" result="orderResult">
                INSERT INTO orders (user_id, total, status, created_at)
                VALUES (
                    <cfqueryparam cfsqltype="cf_sql_integer" value="#arguments.userId#">,
                    <cfqueryparam cfsqltype="cf_sql_decimal" value="#orderTotal#">,
                    'pending',
                    <cfqueryparam cfsqltype="cf_sql_timestamp" value="#now()#">
                )
            </cfquery>

            <cfset var orderId = orderResult.generatedKey>

            <cfloop array="#arguments.items#" index="item">
                <cfquery datasource="#variables.dsn#">
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                    VALUES (
                        <cfqueryparam cfsqltype="cf_sql_integer" value="#orderId#">,
                        <cfqueryparam cfsqltype="cf_sql_integer" value="#item.productId#">,
                        <cfqueryparam cfsqltype="cf_sql_integer" value="#item.quantity#">,
                        <cfqueryparam cfsqltype="cf_sql_decimal" value="#item.unitPrice#">
                    )
                </cfquery>

                <cfquery datasource="#variables.dsn#">
                    UPDATE products
                    SET stock_quantity = stock_quantity - <cfqueryparam cfsqltype="cf_sql_integer" value="#item.quantity#">
                    WHERE id = <cfqueryparam cfsqltype="cf_sql_integer" value="#item.productId#">
                </cfquery>
            </cfloop>
        </cftransaction>

        <cfreturn orderId>
    </cffunction>

    <cffunction name="getOrdersByUser" access="public" returntype="query">
        <cfargument name="userId" type="numeric" required="true">

        <cfquery name="qOrders" datasource="#variables.dsn#">
            SELECT o.id, o.total, o.status, o.created_at,
                   COUNT(oi.id) as item_count
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.user_id = <cfqueryparam cfsqltype="cf_sql_integer" value="#arguments.userId#">
            GROUP BY o.id, o.total, o.status, o.created_at
            ORDER BY o.created_at DESC
        </cfquery>

        <cfreturn qOrders>
    </cffunction>

    <cffunction name="cancelOrder" access="public" returntype="void">
        <cfargument name="orderId" type="numeric" required="true">
        <cfargument name="userId" type="numeric" required="true">

        <cfquery name="qOrder" datasource="#variables.dsn#">
            SELECT id, status, user_id FROM orders
            WHERE id = <cfqueryparam cfsqltype="cf_sql_integer" value="#arguments.orderId#">
        </cfquery>

        <cfif qOrder.recordCount EQ 0>
            <cfthrow type="OrderNotFound" message="Order not found">
        </cfif>

        <cfif qOrder.user_id NEQ arguments.userId>
            <cfthrow type="Unauthorized" message="Not your order">
        </cfif>

        <cfif qOrder.status NEQ "pending">
            <cfthrow type="InvalidState" message="Only pending orders can be cancelled">
        </cfif>

        <cftransaction>
            <cfquery name="qItems" datasource="#variables.dsn#">
                SELECT product_id, quantity FROM order_items
                WHERE order_id = <cfqueryparam cfsqltype="cf_sql_integer" value="#arguments.orderId#">
            </cfquery>

            <cfloop query="qItems">
                <cfquery datasource="#variables.dsn#">
                    UPDATE products
                    SET stock_quantity = stock_quantity + <cfqueryparam cfsqltype="cf_sql_integer" value="#qItems.quantity#">
                    WHERE id = <cfqueryparam cfsqltype="cf_sql_integer" value="#qItems.product_id#">
                </cfquery>
            </cfloop>

            <cfquery datasource="#variables.dsn#">
                UPDATE orders SET status = 'cancelled'
                WHERE id = <cfqueryparam cfsqltype="cf_sql_integer" value="#arguments.orderId#">
            </cfquery>
        </cftransaction>
    </cffunction>

</cfcomponent>
