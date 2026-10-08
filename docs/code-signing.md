# Packaging procedure

Release artifacts, prerequisites, privacy boundaries, signing policy, and data-preservation requirements are owned by [PRD.md](../PRD.md#packaging). Current build state and the unresolved Windows block are in [project status](PROJECT_STATUS.md). The [first-release plan](superpowers/plans/2026-10-08-first-release-extraction.md#task-5-prepare-installer-in-parallel-and-qualify-after-integration) schedules this work.

The independent safety patch follows [Task 0](superpowers/plans/2026-10-08-first-release-extraction.md#task-0-disable-legacy-edit-and-release-v121-independently) using the existing release route. Qualify and prepare its artifact without waiting for extraction or the installer; publication still requires Alex's explicit go. The current workflow publishes on version-tag pushes, so a tag is a release action.

For v1.2.1 only, Alex authorized publication on 2026-10-08 using the recorded local build and startup smoke check, waiving the clean-machine walkthrough. Before tagging, verify the tag workflow runs build.py with product version 1.2.1.0. After publication, verify Latest, the Simplicitor.exe asset, its executable version, and its SHA-256; record evidence in docs/releases/. This exception does not qualify later extraction installers or establish Windows reputation.

## Standalone build

`python build.py` uses the existing PySide6 plugin and Nuitka **4.2.2**, pinned in requirements-build.txt. It builds once in standalone mode with Nuitka's built-in `--windows-create-installer` NSIS backend. The backend downloads its build tool into the configured Nuitka cache if needed; it never installs Simplicitor or a runtime on the host.

Outputs:

- `dist/standalone/main.dist/`: compiled runtime payload, including Qt/document libraries, prompts, icons, both built-in templates, and `third_party/` license notices.
- `dist/Simplicitor-setup.exe`: unsigned current-user installer, without a UAC requirement.
- `dist/Simplicitor-portable.zip`: the exact same payload under a Simplicitor folder.
- `dist/SHA256SUMS.json`: SHA-256 hashes of the two artifacts and every payload file.

The installer offers Desktop and Start Menu shortcuts and registers the Windows uninstaller. It uses current-user mode and disables the folder chooser, with `%LOCALAPPDATA%\Programs\Simplicitor` as the dedicated runtime directory. Keep Nuitka's built-in uninstaller; no generated-script rewriting or cached-makensis lookup is performed. Its uninstaller removes that runtime directory. Settings remain in `%APPDATA%\Simplicitor`, and templates/documents in their configured locations (normally `Documents\Simplicitor`), outside the program directory. The portable build uses these same user-data locations.

Product version is **2.0.0.0**, unreleased. A main-branch push produces CI artifacts. A version-tag push enters the existing release route, but tagging/releasing/publication are not authorized.

### Bundled notices

Before compilation, [build_third_party_notices.py](../scripts/build_third_party_notices.py) assembles `third_party/` from the installed runtime dependency closure and the upstream Qt notice snapshot in [resources/third_party](../resources/third_party/THIRD_PARTY_NOTICES.txt). Platform-conditional installed dependencies are conservatively included; test/build dependencies are excluded except Nuitka's embedded runtime terms. Original wheel license, licence, copyright, and notice files retain their bytes. Python's runtime license and full LGPL/GPL texts accompany the Qt/PySide terms and third-party attributions, including Qt PDF's PDFium dependencies. The inventory records versions and file hashes; the upstream snapshot records exact source URLs and hashes.

Nuitka includes this directory before creating the installer. The archive step rejects absent, empty, or altered notices, so the ZIP has the same notice payload. The Qt snapshot must match installed PySide6 (currently 6.11.2); a version change requires refreshing the upstream notices before building. This is an explicit build failure, not a silent reuse of outdated terms. No new dependency or change to Simplicitor's LICENSE is involved; Alex's separate license decision remains open.

## Runner-only installer qualification

Alex's PC must not run installers, uninstallers, Windows Sandbox, or install/uninstall/delete tests. Local checks may cover source evaluation, synthetic limits, notice assembly/read-only validation, ZIP creation, required build flags/version, and PowerShell syntax parsing. Do not execute the qualification script or the build's artifact-deletion tests locally, including through mocks or a dry-run harness.

The build workflow runs the source suite on a hosted Windows runner, builds the payload/setup/ZIP, then invokes [qualify_windows_installer.ps1](../scripts/qualify_windows_installer.ps1). The script checks GitHub Actions, Windows, and github-hosted environment markers before any installation action, and refuses pre-existing installation/profile test state.

The runner performs these checks in sequence; a failed check fails the workflow:

1. Verify setup/ZIP hashes against the build manifest. Confirm the Ollama endpoint is unavailable.
2. Install silently, verify the dedicated current-user folder, installed version/hash, both shortcut targets, and HKCU uninstall registration.
3. Launch the installed executable from outside the checkout with QT_QPA_PLATFORM=offscreen. Confirm it remains running for 20 seconds without Ollama, then stop only that test process.
4. Create a synthetic settings.json in app data, silently install again over the same installation, and verify the app and settings bytes survive unchanged.
5. Silently uninstall only the fixed, verified test installation. Verify the runtime directory, shortcuts, and uninstall registration disappear while the synthetic settings file retains its hash.

The passing script writes `dist/installer-qualification.json` with its commit/run URL, runner image/OS, check results, and setup/ZIP hashes. Upload this beside the installer, ZIP, and SHA256SUMS.json only after qualification passes. The [first passing run](builds/2026-10-08-task5-ci.json) records verified workflow/artifact state and downloaded hashes. The earlier [local evidence](builds/2026-10-08-task5.json) is historical and predates version 2.0.0.0 and removal of the correction.

This headless hosted-runner lifecycle check does not establish a native extraction/Save As walkthrough, a machine without developer Python/Office, the Task 6 model-accuracy gate, or downloaded-file SmartScreen reputation. Those limits remain explicit; do not infer a release qualification or weaken Windows protection.

## Windows trust investigation

Distinguish publisher reputation warnings from a malware detection and policy blocks. Packaging mode does not prove that any one of these is fixed. Record the actual result on each tested Windows configuration; do not ask users to weaken protection.

Microsoft documents that EV signing no longer automatically bypasses SmartScreen. Self-signing does not establish public publisher trust. Any change to the current signing/distribution policy needs Alex's decision rather than being inserted into build work.

## References

- [Nuitka installer support](https://nuitka.net/user-documentation/user-manual.html#installer).
- [NSIS license](https://nsis.sourceforge.io/License).
- [Microsoft SmartScreen guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).

These are build/trust references. Simplicitor's licensing decision remains owned by [PRD.md](../PRD.md#license-decision).
