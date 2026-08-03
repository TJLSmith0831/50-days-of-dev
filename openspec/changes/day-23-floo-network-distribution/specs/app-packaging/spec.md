## ADDED Requirements

### Requirement: Generate and import a per-machine self-signed identity
The system SHALL provide a documented, repeatable procedure to generate a self-signed code-signing certificate on a machine and import it into that machine's login keychain, scoped so only `codesign` can use it without prompting, with the private key removed from disk after import.

#### Scenario: First-time setup on a machine
- **WHEN** the user runs the identity-setup procedure on a machine that has no Floo Network signing identity yet
- **THEN** a self-signed certificate is created, imported via `security import ... -T /usr/bin/codesign`, and the working private-key file is deleted, leaving the key only in the login keychain

### Requirement: Build and sign the app with a stable identity
The system SHALL provide a build script that runs `pnpm tauri build`, then re-signs the resulting `.app` bundle with the machine's stable self-signed identity, overriding Tauri's default ad-hoc signature.

#### Scenario: Building the app
- **WHEN** the user runs the package script with `CODESIGN_ID` set to the machine's identity
- **THEN** the script builds via `pnpm tauri build` and re-signs the output bundle so its designated requirement is bundle-id + certificate, not a cdhash

#### Scenario: Building without CODESIGN_ID set
- **WHEN** the user runs the package script without `CODESIGN_ID` set
- **THEN** the script warns that the resulting ad-hoc-signed bundle will lose TCC permission grants on every subsequent rebuild

### Requirement: Install directly to /Applications without a DMG
The system SHALL copy the signed `.app` bundle directly to `/Applications`, without producing or requiring a `.dmg` disk image.

#### Scenario: Installing after a successful build
- **WHEN** the package script completes a successful build and sign
- **THEN** the resulting `.app` is copied to `/Applications`, replacing any prior version

### Requirement: TCC grant stability across rebuilds
The system's signed bundle SHALL present the same designated requirement (bundle identifier + certificate) across rebuilds on the same machine, so previously granted macOS permissions are not re-prompted.

#### Scenario: Rebuilding with a code change
- **WHEN** the app is rebuilt on a machine with an already-established stable identity, after a source code change
- **THEN** a macOS permission (e.g. folder access) granted to the prior build is not re-requested by the new build
