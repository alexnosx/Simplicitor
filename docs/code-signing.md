# Packaging procedure

Release artifacts, prerequisites, privacy boundaries, signing policy, and data-preservation requirements are owned by [PRD.md](../PRD.md#packaging). Current build state and the unresolved Windows block are in [project status](PROJECT_STATUS.md). The [first-release plan](superpowers/plans/2026-10-08-first-release-extraction.md#task-5-prepare-installer-in-parallel-and-qualify-after-integration) schedules this work.

The independent safety patch follows [Task 0](superpowers/plans/2026-10-08-first-release-extraction.md#task-0-disable-legacy-edit-and-release-v121-independently) using the existing release route. Qualify and prepare its artifact without waiting for extraction or the installer; publication still requires Alex's explicit go. The current workflow publishes on version-tag pushes, so a tag is a release action.

For v1.2.1 only, Alex authorized publication on 2026-10-08 using the recorded local build and startup smoke check, waiving the clean-machine walkthrough. Before tagging, verify the tag workflow runs build.py with product version 1.2.1.0. After publication, verify Latest, the Simplicitor.exe asset, its executable version, and its SHA-256; record evidence in docs/releases/. This exception does not qualify later extraction installers or establish Windows reputation.

## Standalone build

`python build.py` uses the existing PySide6 plugin and Nuitka **4.2.2**, pinned in requirements-build.txt. It builds once in standalone mode with Nuitka's built-in `--windows-create-installer` NSIS backend. The backend downloads its build tool into the configured Nuitka cache if needed; it never installs Simplicitor or a runtime on the host.

Outputs:

- `dist/standalone/main.dist/`: compiled runtime payload, including Qt/document libraries, prompts, icons, and both built-in templates.
- `dist/Simplicitor-setup.exe`: unsigned current-user installer, without a UAC requirement.
- `dist/Simplicitor-portable.zip`: the exact same payload under a Simplicitor folder.
- `dist/SHA256SUMS.json`: SHA-256 hashes of the two artifacts and every payload file.

The installer offers Desktop and Start Menu shortcuts and registers the Windows uninstaller. It uses current-user mode and disables the folder chooser, with `%LOCALAPPDATA%\Programs\Simplicitor` as the dedicated runtime directory. Keep Nuitka's built-in uninstaller; no generated-script rewriting or cached-makensis lookup is performed. Its uninstaller removes that runtime directory. Settings remain in `%APPDATA%\Simplicitor`, and templates/documents in their configured locations (normally `Documents\Simplicitor`), outside the program directory. The portable build uses these same user-data locations.

Product version is **2.0.0.0**, unreleased. A main-branch push produces CI artifacts. A version-tag push enters the existing release route, but tagging/releasing/publication are not authorized.

## Runner-only installer qualification

Alex's PC must not run installers, uninstallers, Windows Sandbox, or install/uninstall/delete tests. Local checks for this revision are limited to the required build flags/version and PowerShell syntax parsing. Do not execute the qualification script locally, including through mocks or a dry-run harness.

The build workflow runs the source suite on a hosted Windows runner, builds the payload/setup/ZIP, then invokes [qualify_windows_installer.ps1](../scripts/qualify_windows_installer.ps1). The script checks GitHub Actions, Windows, and github-hosted environment markers before any installation action, and refuses pre-existing installation/profile test state.

The runner performs these checks in sequence; a failed check fails the workflow:

1. Verify setup/ZIP hashes against the build manifest. Confirm the Ollama endpoint is unavailable.
2. Install silently, verify the dedicated current-user folder, installed version/hash, both shortcut targets, and HKCU uninstall registration.
3. Launch the installed executable from outside the checkout with QT_QPA_PLATFORM=offscreen. Confirm it remains running for 20 seconds without Ollama, then stop only that test process.
4. Create a synthetic settings.json in app data, silently install again over the same installation, and verify the app and settings bytes survive unchanged.
5. Silently uninstall only the fixed, verified test installation. Verify the runtime directory, shortcuts, and uninstall registration disappear while the synthetic settings file retains its hash.

The passing script writes `dist/installer-qualification.json` with its commit/run URL, runner image/OS, check results, and setup/ZIP hashes. Upload this beside the installer, ZIP, and SHA256SUMS.json only after qualification passes. Record the first passing run in docs/builds/ and verify the workflow/artifact state through GitHub. The earlier [local evidence](builds/2026-10-08-task5.json) is historical and predates version 2.0.0.0 and removal of the correction.

This headless hosted-runner lifecycle check does not establish a native extraction/Save As walkthrough, a machine without developer Python/Office, the Task 6 model-accuracy gate, or downloaded-file SmartScreen reputation. Those limits remain explicit; do not infer a release qualification or weaken Windows protection.

## Windows trust investigation

Distinguish publisher reputation warnings from a malware detection and policy blocks. Packaging mode does not prove that any one of these is fixed. Record the actual result on each tested Windows configuration; do not ask users to weaken protection.

Microsoft documents that EV signing no longer automatically bypasses SmartScreen. Self-signing does not establish public publisher trust. Any change to the current signing/distribution policy needs Alex's decision rather than being inserted into build work.

## References

- [Nuitka installer support](https://nuitka.net/user-documentation/user-manual.html#installer).
- [NSIS license](https://nsis.sourceforge.io/License).
- [Microsoft SmartScreen guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).

These are build/trust references. Simplicitor's licensing decision remains owned by [PRD.md](../PRD.md#license-decision).
