# Packaging and distribution

Updated 2026-10-07. This file retains its existing path for links, but replaces the former paid EV certificate runbook.

## Approved distribution route

Simplicitor will use a free direct-download installer, with a portable ZIP as a secondary option. Microsoft Store publication, paid certificates, and paid signing services are outside the agreed scope. This packaging is not implemented yet: `build.py` and the GitHub workflow currently produce an unsigned onefile `Simplicitor.exe`.

| Artifact | Purpose | Planned contents |
|---|---|---|
| Windows setup executable | Main download for nontechnical users. | NSIS installer for the standalone application, shortcuts, version information, and uninstaller. |
| Portable ZIP | Secondary download and diagnostic fallback. | The same standalone application folder, extracted before launch. |

The final artifact names will be fixed during implementation. The current executable remains distinct from the proposed installer.

## Build approach

Keep Nuitka and its PySide6 plugin. Build in standalone mode so the installed application uses its bundled files instead of extracting a onefile payload at each launch. Bundle prompts, the default PowerPoint template, built-in templates, icons, and all required runtime dependencies. Users must not need Python or build tools.

Nuitka's current documentation describes NSIS installer generation with `--windows-create-installer` starting in version 4.2. Evaluate this support with Simplicitor before writing a separate NSIS packaging script. The existing `nuitka>=2.0` dependency does not guarantee this feature; select and verify a suitable build version during implementation. No dependency or build-script changes are made by this document.

Install for the current user without requesting administrator privileges where the tested installation supports it. Provide Start menu access and an uninstaller. Keep application files separate from user settings and documents. Upgrades and uninstall must preserve user data unless the user explicitly chooses its removal.

NSIS has no purchase requirement for this use. No signing certificate, Store account, or subscription is required to create the unsigned installer. Distribution still requires testing; a successful compile is not a release acceptance check.

## Windows trust and antivirus behavior

Packaging convenience and publisher trust are separate concerns. An unsigned NSIS installer, its application executable, and the portable ZIP's executable can still trigger SmartScreen, Smart App Control, or antivirus blocks. A ZIP does not bypass Windows trust checks. Changing build mode is not proof that a detection is resolved.

The user reports that Windows or antivirus blocks the current executable. The specific warning or detection name is still needed to distinguish reputation checks from a malware detection. Record the artifact version, exact message, affected file, and security product during investigation. Do not disable antivirus or weaken Windows protection as a distribution strategy.

EV signing no longer guarantees an immediate SmartScreen bypass. The previous instruction to buy an EV certificate and the claim that signing eliminates warnings are superseded. Self-signed certificates do not establish public trust on ordinary user machines. Any future signing sponsorship would require a separate eligibility review and approval; it is not a prerequisite of this route.

## Release verification

Before distribution, record evidence for:

1. Clean installation and application launch on the supported Windows versions with default security settings and no development Python installation.
2. Local Ollama connection with a usable model, and clear behavior when the service or model is unavailable.
3. Presence and loading of prompts, icons, default templates, built-in templates, and document-library resources outside the repository checkout.
4. Installer and portable ZIP behavior using the same standalone payload.
5. Upgrade and uninstall, including preservation of documents, settings, templates, and backups.
6. Relevant application regression checks and file-integrity hashes for the published artifacts.
7. Actual SmartScreen or antivirus results, including unresolved warnings or detections.

Publish artifacts through GitHub Releases and link them from `simplicitor.com`. Describe remaining warnings honestly. File hashes identify an artifact; they do not supply a trusted publisher signature. Commit, push, tagging, and publishing remain separately authorized actions.

## Official references

Checked 2026-10-07:

- [Nuitka installer support](https://nuitka.net/user-documentation/user-manual.html#installer) describes standalone builds and NSIS installer generation.
- [NSIS license](https://nsis.sourceforge.io/License) permits use without a purchase requirement, including commercial applications.
- [Microsoft SmartScreen guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation) explains reputation checks, unsigned-file warnings, and the removal of automatic EV trust.

The packaging tools do not change Simplicitor's own license. Business-use licensing remains an open product decision in `PRD.md`.
