"""Sources — one module per federated canonical.

Importing this package registers the built-in sources into the default registry.
"""

from iris.sources import cli_json  # noqa: F401  (import for self-registration)
from iris.sources import constellation  # noqa: F401  (import for self-registration)
