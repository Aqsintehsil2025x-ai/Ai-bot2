# XFA Downloads and Release Delivery

The official XFA website is the user-facing download hub. Release binaries are built and published as versioned GitHub Release assets; the website links to the official assets and displays version/platform/checksum metadata. Do not commit installer binaries into the source repository.

## Planned website routes
- /xfa — authenticated web chat only.
- /xfa/downloads — public download catalogue and release notes.
- /xfa/downloads/latest — latest stable release metadata and platform links.
- /xfa/account — sign-in and account settings.
- /xfa/extensions — connected providers and permission management.
- /xfa/resources — account-level repositories, documents, and links.

The public website must not expose a browser terminal, local filesystem, command execution, or device-control interface.

## Release matrix
- Windows: signed x64 installer (.exe or .msi); add ARM64 only after tested builds exist.
- Linux: AppImage and/or .deb for supported architectures.
- macOS: signed and notarized .dmg/.pkg for supported architectures.
- Android: signed .apk for direct download. If an app store release is added later, publish that as a separate official option.

Never show a platform as downloadable until its artifact exists, has passed CI, and has a published checksum. Do not link to guessed asset names.

## Release integrity and trust
- Use immutable version tags (for example v0.1.0) and GitHub Releases.
- Attach SHA-256 checksums for every binary; publish the checksum file alongside the assets.
- Sign desktop installers and Android APKs. Keep signing keys in protected release secrets, never in source control or Replit client-visible configuration.
- Build from reviewed tags using CI. Do not publish from a developer's unreviewed working tree.
- Show version, platform, architecture, file size, release date, changelog, and SHA-256 on the website.
- Use HTTPS and link only to the official XFA release assets.
- Keep older supported versions available and clearly mark them as older; provide a rollback/revocation process for compromised releases.

## Update behavior
- The app checks a signed release manifest from the official service.
- Updates are opt-in or explicitly confirmed by the user; never silently replace application files.
- Verify signature and checksum before installation.
- The app must clearly show release notes and requested permission changes before an update.
- Mobile platform installation behavior must follow Android's own permission and installation model.

## Current state
This is a release design only. No installer binaries or release workflow are available yet. The website must show "Coming soon" for platforms without a verified artifact, not fake download buttons.
