"""1Password Connect Secrets Provider for Nautobot."""

from django import forms
from django.conf import settings
from nautobot.core.forms import BootstrapMixin
from nautobot.extras.secrets import SecretsProvider, exceptions

try:
    from httpx import HTTPError
    from onepasswordconnectsdk.client import new_client
    from onepasswordconnectsdk.errors import FailedToRetrieveItemException, FailedToRetrieveVaultException
except ImportError:
    new_client = None
    CONNECT_EXCEPTIONS = ()
else:
    CONNECT_EXCEPTIONS = (HTTPError, FailedToRetrieveItemException, FailedToRetrieveVaultException)

__all__ = ("OnePasswordConnectSecretsProvider",)


def get_secret_from_connect(vault, item, field, host, token, section=None):
    """Get a secret from a 1Password Connect server.

    Args:
        vault (str): 1Password Vault title where the secret is located.
        item (str): 1Password Item title where the secret is located.
        field (str): 1Password secret field label.
        host (str): 1Password Connect server URL.
        token (str): 1Password Connect API token.
        section (str, optional): 1Password Item Section label for the field. Defaults to None.

    Returns:
        (str): Value from the secret.

    Raises:
        ValueError: If the vault, item, section, or field cannot be found.
    """
    client = new_client(host, token)
    vault_obj = client.get_vault_by_title(vault)
    item_obj = client.get_item_by_title(item, vault_obj.id)

    section_id = None
    if section:
        matching_section = next((s for s in (item_obj.sections or []) if s.label == section), None)
        if matching_section is None:
            raise ValueError(f"Section {section!r} was not found on item {item!r}.")
        section_id = matching_section.id

    for item_field in item_obj.fields or []:
        if item_field.label != field:
            continue
        if section_id is not None and (item_field.section is None or item_field.section.id != section_id):
            continue
        return item_field.value

    raise ValueError(f"Field {field!r} was not found on item {item!r}.")


class OnePasswordConnectSecretsProvider(SecretsProvider):
    """A secrets provider for 1Password Connect."""

    slug = "one-password-connect"
    name = "1Password Connect"
    is_available = new_client is not None

    # TBD: Remove after pylint-nautobot bump
    # pylint: disable-next=nb-incorrect-base-class
    class ParametersForm(BootstrapMixin, forms.Form):
        """Required parameters for 1Password Connect."""

        vault = forms.CharField(
            required=True,
            help_text="The 1Password Vault title to retrieve the secret from.",
        )
        item = forms.CharField(
            required=True,
            help_text="The item in 1Password.",
        )
        section = forms.CharField(
            required=False,
            help_text="The section where the field is a part of.",
        )
        field = forms.CharField(
            required=True,
            help_text="The field where the secret is located. Defaults to 'password'.",
            initial="password",
        )

    @classmethod
    def get_host_and_token(cls, secret):
        """Get the configured 1Password Connect host and token."""
        plugin_settings = getattr(settings, "PLUGINS_CONFIG", {}).get("nautobot_secrets_providers", {})
        connect_settings = plugin_settings.get("one_password_connect", {})
        if not connect_settings:
            raise exceptions.SecretProviderError(secret, cls, "1Password Connect is not configured!")

        host = connect_settings.get("host")
        token = connect_settings.get("token")
        if not host or not token:
            raise exceptions.SecretProviderError(
                secret, cls, "1Password Connect 'host' and 'token' must both be configured!"
            )
        return host, token

    @classmethod
    def get_value_for_secret(cls, secret, obj=None, **kwargs):
        """Get the value for a secret from 1Password Connect."""
        if not cls.is_available:
            raise exceptions.SecretProviderError(secret, cls, "The 1Password Connect SDK is not installed!")

        host, token = cls.get_host_and_token(secret)
        parameters = secret.rendered_parameters(obj=obj)

        try:
            return get_secret_from_connect(
                vault=parameters["vault"],
                item=parameters["item"],
                field=parameters["field"],
                host=host,
                token=token,
                section=parameters.get("section", None),
            )
        except ValueError as exc:
            raise exceptions.SecretProviderError(secret, cls, str(exc)) from exc
        except CONNECT_EXCEPTIONS as exc:
            raise exceptions.SecretProviderError(secret, cls, "Unable to retrieve secret from 1Password Connect.") from exc
