<cfcomponent displayname="OrderService" extends="BaseService" output="false">
    <cfset variables.dsn = application.datasource>

    <cffunction name="createOrder" access="public" returntype="numeric">
        <cfargument name="userId" type="numeric" required="true">
        <cfargument name="items" type="array" required="true">

        <cfquery name="qProduct" datasource="#variables.dsn#">
            SELECT price, stock_quantity FROM products
            WHERE id = <cfqueryparam cfsqltype="cf_sql_integer" value="#item.productId#">
        </cfquery>

        <cfif qProduct.stock_quantity LT item.quantity>
            <cfthrow type="InsufficientStock" message="Not enough stock">
        </cfif>

        <cftransaction>
            <cfquery name="qOrder" datasource="#variables.dsn#">
                INSERT INTO orders (user_id, total, status)
                VALUES (
                    <cfqueryparam cfsqltype="cf_sql_integer" value="#arguments.userId#">,
                    <cfqueryparam cfsqltype="cf_sql_decimal" value="#orderTotal#">,
                    'pending'
                )
            </cfquery>

            <cfquery datasource="#variables.dsn#">
                INSERT INTO order_items (order_id, product_id, quantity)
                VALUES (
                    <cfqueryparam cfsqltype="cf_sql_integer" value="#orderId#">,
                    <cfqueryparam cfsqltype="cf_sql_integer" value="#item.productId#">,
                    <cfqueryparam cfsqltype="cf_sql_integer" value="#item.quantity#">
                )
            </cfquery>
        </cftransaction>
    </cffunction>
</cfcomponent>
