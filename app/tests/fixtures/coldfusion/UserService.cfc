<cfcomponent displayname="UserService" extends="BaseService" output="false">
    <cfset variables.dsn = application.datasource>

    <cffunction name="authenticate" access="public" returntype="struct">
        <cfargument name="email" type="string" required="true">
        <cfargument name="password" type="string" required="true">

        <cfquery name="qUser" datasource="#variables.dsn#">
            SELECT id, email, password_hash, role, failed_attempts, locked_until
            FROM users
            WHERE email = <cfqueryparam cfsqltype="cf_sql_varchar" value="#arguments.email#">
        </cfquery>

        <cfif qUser.recordCount EQ 0>
            <cfthrow type="InvalidCredentials" message="User not found">
        </cfif>

        <cfif NOT hashVerify(arguments.password, qUser.password_hash)>
            <cfquery datasource="#variables.dsn#">
                UPDATE users
                SET failed_attempts = failed_attempts + 1
                WHERE id = <cfqueryparam cfsqltype="cf_sql_integer" value="#qUser.id#">
            </cfquery>
            <cfthrow type="InvalidCredentials" message="Invalid password">
        </cfif>

        <cfset session.userId = qUser.id>
        <cfset session.userRole = qUser.role>

        <cfreturn {id: qUser.id, email: qUser.email, role: qUser.role}>
    </cffunction>
</cfcomponent>
