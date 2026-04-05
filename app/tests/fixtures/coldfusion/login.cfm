<cfif structKeyExists(form, "email") AND structKeyExists(form, "password")>
    <cftry>
        <cfset userService = createObject("component", "UserService")>
        <cfset result = userService.authenticate(form.email, form.password)>
        <cflocation url="/dashboard.cfm" addtoken="false">
    <cfcatch type="InvalidCredentials">
        <cfset errorMessage = "Invalid email or password.">
    </cfcatch>
    <cfcatch type="AccountLocked">
        <cfset errorMessage = "Your account has been locked. Please try again in 30 minutes.">
    </cfcatch>
    </cftry>
</cfif>

<!DOCTYPE html>
<html>
<body>
    <cfform action="/login.cfm" method="post">
        <cfinput type="text" name="email" id="email" required="true">
        <cfinput type="password" name="password" id="password" required="true">
    </cfform>
</body>
</html>
