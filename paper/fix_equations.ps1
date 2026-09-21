# Convert 'EQ:' linear-math paragraphs into real Word equations (OMath + BuildUp)
# Usage: powershell -File fix_equations.ps1 -Files doc1.docx, doc2.docx
param([Parameter(Mandatory = $true)][string[]]$Files)

$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

try {
    foreach ($f in $Files) {
        $full = (Resolve-Path -LiteralPath $f).Path
        $doc = $word.Documents.Open($full)
        $count = 0
        $failed = @()

        for ($i = 1; $i -le $doc.Paragraphs.Count; $i++) {
            $p = $doc.Paragraphs.Item($i)
            $t = $p.Range.Text
            if (-not $t.StartsWith('EQ:')) { continue }
            try {
                $start = $p.Range.Start
                $len = $t.Length - 1              # exclude paragraph mark
                $math = $t.Substring(3).Trim()    # drop 'EQ:' prefix

                $r = $doc.Range($start, $start + $len)
                $r.Text = $math

                $eqRange = $doc.Range($start, $start + $math.Length)
                $eqRange.OMaths.Add($eqRange) | Out-Null

                $p2 = $doc.Paragraphs.Item($i)
                if ($p2.Range.OMaths.Count -gt 0) {
                    $p2.Range.OMaths.Item(1).BuildUp() | Out-Null
                }
                $count++
            }
            catch {
                $failed += ("para {0}: {1}" -f $i, $_.Exception.Message)
            }
        }

        $doc.Save()
        $doc.Close()
        Write-Output ("[OK] {0} -> {1} equation(s) converted" -f (Split-Path $full -Leaf), $count)
        foreach ($fl in $failed) { Write-Output ("  [FAIL] {0}" -f $fl) }
    }
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
