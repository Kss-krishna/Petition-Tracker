# Security Event Logging and Monitoring Policy

## Purpose
Define minimum logging and monitoring controls for authentication, authorization, and request-integrity events.

## Log Format
- Application emits structured JSON security events through `app.logger`.
- Core fields:
  - `event_type`
  - `severity`
  - `ts` (UTC ISO-8601)
  - `path`, `method`, `ip`, `user_agent`
  - `user_id`, `user_role`
  - optional context fields (`petition_id`, `cvo_id`, `owner_id`, etc.)

## Security Events Implemented
- `auth.login_failed`
- `auth.login_lockout_triggered`
- `auth.login_blocked`
- `auth.login_success`
- `web.csrf_validation_failed`
- `access.unauthenticated_request`
- `access.role_forbidden`
- `access.petition_forbidden`
- `access.petition_action_forbidden`
- `access.file_forbidden`
- `access.profile_photo_forbidden`
- `access.api_inspectors_forbidden`

## Severity Mapping
- `info`: successful authentication events.
- `warning`: failed/blocked auth and authorization denials.
- `error`/`critical`: reserved for security-critical failures requiring immediate response.

## Monitoring Requirements
- Centralize logs to SIEM/log platform (e.g., ELK/Splunk/Cloud logging).
- Create alerts for:
  - repeated `auth.login_failed` from same IP/user in short windows
  - `auth.login_lockout_triggered`
  - spikes in `web.csrf_validation_failed`
  - repeated access denial events on protected objects/files
- Correlate by `ip`, `user_id`, and `event_type`.

## Retention and Access
- Retain security logs for at least 180 days (or per policy/regulation, whichever is higher).
- Restrict access to logs to authorized security/admin personnel.
- Protect logs from unauthorized modification/deletion.

## Incident Response Handoff
- On alert, capture:
  - event timeline
  - impacted account/object IDs
  - source IP/user-agent
  - action taken (blocked, reset credential, ticket ID)
- Track resolution in incident register.
