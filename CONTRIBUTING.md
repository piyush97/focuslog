# Contributing

Contributions to focuslog are welcome. Keep changes focused, explain the user-visible behavior, and update documentation when behavior or setup changes.

## Before you start

1. Open an issue to discuss a substantial behavior change before investing in implementation.
2. Fork the repository and create a branch for your change.
3. Keep pull requests focused; avoid unrelated formatting or refactoring.

## Local setup

focuslog requires Python 3.11 or later. The tracker itself uses Python's standard library. Tests also require Node.js 22+ and `jq` for the dashboard and installer regression checks. For safe local development, run the test suite before and after your changes:

```sh
python3 -m unittest discover -s tests -v
bash -n install.sh uninstall.sh
python3 -m py_compile focuslog.py
```

The tests use mocks and temporary directories for classifier, installer, and HTTP behavior. They do not verify integration with a live Jev account or a running Omarchy/Quickshell desktop. Native UI and marketplace validation require an Omarchy environment.

## Pull requests

- Describe the problem and the change, including any user-visible impact.
- Include reproduction steps for a bug fix where practical.
- Add or update tests for behavior changes.
- Update `README.md` or the relevant guide if install, configuration, privacy, or troubleshooting instructions change.
- Do not include API keys, personal window-title samples, local databases, or unredacted screenshots.
- State what you tested and identify anything you could not test.

## Documentation and release notes

Use concise, task-oriented Markdown. Make commands copyable, use meaningful image alt text, and do not claim that native Omarchy or hosted-classifier behavior was tested unless it was. Add user-facing changes to `CHANGELOG.md`.

## Reporting a vulnerability

Do not report security vulnerabilities in a public issue. Follow the private reporting instructions in [SECURITY.md](SECURITY.md).
