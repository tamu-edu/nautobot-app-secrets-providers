# 1Password Connect

Requires a self-hosted [1Password Connect server](https://developer.1password.com/docs/connect).

## Prerequisites

You must [deploy a 1Password Connect server](https://developer.1password.com/docs/connect/get-started/#step-1-deploy-connect-server) and [issue an Access Token](https://developer.1password.com/docs/connect/get-started/#step-2-issue-an-access-token) for the vault(s) you want Nautobot to access.

## Configuration

You must provide a mapping in `PLUGINS_CONFIG` within your `nautobot_config.py`, for example:

```python
PLUGINS_CONFIG = {
    "nautobot_secrets_providers": {
        "one_password_connect": {
            "host": os.environ.get("OP_CONNECT_HOST"),
            "token": os.environ.get("OP_CONNECT_TOKEN"),
        },
    },
}
```

- `host` - (required) The URL of the 1Password Connect server.
- `token` - (required) The 1Password Connect API token used to authenticate with the Connect server.

## Usage

When adding a Secret in Nautobot using the 1Password Connect provider, you must supply the following parameters:

- `vault` - (required) The title of the 1Password Vault where the secret is located.
- `item` - (required) The title of the 1Password Item where the secret is located.
- `section` - (optional) The label of the Section within the Item where the field is located.
- `field` - (required) The label of the field where the secret value is located. Defaults to `password`.
