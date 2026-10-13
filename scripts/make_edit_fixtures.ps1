param([string]$OutDir = (Join-Path $PSScriptRoot "..\tests\editing\fixtures"))
# Builds the Word-saved editing fixtures (fictional text) through Word COM. Run once on a PC
# with Word, commit the two files; CI never runs this script. It starts its own Word instance
# (separate from any open Word window) and always quits it.
$ErrorActionPreference = "Stop"
$OutDir = (New-Item -ItemType Directory -Force $OutDir).FullName
$word = New-Object -ComObject Word.Application
$word.Visible = $false
function Find-Paragraph($doc, [string]$start) {
  foreach ($p in $doc.Paragraphs) { if ($p.Range.Text.StartsWith($start)) { return $p } }
  throw "paragraph not found: $start"
}
try {
  # word-basic.docx: formatting, bookmarked heading, tab, line break, list, table, link, field.
  $doc = $word.Documents.Add()
  $sel = $word.Selection
  $sel.Style = $doc.Styles.Item(-2); $sel.TypeText("Service outline"); $sel.TypeParagraph()
  $sel.Style = $doc.Styles.Item(-1)
  $sel.TypeText("This sample agreement describes a review project between ")
  $sel.Font.Bold = $true; $sel.TypeText("Example Services"); $sel.Font.Bold = $false
  $sel.TypeText(" and ")
  $sel.Font.Italic = $true; $sel.TypeText("Sample Studio"); $sel.Font.Italic = $false
  $sel.TypeText("."); $sel.TypeParagraph()
  $sel.Style = $doc.Styles.Item(-3); $sel.TypeText("1. Scope")
  $doc.Bookmarks.Add("ScopeHeading", $sel.Paragraphs.Item(1).Range) | Out-Null
  $sel.TypeParagraph()
  $sel.Style = $doc.Styles.Item(-1)
  $sel.TypeText("The project includes a document review and a short findings report."); $sel.TypeParagraph()
  $sel.TypeText("Deliver the first draft within two weeks.`tKeep feedback concise.")
  $sel.InsertBreak(11)
  $sel.TypeText("Second line of the same paragraph."); $sel.TypeParagraph()
  $sel.Range.ListFormat.ApplyBulletDefault()
  $sel.TypeText("A short findings report with the main actions."); $sel.TypeParagraph()
  $sel.TypeText("One review meeting after the draft."); $sel.TypeParagraph()
  $sel.Range.ListFormat.RemoveNumbers()
  $table = $doc.Tables.Add($sel.Range, 2, 2)
  $table.Cell(1,1).Range.Text = "Milestone"; $table.Cell(1,2).Range.Text = "Example date"
  $table.Cell(2,1).Range.Text = "First draft"; $table.Cell(2,2).Range.Text = "10 November 2026"
  $sel.EndKey(6) | Out-Null; $sel.TypeParagraph()
  $sel.TypeText("Invoices are payable within ")
  $sel.Font.Bold = $true; $sel.TypeText("30 days"); $sel.Font.Bold = $false
  $sel.TypeText(" of receipt."); $sel.TypeParagraph()
  $sel.TypeText("Related policy: ")
  $doc.Hyperlinks.Add($sel.Range, "https://example.com/policy", "", "", "example policy link") | Out-Null
  $sel.EndKey(6) | Out-Null; $sel.TypeParagraph()
  $sel.TypeText("Reference page "); $sel.Fields.Add($sel.Range, 33) | Out-Null
  $sel.EndKey(6) | Out-Null; $sel.TypeParagraph()
  $sel.TypeText("Use the agreed project scope when preparing the final report.")
  $doc.SaveAs2([string](Join-Path $OutDir "word-basic.docx"), 16); $doc.Close(0)

  # word-ranges.docx: field and comment ranges across paragraphs, bookmark kinds, page break.
  $doc = $word.Documents.Add()
  $sel = $word.Selection
  foreach ($pair in @(@("Service outline", -2), @("First heading", -3), @("Second heading", -3))) {
    $sel.Style = $doc.Styles.Item([int]$pair[1]); $sel.TypeText($pair[0]); $sel.TypeParagraph()
  }
  $sel.Style = $doc.Styles.Item(-1)
  $doc.Fields.Add($sel.Range, 13, '\o "1-3"', $false) | Out-Null
  $sel.EndKey(6) | Out-Null; $sel.TypeParagraph()
  foreach ($text in @("Comment range starts in this paragraph.",
                      "This middle paragraph is inside the comment range.",
                      "Comment range ends in this paragraph.",
                      "Invoices are payable within 30 days of receipt.",
                      "The GoBack bookmark sits inside this sentence.",
                      "This paragraph starts on a new page.",
                      "Use the agreed project scope when preparing the final report.")) {
    $sel.TypeText($text); $sel.TypeParagraph()
  }
  $a = (Find-Paragraph $doc "Comment range starts").Range.Start
  $b = (Find-Paragraph $doc "Comment range ends").Range.End - 1
  $doc.Comments.Add($doc.Range($a, $b), "Fictional review comment") | Out-Null
  $s = (Find-Paragraph $doc "Invoices are payable").Range.Start + "Invoices are payable within ".Length
  $doc.Bookmarks.Add("PaymentTerm", $doc.Range($s, $s + 7)) | Out-Null
  $g = (Find-Paragraph $doc "The GoBack bookmark").Range.Start + 4
  $doc.Bookmarks.Add("_GoBack", $doc.Range($g, $g)) | Out-Null
  $doc.Bookmarks.Add("SecondHeading", (Find-Paragraph $doc "Second heading").Range) | Out-Null
  (Find-Paragraph $doc "This paragraph starts on a new page").PageBreakBefore = $true
  $doc.SaveAs2([string](Join-Path $OutDir "word-ranges.docx"), 16); $doc.Close(0)
} finally {
  $word.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
