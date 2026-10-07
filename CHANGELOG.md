# Changelog

Notable user-facing changes for focuslog are listed here. Versions follow the project manifest.

## [1.1.0] - 2026-10-06

### Added

- Public documentation for installation, configuration, troubleshooting, privacy, contribution, and security.
- Built-in read-only demo mode, a labeled preview, animated tour, and compact/detail screenshots.
- Automated classifier, dashboard, HTTP, install, upgrade, and uninstall regression tests.
- Native Omarchy Quickshell bar widget entry as `Widget.qml`.
- Installer migration that appends default `[jev]` settings to an existing config and saves `config.toml.before-jev` first.

> **Upgrade from the private prototype:** Public history starts with a sanitized release snapshot. Re-clone the repository instead of pulling the rewritten history; your separately stored configuration and study database are preserved when you rerun the installer.

### Changed

- Updated the marketplace plugin manifest to version 1.1.0.
- Set `daily_goal_minutes = 0` to disable the daily goal and goal notification.
- Keep marketplace-managed plugin Git checkouts on uninstall; remove one separately with `omarchy plugin remove piyush97.focuslog`.
- Classifier setting changes invalidate cached automatic verdicts while preserving manual user labels.

### Fixed

- Focus-percentage rendering and mobile layout.
- Native Quattro lock queries no longer suppress their answer.
- Helium browser classification order.
- String and object bar-layout entries during installation/removal.
- Plugin discovery is awaited before activation.
- Jev failures use a retry cooldown rather than a request every sample.

### Security

- Require HTTPS for Jev requests and reject redirects.
- Bind the dashboard to loopback and validate Host and Fetch metadata without enabling CORS.

## [1.0.0] - Initial project release

- Track focused-window study, waste, and neutral time on Omarchy/Hyprland.
- Provide local rules and optional Jev classification, dashboard, terminal report, manual labels, notifications, and Omarchy/Waybar bar integration.
