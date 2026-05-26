import os


class SecretLookupError(RuntimeError):
    pass


def read_secret_ref(secret_ref: str | None) -> str | None:
    """Resolve a runtime-only secret reference such as `env:NAME`.

    Secret values returned from this function must not be persisted.
    """

    if not secret_ref:
        return None
    if secret_ref.startswith("env:"):
        name = secret_ref.removeprefix("env:")
        value = os.environ.get(name)
        if value is None:
            raise SecretLookupError(f"Missing environment secret reference: {secret_ref}")
        return value
    raise SecretLookupError(f"Unsupported secret reference scheme: {secret_ref}")
