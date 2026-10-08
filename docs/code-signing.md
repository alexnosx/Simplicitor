# Packaging procedure

Release artifacts, prerequisites, privacy boundaries, signing policy, and data-preservation requirements are owned by [PRD.md](../PRD.md#packaging). Current build state and the unresolved Windows block are in [project status](PROJECT_STATUS.md). The [first-release plan](superpowers/plans/2026-10-08-first-release-extraction.md#task-5-prepare-installer-in-parallel-and-qualify-after-integration) schedules this work.

The independent safety patch follows [Task 0](superpowers/plans/2026-10-08-first-release-extraction.md#task-0-disable-legacy-edit-and-release-v121-independently) using the existing release route. Qualify and prepare its artifact without waiting for extraction or the installer; publication still requires Alex's explicit go. The current workflow publishes on version-tag pushes, so a tag is a release action.

For v1.2.1 only, Alex authorized publication on 2026-10-08 using the recorded local build and startup smoke check, waiving the clean-machine walkthrough. Before tagging, verify the tag workflow runs build.py with product version 1.2.1.0. After publication, verify Latest, the Simplicitor.exe asset, its executable version, and its SHA-256; record evidence in docs/releases/. This exception does not qualify later extraction installers or establish Windows reputation.

## Standalone build

Retain build.py, the PySide6 plugin, and existing resource discovery. Change the build mode during implementation and bundle prompts, icons, current template resources, and the extraction modules/libraries. Run the resulting application outside the checkout to expose accidental source-directory dependencies.

Nuitka documents built-in NSIS installer generation from version 4.2 with --windows-create-installer. Evaluate that route with a pinned tested build version before adding a separate NSIS script; the current nuitka>=2.0 declaration does not select it. Check actual options against that version during implementation.

Produce installer and portable archives from the same successful payload. Keep runtime files separate from settings and user data. Test shortcuts and uninstaller behavior, including upgrades from the previous layout.

## Qualification procedure

1. Build and launch from a directory outside the checkout, using fresh application settings.
2. Test on clean Windows with the prerequisites stated in PRD.md and without a developer Python environment.
3. Run existing generation/template smoke checks and the new extraction/review/save scenario using synthetic files.
4. Check missing-runtime/model messages, cancellation/failure, normal Save As overwrite confirmation, and source-path refusal.
5. Install, upgrade, and uninstall while checking user settings, templates, and documents survive.
6. Compare payload/resource inventories and record artifact SHA-256 hashes.
7. Record the exact Windows/antivirus warning or detection, artifact version, affected file, and security product with default protection enabled.

A compiled executable alone is not this qualification evidence. Do not tag or publish artifacts during build preparation. Publishing remains an explicitly authorized action after release gates.

## Windows trust investigation

Distinguish publisher reputation warnings from a malware detection and policy blocks. Packaging mode does not prove that any one of these is fixed. Record the actual result on each tested Windows configuration; do not ask users to weaken protection.

Microsoft documents that EV signing no longer automatically bypasses SmartScreen. Self-signing does not establish public publisher trust. Any change to the current signing/distribution policy needs Alex's decision rather than being inserted into build work.

## References

- [Nuitka installer support](https://nuitka.net/user-documentation/user-manual.html#installer).
- [NSIS license](https://nsis.sourceforge.io/License).
- [Microsoft SmartScreen guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).

These are build/trust references. Simplicitor's licensing decision remains owned by [PRD.md](../PRD.md#license-decision).
