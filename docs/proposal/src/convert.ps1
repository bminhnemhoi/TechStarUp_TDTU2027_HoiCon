param(
  [string]$InDocx,
  [string]$OutDocx,
  [string]$OutPdf
)
$ErrorActionPreference = "Stop"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open($InDocx, $false, $false)
  # Cap nhat muc luc va moi truong (so trang)
  foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
  $null = $doc.Fields.Update()
  foreach ($toc in $doc.TablesOfContents) { $toc.UpdatePageNumbers() }
  # Luu ban Word (wdFormatDocumentDefault = 16)
  $doc.SaveAs2($OutDocx, 16)
  # Xuat PDF: dinh dang 17, toi uu in an, tao bookmark theo heading
  $doc.ExportAsFixedFormat($OutPdf, 17, $false, 0, 0, 1, 1, 0, $true, $true, 1, $true, $true, $false)
  $pages = $doc.ComputeStatistics(2)
  Write-Output "PAGES=$pages"
  $doc.Close($false)
}
finally {
  $word.Quit()
  [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
}
