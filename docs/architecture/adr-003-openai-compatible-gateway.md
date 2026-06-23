# Status: Accepted

## Decision

Expose **OpenAI-compatible** endpoints from the gateway (`/v1/chat/completions`, `/v1/models`) for Continue and other clients. Authenticate with bearer API key.

## References

- `apps/gateway/src/annulus_gateway/routes/chat.py`
