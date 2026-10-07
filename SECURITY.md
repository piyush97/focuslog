# Security policy

## Supported versions

Security fixes are developed against the latest version on the default branch. If a released version is affected, update to a fixed release when one is available.

## Report a vulnerability

Please do not report vulnerabilities in public GitHub issues. If private vulnerability reporting is enabled, use GitHub's **Report a vulnerability** option on the repository's Security tab. Otherwise, contact the repository maintainer privately through GitHub. Include the affected version or commit, impact, and reproduction steps. Remove secrets and private window data from logs; do not include API keys, personal activity databases, or unredacted window titles.

Please allow the maintainer time to assess and address a report before public disclosure.

## Security considerations

focuslog stores window titles and app classes in a local SQLite database. Jev mode sends the configured goal, active app class, and active window title to the configured HTTPS TypeSafe AI endpoint. The optional key is stored in `~/.config/focuslog/env`; the installer sets mode `0600`. Treat local database and config files as sensitive.

The dashboard binds to loopback and applies Host and Fetch metadata checks, but does not authenticate local users. Do not expose it to untrusted networks. See [Privacy and data](docs/privacy.md) for details.
