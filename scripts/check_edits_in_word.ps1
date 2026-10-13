param([Parameter(Mandatory = $true)][string]$Folder)
# One-off Word check (Task C2): requires exactly the six samples from build_edit_samples.py,
# opens each read-only with repair off and prints paragraph and bookmark counts. Writes
# nothing. Exits 1 if the set differs or any file fails to open. It starts its own Word
# instance (separate from any open Word window) and always quits it.
$ErrorActionPreference = "Stop"
$expected = @("bold-value.docx", "goback-rewrite.docx", "headings-split.docx",
              "list-item-added.docx", "page-break-split.docx", "range-split.docx")
$found = @(Get-ChildItem -Path $Folder -Filter *.docx | Sort-Object Name | ForEach-Object { $_.Name })
if (($found -join "|") -ne ($expected -join "|")) {
  "Expected exactly: $($expected -join ', '). Found: $($found -join ', ')"
  exit 1
}
$failed = $false
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
  "Word $($word.Version) build $($word.Build)"
  foreach ($name in $expected) {
    $path = [string](Join-Path $Folder $name)
    try {
      $doc = $word.Documents.Open($path, $false, $true, $false, "", "", $false, "", "", 0, 0, $false, $false)
      $doc.Bookmarks.ShowHidden = $true
      "${name}: opened, paragraphs $($doc.Paragraphs.Count), bookmarks $($doc.Bookmarks.Count)"
      $doc.Close(0)
    } catch {
      "${name}: FAILED to open ($($_.Exception.HResult))"
      $failed = $true
    }
  }
} finally {
  $word.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
if ($failed) { exit 1 }
exit 0
