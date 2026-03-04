# Security Audit Readiness

This project has been hardened for a baseline web application security audit.

## Implemented Controls

- Session hardening:
  - `HttpOnly`, `Secure` (production), `SameSite=Lax`
  - Permanent session timeout (`SESSION_LIFETIME_MINUTES`, default 120)
  - Session reset on successful login (session fixation mitigation)
- CSRF protection:
  - Global CSRF check for authenticated unsafe methods (`POST/PUT/PATCH/DELETE`)
  - Token is injected globally into all forms and AJAX/fetch requests
- Security headers:
  - `Content-Security-Policy`
  - `X-Frame-Options: DENY`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy`
  - `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`
  - `Strict-Transport-Security` in production
- Brute-force login protection:
  - IP-based rate limiting with temporary lockout
  - Configurable via:
    - `LOGIN_RATE_LIMIT_WINDOW_SECONDS`
    - `LOGIN_RATE_LIMIT_MAX_ATTEMPTS`
    - `LOGIN_RATE_LIMIT_BLOCK_SECONDS`
- Upload and request safety:
  - Global request body limit (`MAX_CONTENT_LENGTH`)
  - Existing upload checks retained (extension, size, PDF signature)
- Access control hardening:
  - Petition-level authorization added to petition view/action
  - Petition file access now checks petition visibility
  - Profile photo access restricted to owner or super admin
- Credential policy:
  - Password complexity checks enforced for reset/create/update/recovery flows
  - Minimum 8 chars + upper/lower/digit/special
- OTP transport hardening:
  - OTP endpoints are required to use `https://` by default
  - Internal `http://` is blocked unless explicitly approved via:
    - `OTP_ALLOW_HTTP_INTERNAL=1`
    - `OTP_HTTP_ALLOWED_HOSTS`
    - `OTP_HTTP_EXCEPTION_TICKET`
    - `OTP_HTTP_EXCEPTION_APPROVED_BY`
    - `OTP_HTTP_EXCEPTION_REASON`

## Environment Checklist (Before External Audit)

- Set `APP_ENV=production`.
- Set a strong `SECRET_KEY` (not default).
- Serve app only behind HTTPS termination.
- Store `.env` securely (not public).
- Rotate admin credentials and database credentials.
- Ensure database backups are encrypted and access-controlled.
- Enable centralized log retention and alerting.

## Recommended Next Enhancements (Optional but Valuable)

- Add account lock/unlock workflow in DB (persistent lockouts).
- Add MFA for all privileged roles (not only OTP toggle).
- Add automated dependency vulnerability scan in CI.
- Add structured security event logs (auth failures, privilege changes).
