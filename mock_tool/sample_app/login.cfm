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
<head>
    <title>Login</title>
    <link rel="stylesheet" href="/css/styles.css">
</head>
<body>
    <div class="login-container">
        <h1>Sign In</h1>

        <cfif isDefined("errorMessage")>
            <div class="error-banner">
                <cfoutput>#errorMessage#</cfoutput>
            </div>
        </cfif>

        <cfform action="/login.cfm" method="post">
            <div class="form-group">
                <label for="email">Email Address</label>
                <cfinput type="text" name="email" id="email" required="true"
                         validate="email" message="Please enter a valid email">
            </div>

            <div class="form-group">
                <label for="password">Password</label>
                <cfinput type="password" name="password" id="password" required="true">
            </div>

            <div class="form-group">
                <input type="submit" value="Sign In" class="btn-primary">
            </div>

            <div class="form-links">
                <a href="/forgot-password.cfm">Forgot Password?</a>
                <a href="/register.cfm">Create Account</a>
            </div>
        </cfform>
    </div>
</body>
</html>
