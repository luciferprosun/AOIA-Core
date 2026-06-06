# Secret Management

AOIA-Core must not store real secrets in git.

- Never commit real secrets.
- Use `.env.local` for local development secrets.
- Use provider secret managers for deployment where possible.
- Use one key per provider and purpose.
- Use minimum scopes.
- Set expiry dates where possible.
- Set AI provider spending limits where possible.
- Disable withdrawals on trading keys.
- Never paste secrets into ChatGPT/Codex.
- Rotate immediately if a secret is exposed.
- Keep a private inventory with token name, provider, purpose, scope, creation date, expiry, storage location, and owner. Do not store the secret value in the inventory.
