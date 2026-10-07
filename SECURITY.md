# Security

## Reporting a vulnerability

To report a security issue, email **alex@thursdaysoftware.com** with a description and reproduction steps. Maintenance is best-effort; there is no formal response SLA. Do not include confidential client documents or secrets in public issues.

## Distribution and Windows trust

Current releases are unsigned onefile executables. Windows may show a reputation warning or block launch, and antivirus detections need investigation. The planned free NSIS installer and portable ZIP are not yet implemented and do not establish a trusted publisher signature. Paid certificates and Microsoft Store publication are outside the agreed distribution route. See [packaging](docs/code-signing.md).

## Local processing and known gaps

Application inference calls target localhost Ollama. Verify that the configured model uses local weights rather than a cloud model. The approved workflow requires local document processing, local previews, no cloud fallback, and disclosed retention of temporary files, drafts, and backups.

The logging policy prohibits prompts, file content, model output, and sensitive identifiers. The current source still has content-bearing parser/HTTP error paths, and filenames and paths can contain sensitive details. Metadata-only logging is not a verified universal guarantee. Sanitization and network checks remain acceptance work.

Legacy editing reconstructs files from extracted text, accepts truncated or empty responses in some cases, and uses filename-based upload and backup destinations that can collide. The new selective-editing, preservation, preview, and approval requirements are not implemented yet. Consult [project status](docs/PROJECT_STATUS.md) before using the legacy Edit workflow with important documents.

## Development and release evidence

Use synthetic or suitably sanitized documents in tracked fixtures and logs. Preserve original source files, identify permitted targets, and verify candidate preservation before publication. Report tested model/configuration and actual release security checks; valid workflow output or a passing source suite does not prove confidential handling or Windows trust.

Simplicitor's current PolyForm Noncommercial license remains unchanged. The intended business audience requires a licensing decision before promotion for that use. Local processing alone is not a GDPR compliance claim.
