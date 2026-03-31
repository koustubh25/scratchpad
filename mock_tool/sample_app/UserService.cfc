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

        <cfif qUser.locked_until GT now()>
            <cfthrow type="AccountLocked" message="Account is locked">
        </cfif>

        <cfif NOT hashVerify(arguments.password, qUser.password_hash)>
            <cfquery datasource="#variables.dsn#">
                UPDATE users
                SET failed_attempts = failed_attempts + 1,
                    locked_until = CASE WHEN failed_attempts >= 2 THEN <cfqueryparam cfsqltype="cf_sql_timestamp" value="#dateAdd('n', 30, now())#"> ELSE locked_until END
                WHERE id = <cfqueryparam cfsqltype="cf_sql_integer" value="#qUser.id#">
            </cfquery>
            <cfthrow type="InvalidCredentials" message="Invalid password">
        </cfif>

        <cfquery datasource="#variables.dsn#">
            UPDATE users SET failed_attempts = 0, last_login = <cfqueryparam cfsqltype="cf_sql_timestamp" value="#now()#">
            WHERE id = <cfqueryparam cfsqltype="cf_sql_integer" value="#qUser.id#">
        </cfquery>

        <cfset session.userId = qUser.id>
        <cfset session.userRole = qUser.role>
        <cfset session.userEmail = qUser.email>

        <cfreturn {id: qUser.id, email: qUser.email, role: qUser.role}>
    </cffunction>

    <cffunction name="getUserById" access="public" returntype="query">
        <cfargument name="userId" type="numeric" required="true">

        <cfquery name="qUser" datasource="#variables.dsn#">
            SELECT id, email, first_name, last_name, role, created_at
            FROM users
            WHERE id = <cfqueryparam cfsqltype="cf_sql_integer" value="#arguments.userId#">
        </cfquery>

        <cfreturn qUser>
    </cffunction>

    <cffunction name="updateProfile" access="public" returntype="void">
        <cfargument name="userId" type="numeric" required="true">
        <cfargument name="firstName" type="string" required="true">
        <cfargument name="lastName" type="string" required="true">
        <cfargument name="email" type="string" required="true">

        <cfquery name="qExisting" datasource="#variables.dsn#">
            SELECT id FROM users
            WHERE email = <cfqueryparam cfsqltype="cf_sql_varchar" value="#arguments.email#">
            AND id != <cfqueryparam cfsqltype="cf_sql_integer" value="#arguments.userId#">
        </cfquery>

        <cfif qExisting.recordCount GT 0>
            <cfthrow type="DuplicateEmail" message="Email already in use">
        </cfif>

        <cfquery datasource="#variables.dsn#">
            UPDATE users
            SET first_name = <cfqueryparam cfsqltype="cf_sql_varchar" value="#arguments.firstName#">,
                last_name = <cfqueryparam cfsqltype="cf_sql_varchar" value="#arguments.lastName#">,
                email = <cfqueryparam cfsqltype="cf_sql_varchar" value="#arguments.email#">,
                updated_at = <cfqueryparam cfsqltype="cf_sql_timestamp" value="#now()#">
            WHERE id = <cfqueryparam cfsqltype="cf_sql_integer" value="#arguments.userId#">
        </cfquery>

        <cfif arguments.email NEQ session.userEmail>
            <cfset session.userEmail = arguments.email>
        </cfif>
    </cffunction>

</cfcomponent>
