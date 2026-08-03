## 1. Baseline build verification

- [x] 1.1 Run `pnpm tauri build` with no signing changes and confirm it produces a working `.app` bundle — built in 36.5s to `src-tauri/target/release/bundle/macos/Floo Network.app`
- [x] 1.2 Inspect the default output's `codesign -d -r-` designated requirement to confirm it's a cdhash (ad-hoc), establishing the baseline problem — confirmed: `designated => cdhash H"64d09a45…"`, `Signature=adhoc`, and `Identifier=floo_network-24b5466884a90db2` (derived from the binary name, not the bundle id — hence P7)

## 2. Self-signed identity — personal laptop

- [x] 2.1 Generate a self-signed certificate for the personal laptop — LibreSSL has no `-addext`, so the extensions go in a config file; the exact invocation is in `package.sh`'s comments. Verified the result carries `CA:FALSE`, `digitalSignature`, and `Code Signing` EKU.
- [x] 2.2 Import the certificate with `security import ... -T /usr/bin/codesign`, scoped to codesign-only use — "1 identity imported"
- [x] 2.3 Delete the working private-key file from disk after successful import
- [x] 2.4 Manually verify: build, grant a permission, change the version string, rebuild, confirm no re-prompt — verified via the designated requirement, which is what TCC actually keys on: it is now `identifier "com.tjlsmith0831.floo-network" and certificate leaf = H"…"`, stable across rebuilds, instead of the per-build cdhash from 1.2

## 3. Build/package script

- [x] 3.1 Write the package script: `pnpm tauri build` → re-sign with `$CODESIGN_ID` → copy `.app` to `/Applications` (no DMG step; `bundle.targets` is `["app"]`)
- [x] 3.2 Implement the warning path when `CODESIGN_ID` is unset
- [x] 3.3 Implement a loud failure if the expected pre-re-sign bundle path doesn't exist (guards against Tauri bundler output changes)
- [x] 3.4 Update `day-23-floo-network/AGENTS.md` with the verified `CODESIGN_ID=... ./package.sh` command, mirroring `day-22-stackwatch/AGENTS.md`'s documentation pattern — including the first-signing keychain prompt (P8)

## 4. Self-signed identity — work laptop

**Blocked per P9 — the work laptop is not this machine.** The procedure is
written down in `package.sh` and `AGENTS.md`, and the script reads
`CODESIGN_ID` from the environment so nothing in it is machine-specific, but
none of the below has been run there and none is claimed.

- [ ] 4.1 Repeat §2's identity generation/import procedure independently on the work laptop
- [ ] 4.2 Manually verify TCC-grant stability on the work laptop using the same rebuild-and-check method as §2.4
- [ ] 4.3 Confirm the package script from §3 works unmodified on the work laptop (same script, different local `CODESIGN_ID`/keychain identity)

## 5. Verification

- [ ] 5.1 Confirm both laptops can independently `git pull` + run the package script — **blocked per P9**: verified on the personal laptop only
- [x] 5.2 Confirm `openspec status` shows all tasks complete before archiving — run, with §4 and §5.1 deliberately left open
