## Why

Floo Network needs to run as an installed, permission-stable app on both the personal and work laptop (per the project's core cross-machine requirement). Without a stable code-signing identity, every rebuild presents as a new app to macOS's TCC system, forcing the user to re-grant filesystem/folder-access permissions after every change — exactly the problem already solved once in this repo for `day-22-stackwatch`.

## What Changes

- Add a self-signed code-signing identity generation/import procedure (one per machine), following the `day-22-stackwatch` precedent: generate, import scoped to `codesign` only, remove the private key from disk.
- Add a `package.sh`-equivalent build script: `pnpm tauri build` → post-build re-sign with the machine's stable identity → copy the `.app` directly to `/Applications` (no DMG).
- Document the per-machine setup procedure in `day-23-floo-network/AGENTS.md` so both laptops can be brought up independently.
- No auto-update mechanism — both laptops `git pull` and re-run the package script whenever they want the latest version.

## Capabilities

### New Capabilities

- `app-packaging`: build-script wrapping, post-build code signing with a stable self-signed identity, direct `/Applications` install, per-machine setup documentation.

### Modified Capabilities

None.

## Impact

- New build tooling: a shell script (`package.sh` or equivalent) in `day-23-floo-network/`.
- New per-machine, out-of-repo state: a self-signed certificate in each machine's login keychain (private key never persisted to disk after import, per `day-22-stackwatch`'s precedent).
- `day-23-floo-network/AGENTS.md` gains a documented per-machine setup procedure (identity generation, verification steps).
- No network infrastructure, no update server, no Apple Developer Program account.
- Depends on changes 1–3 existing as buildable code; can be specified now but isn't meaningfully runnable until at least change 1 (and ideally all three) are implemented.
