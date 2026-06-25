# Changelog

All notable changes to FrinkLoop are tracked here. Follows [semantic versioning](https://semver.org/).

## [1.0.0] — 2026-06-25

### Changed
- First stable marketplace release.
- Flattened repository structure: plugin source moved from `01_Codebase/plugin/` to `plugin/` at root; docs moved to `docs/`; tests moved to `tests/`.
- Completed `plugin.json` and `marketplace.json` with full metadata (version, license, repository, engines, skills and commands lists).
- Fixed `frinkloop-new.md` command: removed Plan 1 stub, now hands off to `mvp-loop` skill after intake.
- Added `UPLOAD.md` with step-by-step publication instructions.

### Security
- Removed committed `.env` file. Added `.env.example` with placeholder values. `.gitignore` now excludes `.env` and `.frinkloop/` directories.

### Fixed
- Updated test paths to reflect new `plugin/` root structure.
