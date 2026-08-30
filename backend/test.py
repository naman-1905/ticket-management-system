import requests
import uuid
import sys

BASE_URL = "http://127.0.0.1:8000"

# ---------------------------------------------------------------------------
# TEST ACCOUNTS
# ---------------------------------------------------------------------------

CUSTOMER = {
    "email": "customer@example.com",
    "password": "Customer@2026!",
}

AGENT = {
    "email": "agent@example.com",
    "password": "Agent@2026!",
}

ADMIN = {
    "email": "admin@example.com",
    "password": "Admin@2026!",
}

# Unique user for registration test
SMOKE_EMAIL = f"smoke_{uuid.uuid4().hex[:8]}@example.com"
SMOKE_PASSWORD = "SmokeTest123!"
SMOKE_NAME = "API Smoke Test User"

passed = 0
failed = 0
results = []


# ---------------------------------------------------------------------------
# HTTP TEST HELPER
# ---------------------------------------------------------------------------

def test(name, method, path, expected, headers=None, **kwargs):
    global passed, failed

    url = BASE_URL + path

    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            timeout=10,
            **kwargs,
        )

        ok = response.status_code in expected

        if ok:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"

        results.append((status, name, response.status_code))

        print(
            f"[{status}] "
            f"{method:<6} "
            f"{path:<55} "
            f"{response.status_code}"
        )

        if not ok:
            try:
                print("       ", response.json())
            except Exception:
                print("       ", response.text[:500])

        return response

    except Exception as e:
        failed += 1
        results.append(("FAIL", name, "ERROR"))

        print(
            f"[FAIL] "
            f"{method:<6} "
            f"{path:<55} "
            f"ERROR: {e}"
        )

        return None


# ---------------------------------------------------------------------------
# AUTH HELPERS
# ---------------------------------------------------------------------------

def login_account(label, account):
    response = test(
        f"{label} login",
        "POST",
        "/api/v1/auth/login",
        {200},
        json={
            "email": account["email"],
            "password": account["password"],
        },
    )

    if response is None or response.status_code != 200:
        return None

    data = response.json()

    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    if not access_token or not refresh_token:
        print(f"[FAIL] {label} login did not return both tokens")
        return None

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "headers": {
            "Authorization": f"Bearer {access_token}",
        },
    }


def assert_forbidden(label, method, path, headers=None, **kwargs):
    return test(
        label,
        method,
        path,
        {403},
        headers=headers,
        **kwargs,
    )


# ===========================================================================
# HEADER
# ===========================================================================

print("=" * 100)
print("FASTAPI FULL ROLE-AWARE API SMOKE TEST")
print("=" * 100)
print(f"Base URL : {BASE_URL}")
print(f"Smoke user: {SMOKE_EMAIL}")
print("=" * 100)


# ===========================================================================
# HEALTH / META
# ===========================================================================

print("\n[1] HEALTH / META")
print("-" * 100)

test(
    "Root",
    "GET",
    "/",
    {200},
)

test(
    "Health",
    "GET",
    "/health",
    {200},
)

test(
    "Healthz",
    "GET",
    "/healthz",
    {200},
)

test(
    "Database health",
    "GET",
    "/health/db",
    {200},
)

test(
    "Version",
    "GET",
    "/api/v1/meta/version",
    {200},
)


# ===========================================================================
# REGISTRATION
# ===========================================================================

print("\n[2] REGISTRATION")
print("-" * 100)

register = test(
    "Register new CUSTOMER",
    "POST",
    "/api/v1/auth/register",
    {200, 201},
    json={
        "email": SMOKE_EMAIL,
        "full_name": SMOKE_NAME,
        "password": SMOKE_PASSWORD,
    },
)

if register is None or register.status_code not in {200, 201}:
    print("\nRegistration failed.")
    print("Continuing with seeded accounts.")


# ===========================================================================
# LOGIN ALL ROLES
# ===========================================================================

print("\n[3] ROLE AUTHENTICATION")
print("-" * 100)

customer = login_account("CUSTOMER", CUSTOMER)
agent = login_account("AGENT", AGENT)
admin = login_account("ADMIN", ADMIN)
print("\nADMIN ACCESS TOKEN:")
print(admin["access_token"])
print()

if not customer or not agent or not admin:
    print("\nOne or more seeded accounts could not authenticate.")
    print("Cannot perform the complete role-aware test.")
    sys.exit(1)


# ===========================================================================
# AUTH / ME
# ===========================================================================

print("\n[4] AUTH / ME")
print("-" * 100)

test(
    "CUSTOMER /me",
    "GET",
    "/api/v1/auth/me",
    {200},
    headers=customer["headers"],
)

test(
    "AGENT /me",
    "GET",
    "/api/v1/auth/me",
    {200},
    headers=agent["headers"],
)

test(
    "ADMIN /me",
    "GET",
    "/api/v1/auth/me",
    {200},
    headers=admin["headers"],
)


# ===========================================================================
# USER AUTHORIZATION
# ===========================================================================

print("\n[5] USER AUTHORIZATION")
print("-" * 100)

# ADMIN should be allowed
test(
    "ADMIN list users",
    "GET",
    "/api/v1/users",
    {200},
    headers=admin["headers"],
)

# CUSTOMER should be forbidden
assert_forbidden(
    "CUSTOMER list users forbidden",
    "GET",
    "/api/v1/users",
    headers=customer["headers"],
)

# AGENT should be tested against the actual endpoint authorization
agent_users = test(
    "AGENT list users",
    "GET",
    "/api/v1/users",
    {200, 403},
    headers=agent["headers"],
)


# ===========================================================================
# SLA AUTHORIZATION
# ===========================================================================

print("\n[6] SLA POLICIES")
print("-" * 100)

# ADMIN
sla_admin = test(
    "ADMIN list SLA policies",
    "GET",
    "/api/v1/sla/policies",
    {200},
    headers=admin["headers"],
)

# CUSTOMER should not access SLA administration
assert_forbidden(
    "CUSTOMER SLA policies forbidden",
    "GET",
    "/api/v1/sla/policies",
    headers=customer["headers"],
)

# AGENT authorization depends on router policy
test(
    "AGENT list SLA policies",
    "GET",
    "/api/v1/sla/policies",
    {200, 403},
    headers=agent["headers"],
)


# ===========================================================================
# CUSTOMER - CREATE TICKET
# ===========================================================================

print("\n[7] CUSTOMER TICKET FLOW")
print("-" * 100)

idempotency_key = f"smoke-ticket-{uuid.uuid4()}"

ticket = test(
    "CUSTOMER create ticket",
    "POST",
    "/api/v1/tickets",
    {201},
    headers={
        **customer["headers"],
        "Idempotency-Key": idempotency_key,
    },
    json={
        "title": "API Smoke Test Ticket",
        "description": "Created automatically by the role-aware API smoke test.",
        "priority": "P3",
        "category": "TEST",
    },
)

ticket_id = None

if ticket is not None and ticket.status_code == 201:
    try:
        ticket_data = ticket.json()
        ticket_id = ticket_data.get("id")
        print(f"       Ticket ID: {ticket_id}")
    except Exception as e:
        print(f"[FAIL] Could not parse created ticket: {e}")


# ===========================================================================
# CUSTOMER - IDEMPOTENCY
# ===========================================================================

if ticket_id:
    print("\n[8] IDEMPOTENCY")
    print("-" * 100)

    duplicate = test(
        "Duplicate ticket request returns same result",
        "POST",
        "/api/v1/tickets",
        {200, 201},
        headers={
            **customer["headers"],
            "Idempotency-Key": idempotency_key,
        },
        json={
            "title": "THIS SHOULD NOT CREATE A SECOND TICKET",
            "description": "Idempotency verification.",
            "priority": "P3",
            "category": "TEST",
        },
    )

    if duplicate is not None and duplicate.status_code in {200, 201}:
        try:
            duplicate_data = duplicate.json()

            if duplicate_data.get("id") == ticket_id:
                print("[PASS] Idempotency returned the original ticket")
            else:
                print("[FAIL] Idempotency returned a different ticket")
                failed += 1
                passed -= 1

        except Exception:
            pass


# ===========================================================================
# CUSTOMER - TICKET OPERATIONS
# ===========================================================================

if ticket_id:

    print("\n[9] CUSTOMER TICKET OPERATIONS")
    print("-" * 100)

    test(
        "CUSTOMER list tickets",
        "GET",
        "/api/v1/tickets",
        {200},
        headers=customer["headers"],
    )

    test(
        "CUSTOMER get ticket",
        "GET",
        f"/api/v1/tickets/{ticket_id}",
        {200},
        headers=customer["headers"],
    )

    test(
        "CUSTOMER list comments",
        "GET",
        f"/api/v1/tickets/{ticket_id}/comments",
        {200},
        headers=customer["headers"],
    )

    test(
        "CUSTOMER create public comment",
        "POST",
        f"/api/v1/tickets/{ticket_id}/comments",
        {201},
        headers=customer["headers"],
        json={
            "body": "Customer smoke-test comment.",
            "is_internal": False,
        },
    )

    test(
        "CUSTOMER get ticket SLA",
        "GET",
        f"/api/v1/tickets/{ticket_id}/sla",
        {200},
        headers=customer["headers"],
    )

    # CUSTOMER must NOT be allowed to move OPEN -> IN_PROGRESS
    assert_forbidden(
        "CUSTOMER cannot set IN_PROGRESS",
        "PATCH",
        f"/api/v1/tickets/{ticket_id}/status",
        headers=customer["headers"],
        json={
            "status": "IN_PROGRESS",
        },
    )

    # CUSTOMER must NOT assign
    assert_forbidden(
        "CUSTOMER cannot assign ticket",
        "POST",
        f"/api/v1/tickets/{ticket_id}/assign",
        headers=customer["headers"],
        json={
            "assignee_id": "00000000-0000-0000-0000-000000000000",
        },
    )


# ===========================================================================
# AGENT - TICKET OPERATIONS
# ===========================================================================

if ticket_id:

    print("\n[10] AGENT TICKET OPERATIONS")
    print("-" * 100)

    test(
        "AGENT list tickets",
        "GET",
        "/api/v1/tickets",
        {200},
        headers=agent["headers"],
    )

    test(
        "AGENT get customer ticket",
        "GET",
        f"/api/v1/tickets/{ticket_id}",
        {200},
        headers=agent["headers"],
    )

    # OPEN -> IN_PROGRESS is valid for AGENT
    test(
        "AGENT set ticket IN_PROGRESS",
        "PATCH",
        f"/api/v1/tickets/{ticket_id}/status",
        {200},
        headers=agent["headers"],
        json={
            "status": "IN_PROGRESS",
        },
    )

    # Get agent/admin ID from ADMIN users endpoint
    users_response = requests.get(
        BASE_URL + "/api/v1/users",
        headers=admin["headers"],
        timeout=10,
    )

    assignee_id = None

    if users_response.status_code == 200:
        try:
            users_data = users_response.json()

            if isinstance(users_data, list):
                user_list = users_data
            elif isinstance(users_data, dict):
                user_list = (
                    users_data.get("items")
                    or users_data.get("users")
                    or []
                )
            else:
                user_list = []

            for user in user_list:
                if user.get("role") == "AGENT" and user.get("is_active", True):
                    assignee_id = user.get("id")
                    break

        except Exception:
            pass

    if assignee_id:
        test(
            "AGENT assign ticket",
            "POST",
            f"/api/v1/tickets/{ticket_id}/assign",
            {200},
            headers=agent["headers"],
            json={
                "assignee_id": assignee_id,
            },
        )
    else:
        print("[SKIP] AGENT assign ticket - no active AGENT ID found")

    test(
        "AGENT create comment",
        "POST",
        f"/api/v1/tickets/{ticket_id}/comments",
        {201},
        headers=agent["headers"],
        json={
            "body": "Agent smoke-test comment.",
            "is_internal": False,
        },
    )

    test(
        "AGENT create internal comment",
        "POST",
        f"/api/v1/tickets/{ticket_id}/comments",
        {201},
        headers=agent["headers"],
        json={
            "body": "Internal agent smoke-test comment.",
            "is_internal": True,
        },
    )

    test(
        "AGENT get ticket SLA",
        "GET",
        f"/api/v1/tickets/{ticket_id}/sla",
        {200},
        headers=agent["headers"],
    )


# ===========================================================================
# ADMIN - TICKET / AUDIT OPERATIONS
# ===========================================================================

if ticket_id:

    print("\n[11] ADMIN OPERATIONS")
    print("-" * 100)

    test(
        "ADMIN list tickets",
        "GET",
        "/api/v1/tickets",
        {200},
        headers=admin["headers"],
    )

    test(
        "ADMIN get ticket",
        "GET",
        f"/api/v1/tickets/{ticket_id}",
        {200},
        headers=admin["headers"],
    )

    test(
        "ADMIN audit logs",
        "GET",
        "/api/v1/audit/logs",
        {200},
        headers=admin["headers"],
    )

    test(
        "ADMIN list SLA policies",
        "GET",
        "/api/v1/sla/policies",
        {200},
        headers=admin["headers"],
    )


# ===========================================================================
# AUTH - REFRESH TOKEN ROTATION
# ===========================================================================

print("\n[12] REFRESH TOKEN ROTATION")
print("-" * 100)

# Login a fresh CUSTOMER session specifically for refresh testing.
refresh_session = login_account(
    "CUSTOMER refresh-test",
    CUSTOMER,
)

if refresh_session:

    original_refresh_token = refresh_session["refresh_token"]

    refresh = test(
        "Refresh token",
        "POST",
        "/api/v1/auth/refresh",
        {200},
        json={
            "refresh_token": original_refresh_token,
        },
    )

    new_refresh_token = None
    new_access_token = None

    if refresh is not None and refresh.status_code == 200:
        try:
            refresh_data = refresh.json()

            new_access_token = refresh_data["access_token"]
            new_refresh_token = refresh_data["refresh_token"]

            new_auth_headers = {
                "Authorization": f"Bearer {new_access_token}",
            }

        except Exception as e:
            print(f"[FAIL] Could not parse refresh response: {e}")

    # -----------------------------------------------------------------------
    # Old token must be rejected after rotation.
    # -----------------------------------------------------------------------

    if new_refresh_token:

        test(
            "Old refresh token rejected after rotation",
            "POST",
            "/api/v1/auth/refresh",
            {400, 401, 403},
            json={
                "refresh_token": original_refresh_token,
            },
        )

        # -------------------------------------------------------------------
        # LOGOUT
        # -------------------------------------------------------------------

        logout = test(
            "Logout",
            "POST",
            "/api/v1/auth/logout",
            {200, 204},
            headers=new_auth_headers,
            json={
                "refresh_token": new_refresh_token,
            },
        )

        # -------------------------------------------------------------------
        # Refresh after logout MUST fail.
        # -------------------------------------------------------------------

        test(
            "Refresh after logout should fail",
            "POST",
            "/api/v1/auth/refresh",
            {400, 401, 403},
            json={
                "refresh_token": new_refresh_token,
            },
        )


# ===========================================================================
# SUMMARY
# ===========================================================================

print("\n")
print("=" * 100)
print("TEST SUMMARY")
print("=" * 100)

for status, name, code in results:
    print(f"{status:<6} {name:<45} {code}")

print("-" * 100)
print(f"PASSED : {passed}")
print(f"FAILED : {failed}")
print(f"TOTAL  : {passed + failed}")
print("=" * 100)

if failed:
    print("\nAPI SMOKE TEST FAILED")
    sys.exit(1)

print("\nALL API SMOKE TESTS PASSED")

