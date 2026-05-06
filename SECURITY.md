# Security

## Reporting a vulnerability

To report a security issue, email **alex@thursdaysoftware.com** with a description of the vulnerability and steps to reproduce it. There is no formal SLA — this is a personal project maintained on a best-effort basis. You will receive a response when the issue has been reviewed.

## Unsigned binary

The distributed `Simplicitor.exe` is currently unsigned. Windows SmartScreen will show a warning on first run — this is expected behavior for v1, not a security problem. EV code signing is planned for a future release.

## Scope

Simplicitor communicates only with a locally running Ollama instance at `localhost:11434`. It makes no outbound network requests. Log files contain operation metadata only — never file content or prompt text.
