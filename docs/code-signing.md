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

The installer offers Desktop and Start Menu shortcuts and registers the Windows uninstaller. Its normal directory is `%LOCALAPPDATA%\Programs\Simplicitor`; the directory-selection page is disabled to keep it dedicated to runtime files. Nuitka remembers an existing install directory for upgrades. Hiding the chooser does not force a dedicated directory: registry state and NSIS's [/D override](https://nsis.sourceforge.io/Docs/Chapter3.html#installerusage) can still select another path. Close the app before installing/upgrading. The earlier onefile download has no installer registration: installing this payload leaves that manually downloaded executable alone.

Settings remain in `%APPDATA%\Simplicitor`, templates/documents in their configured locations (normally `Documents\Simplicitor`). The portable build uses these same user-data locations; portable means the runtime can be moved, not that all user data stays beside it. The stock Nuitka uninstaller recursively deletes its runtime directory. Under Alex's approved fallback, build.py requires that exact removal line in the generated Uninstall section, replaces it with Delete instructions for packaged files and non-recursive RMDir instructions, and recompiles with the same NSIS tool. If the expected text is absent/changed/duplicated or correction compilation fails, the build fails and discards the installer/archive/hash outputs. Other files are retained, including files in subdirectories; non-empty directories remain. Packaged runtime/resource files themselves are installer-owned and are removed. This source/build contract is tested; actual installation/uninstall behavior remains unverified.

These are unpublished development artifacts. Their executable metadata retains 1.2.1.0 from the existing build pending the next release-version decision; they do not replace the published v1.2.1 asset. A main-branch push uploads CI artifacts only. Only a version-tag push enters the existing release step, and no tag/publication is authorized for Task 5.

## Qualification procedure

Source tests and an archive hash comparison do not prove installation or clean-machine behavior. Record each check separately in the [local packaging evidence](builds/2026-10-08-task5.json).

1. Build with `python build.py`. Inspect the generated NSIS script for per-user scope, install/uninstall paths, shortcut targets, and payload source. Compare every ZIP member with the standalone payload and SHA256SUMS.json.
2. Launch the ZIP payload with a working directory outside the checkout, using a fresh profile whose USERPROFILE/APPDATA/LOCALAPPDATA point into test scratch. Check prompts, icon, template discovery, source readers, extraction/review/Save As, and normal close. Preserve source hashes. A developer-PC run is local evidence only.
3. On clean Windows without Python or Office, use the PRD prerequisites and default security protection. Check missing runtime/model messages, the non-blocking warning, the extraction scenario, cancellation/failure, Save As overwrite/source refusal, and cleanup. Record Windows/security-product versions and the exact warning or detection, affected file, and artifact hash. Do not weaken protection.
4. With approval for the specific test account/machine, install using the current-user setup. Check Desktop/Start Menu shortcut targets and Apps uninstall registration; launch through a shortcut.
5. Before upgrading, hash synthetic settings, a custom template, and saved documents outside the runtime directory. Install a subsequent test build over the first without changing data locations. Verify runtime replacement, shortcut/registration state, all user-data hashes, template discovery, and normal launch. Test a prior onefile user's existing settings/template locations too.
6. Run the registered uninstaller only on that approved test installation. Verify runtime files, shortcuts, and uninstall registration are removed, while all external settings/templates/documents retain their hashes. Reinstall and verify those settings/templates are reused.

Alex has no clean Windows environment and requires explicit approval before installer execution, registry/shortcut changes, or uninstall on his PC. These checks must stay pending until an approved test environment is available. The build itself must never execute the setup/uninstaller. No clean-machine waiver has been granted for extraction packaging.

## Windows trust investigation

Distinguish publisher reputation warnings from a malware detection and policy blocks. Packaging mode does not prove that any one of these is fixed. Record the actual result on each tested Windows configuration; do not ask users to weaken protection.

Microsoft documents that EV signing no longer automatically bypasses SmartScreen. Self-signing does not establish public publisher trust. Any change to the current signing/distribution policy needs Alex's decision rather than being inserted into build work.

## References

- [Nuitka installer support](https://nuitka.net/user-documentation/user-manual.html#installer).
- [NSIS license](https://nsis.sourceforge.io/License).
- [Microsoft SmartScreen guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).

These are build/trust references. Simplicitor's licensing decision remains owned by [PRD.md](../PRD.md#license-decision).
