Set-StrictMode -Version 2.0

$script:AriaFunctionGlyphTargets = @{
    '⋈' = 'MemoryBalance'
    '≋' = 'ConstitutionalPotential'
    '⌁' = 'ReversibilityBurden'
    '↧' = 'AuthorityAdmissible'
    '↶' = 'RecoveryAdmissible'
}

function Remove-AriaComment {
    param([Parameter(Mandatory=$true)][AllowEmptyString()][string]$Line)
    $inString = $false
    $escaped = $false
    for ($index = 0; $index -lt $Line.Length; $index++) {
        $character = $Line[$index]
        if ($escaped) { $escaped = $false; continue }
        if ([int][char]$character -eq 92 -and $inString) { $escaped = $true; continue }
        if ($character -eq '"') { $inString = -not $inString; continue }
        if ($character -eq '#' -and -not $inString) { return $Line.Substring(0, $index) }
    }
    return $Line
}

function Get-AriaLexedLines {
    param([Parameter(Mandatory=$true)][string]$Source)
    $result = New-Object System.Collections.Generic.List[object]
    $lines = (Normalize-AriaText -Text $Source).Split("`n")
    for ($index = 0; $index -lt $lines.Length; $index++) {
        $clean = (Remove-AriaComment -Line $lines[$index]).Trim()
        if ($clean.Length -gt 0) {
            $result.Add([pscustomobject][ordered]@{ number = $index + 1; text = $clean })
        }
    }
    return $result.ToArray()
}

function ConvertFrom-AriaLiteral {
    param([Parameter(Mandatory=$true)][string]$Text, [int]$Line = 0)
    $trimmed = $Text.Trim()
    if ($trimmed.StartsWith('"') -and $trimmed.EndsWith('"')) {
        try { return [pscustomobject][ordered]@{ kind = 'literal'; value = ($trimmed | ConvertFrom-Json); valueType = 'Text' } }
        catch { throw "Invalid string literal on line ${Line}: $trimmed" }
    }
    if ($trimmed -eq 'true') { return [pscustomobject][ordered]@{ kind = 'literal'; value = $true; valueType = 'Bool' } }
    if ($trimmed -eq 'false') { return [pscustomobject][ordered]@{ kind = 'literal'; value = $false; valueType = 'Bool' } }
    if ($trimmed -eq 'null') { return [pscustomobject][ordered]@{ kind = 'literal'; value = $null; valueType = 'Null' } }
    if ($trimmed -match '^-?[0-9]+$') { return [pscustomobject][ordered]@{ kind = 'literal'; value = [long]$trimmed; valueType = 'Number' } }
    if ($trimmed -match '^-?[0-9]+\.[0-9]+$') { return [pscustomobject][ordered]@{ kind = 'literal'; value = [double]::Parse($trimmed, [System.Globalization.CultureInfo]::InvariantCulture); valueType = 'Number' } }
    if ($trimmed -match '^[A-Za-z_][A-Za-z0-9_.]*$') { return [pscustomobject][ordered]@{ kind = 'identifier'; value = $trimmed } }
    throw "Invalid ARIA expression on line ${Line}: $trimmed"
}

function Get-AriaExpressionTokens {
    param([Parameter(Mandatory=$true)][string]$Text, [int]$Line = 0)
    $tokens = New-Object System.Collections.Generic.List[object]
    $index = 0
    while ($index -lt $Text.Length) {
        $ch = $Text[$index]
        if ([char]::IsWhiteSpace($ch)) { $index++; continue }

        if ($ch -eq '"') {
            $start = $index
            $index++
            $escaped = $false
            $closed = $false
            while ($index -lt $Text.Length) {
                $current = $Text[$index]
                if ($escaped) { $escaped = $false; $index++; continue }
                if ([int][char]$current -eq 92) { $escaped = $true; $index++; continue }
                if ($current -eq '"') { $index++; $closed = $true; break }
                $index++
            }
            if (-not $closed) { throw "Unterminated string expression on line ${Line}." }
            $raw = $Text.Substring($start, $index - $start)
            try { $value = $raw | ConvertFrom-Json }
            catch { throw "Invalid string expression on line ${Line}: $raw" }
            $tokens.Add([pscustomobject][ordered]@{ kind='literal'; text=$raw; value=$value; valueType='Text' })
            continue
        }

        if ($ch -eq '▷') {
            $tokens.Add(
                [pscustomobject][ordered]@{
                    kind = 'invoke'
                    text = '▷'
                }
            )
            $index++
            continue
        }

        if ($ch -eq '≫') {
            $tokens.Add(
                [pscustomobject][ordered]@{
                    kind = 'pipe'
                    text = '≫'
                }
            )
            $index++
            continue
        }

        if ($ch -eq '⨯') {
            $tokens.Add(
                [pscustomobject][ordered]@{
                    kind = 'map'
                    text = '⨯'
                }
            )
            $index++
            continue
        }

        if ($ch -eq '⫰') {
            $tokens.Add(
                [pscustomobject][ordered]@{
                    kind = 'filter'
                    text = '⫰'
                }
            )
            $index++
            continue
        }

        if ($ch -eq 'Σ') {
            $tokens.Add(
                [pscustomobject][ordered]@{
                    kind = 'reduce'
                    text = 'Σ'
                }
            )
            $index++
            continue
        }

        $glyphText = [string]$ch
        if ($script:AriaFunctionGlyphTargets.ContainsKey($glyphText)) {
            $tokens.Add(
                [pscustomobject][ordered]@{
                    kind = 'functionGlyph'
                    text = $glyphText
                    value = $script:AriaFunctionGlyphTargets[$glyphText]
                }
            )
            $index++
            continue
        }

        if ([char]::IsDigit($ch)) {
            $start = $index
            while ($index -lt $Text.Length -and [char]::IsDigit($Text[$index])) { $index++ }
            if ($index -lt $Text.Length -and $Text[$index] -eq '.') {
                $index++
                if ($index -ge $Text.Length -or -not [char]::IsDigit($Text[$index])) { throw "Invalid numeric expression on line ${Line}." }
                while ($index -lt $Text.Length -and [char]::IsDigit($Text[$index])) { $index++ }
            }
            $raw = $Text.Substring($start, $index - $start)
            $value = if ($raw.Contains('.')) { [double]::Parse($raw, [Globalization.CultureInfo]::InvariantCulture) } else { [long]$raw }
            $tokens.Add([pscustomobject][ordered]@{ kind='literal'; text=$raw; value=$value; valueType='Number' })
            continue
        }

        if ([char]::IsLetter($ch) -or $ch -eq '_') {
            $start = $index
            $index++
            while ($index -lt $Text.Length) {
                $candidate = $Text[$index]
                if ([char]::IsLetterOrDigit($candidate) -or $candidate -eq '_' -or $candidate -eq '.') { $index++ } else { break }
            }
            $raw = $Text.Substring($start, $index - $start)
            switch ($raw) {
                'true'  { $tokens.Add([pscustomobject][ordered]@{ kind='literal'; text=$raw; value=$true; valueType='Bool' }) }
                'false' { $tokens.Add([pscustomobject][ordered]@{ kind='literal'; text=$raw; value=$false; valueType='Bool' }) }
                'null'  { $tokens.Add([pscustomobject][ordered]@{ kind='literal'; text=$raw; value=$null; valueType='Null' }) }
                'and'   { $tokens.Add([pscustomobject][ordered]@{ kind='operator'; text='and' }) }
                'or'    { $tokens.Add([pscustomobject][ordered]@{ kind='operator'; text='or' }) }
                'not'   { $tokens.Add([pscustomobject][ordered]@{ kind='operator'; text='not' }) }
                default { $tokens.Add([pscustomobject][ordered]@{ kind='identifier'; text=$raw; value=$raw }) }
            }
            continue
        }

        $two = if ($index + 1 -lt $Text.Length) { $Text.Substring($index, 2) } else { '' }
        if ($two -in @('==','!=','<=','>=')) {
            $tokens.Add([pscustomobject][ordered]@{ kind='operator'; text=$two })
            $index += 2
            continue
        }
        if ($ch -in @('+','-','*','/','<','>')) {
            $tokens.Add([pscustomobject][ordered]@{ kind='operator'; text=[string]$ch })
            $index++
            continue
        }
        if ($ch -eq '(') { $tokens.Add([pscustomobject][ordered]@{ kind='lparen'; text='(' }); $index++; continue }
        if ($ch -eq ')') { $tokens.Add([pscustomobject][ordered]@{ kind='rparen'; text=')' }); $index++; continue }
        if ($ch -eq '[') { $tokens.Add([pscustomobject][ordered]@{ kind='lbracket'; text='[' }); $index++; continue }
        if ($ch -eq ']') { $tokens.Add([pscustomobject][ordered]@{ kind='rbracket'; text=']' }); $index++; continue }
        if ($ch -eq ',') { $tokens.Add([pscustomobject][ordered]@{ kind='comma'; text=',' }); $index++; continue }
        throw "Unexpected expression character '$ch' on line ${Line}."
    }
    $tokens.Add([pscustomobject][ordered]@{ kind='eof'; text='' })
    return $tokens.ToArray()
}

function Get-AriaCurrentExpressionToken { param($State) return $State.tokens[$State.index] }
function Move-AriaExpressionToken { param($State) $State.index = [int]$State.index + 1 }
function Test-AriaExpressionToken { param($State,[string]$Kind,[string]$Text='') $token=Get-AriaCurrentExpressionToken $State; if ($token.kind -ne $Kind) { return $false }; return (-not $Text -or $token.text -eq $Text) }
function Read-AriaExpressionToken { param($State,[string]$Kind,[string]$Text='') if (-not (Test-AriaExpressionToken $State $Kind $Text)) { $token=Get-AriaCurrentExpressionToken $State; throw "Expected $Kind '$Text' on line $($State.line), found '$($token.text)'." }; $token=Get-AriaCurrentExpressionToken $State; Move-AriaExpressionToken $State; return $token }

function Parse-AriaPrimaryExpression {
    param($State)
    $token = Get-AriaCurrentExpressionToken $State
    if ($token.kind -eq 'literal') { Move-AriaExpressionToken $State; return [pscustomobject][ordered]@{ kind='literal'; value=$token.value; valueType=$token.valueType } }
    if ($token.kind -eq 'invoke') {
        Move-AriaExpressionToken $State

        $nameToken = Read-AriaExpressionToken `
            -State $State `
            -Kind 'identifier'

        $name = [string]$nameToken.value

        $null = Read-AriaExpressionToken `
            -State $State `
            -Kind 'lparen'

        $arguments = New-Object System.Collections.Generic.List[object]

        if (-not (Test-AriaExpressionToken $State 'rparen')) {
            while ($true) {
                $arguments.Add((Parse-AriaPipeExpression $State))

                if (Test-AriaExpressionToken $State 'comma') {
                    Move-AriaExpressionToken $State
                    continue
                }

                break
            }
        }

        $null = Read-AriaExpressionToken $State 'rparen'

        return [pscustomobject][ordered]@{
            kind = 'call'
            name = $name
            arguments = $arguments.ToArray()
        }
    }

    if ($token.kind -eq 'functionGlyph') {
        Move-AriaExpressionToken $State
        $null = Read-AriaExpressionToken -State $State -Kind 'lparen'
        $arguments = New-Object System.Collections.Generic.List[object]
        if (-not (Test-AriaExpressionToken $State 'rparen')) {
            while ($true) {
                $arguments.Add((Parse-AriaPipeExpression $State))
                if (Test-AriaExpressionToken $State 'comma') {
                    Move-AriaExpressionToken $State
                    continue
                }
                break
            }
        }
        $null = Read-AriaExpressionToken -State $State -Kind 'rparen'
        return [pscustomobject][ordered]@{
            kind = 'call'
            name = [string]$token.value
            arguments = $arguments.ToArray()
            glyph = [string]$token.text
        }
    }

    if ($token.kind -eq 'map') {
        Move-AriaExpressionToken $State
        $null = Read-AriaExpressionToken -State $State -Kind 'lparen'
        $sequence = Parse-AriaPipeExpression $State
        $null = Read-AriaExpressionToken -State $State -Kind 'comma'
        $transform = Read-AriaExpressionToken -State $State -Kind 'identifier'
        $null = Read-AriaExpressionToken -State $State -Kind 'rparen'
        return [pscustomobject][ordered]@{
            kind = 'map'
            sequence = $sequence
            transform = [string]$transform.value
        }
    }

    if ($token.kind -eq 'filter') {
        Move-AriaExpressionToken $State
        $null = Read-AriaExpressionToken -State $State -Kind 'lparen'
        $sequence = Parse-AriaPipeExpression $State
        $null = Read-AriaExpressionToken -State $State -Kind 'comma'
        $predicate = Read-AriaExpressionToken -State $State -Kind 'identifier'
        $null = Read-AriaExpressionToken -State $State -Kind 'rparen'
        return [pscustomobject][ordered]@{
            kind = 'filter'
            sequence = $sequence
            predicate = [string]$predicate.value
        }
    }

    if ($token.kind -eq 'reduce') {
        Move-AriaExpressionToken $State
        $null = Read-AriaExpressionToken -State $State -Kind 'lparen'
        $sequence = Parse-AriaPipeExpression $State
        $null = Read-AriaExpressionToken -State $State -Kind 'comma'
        $reducer = Read-AriaExpressionToken -State $State -Kind 'identifier'
        $null = Read-AriaExpressionToken -State $State -Kind 'comma'
        $initial = Parse-AriaPipeExpression $State
        $null = Read-AriaExpressionToken -State $State -Kind 'rparen'
        return [pscustomobject][ordered]@{
            kind = 'reduce'
            sequence = $sequence
            reducer = [string]$reducer.value
            initial = $initial
        }
    }

    if (Test-AriaExpressionToken $State 'lbracket') {
        Move-AriaExpressionToken $State
        $elements = New-Object System.Collections.Generic.List[object]

        if (-not (Test-AriaExpressionToken $State 'rbracket')) {
            while ($true) {
                $elements.Add((Parse-AriaPipeExpression $State))

                if (Test-AriaExpressionToken $State 'comma') {
                    Move-AriaExpressionToken $State
                    continue
                }

                break
            }
        }

        $null = Read-AriaExpressionToken $State 'rbracket'

        return [pscustomobject][ordered]@{
            kind = 'sequence'
            elements = $elements.ToArray()
        }
    }

    if ($token.kind -eq 'identifier') {
        Move-AriaExpressionToken $State
        $name = [string]$token.value
        if (Test-AriaExpressionToken $State 'lparen') {
            Move-AriaExpressionToken $State
            $arguments = New-Object System.Collections.Generic.List[object]
            if (-not (Test-AriaExpressionToken $State 'rparen')) {
                while ($true) {
                    $arguments.Add((Parse-AriaPipeExpression $State))
                    if (Test-AriaExpressionToken $State 'comma') { Move-AriaExpressionToken $State; continue }
                    break
                }
            }
            $null = Read-AriaExpressionToken $State 'rparen'
            return [pscustomobject][ordered]@{ kind='call'; name=$name; arguments=$arguments.ToArray() }
        }
        return [pscustomobject][ordered]@{ kind='identifier'; value=$name }
    }
    if (Test-AriaExpressionToken $State 'lparen') {
        Move-AriaExpressionToken $State
        $value = Parse-AriaPipeExpression $State
        $null = Read-AriaExpressionToken $State 'rparen'
        return $value
    }
    throw "Expected expression on line $($State.line), found '$($token.text)'."
}

function Parse-AriaUnaryExpression {
    param($State)
    if (Test-AriaExpressionToken $State 'operator' 'not') { Move-AriaExpressionToken $State; return [pscustomobject][ordered]@{ kind='unary'; operator='not'; operand=(Parse-AriaUnaryExpression $State) } }
    if (Test-AriaExpressionToken $State 'operator' '-') { Move-AriaExpressionToken $State; return [pscustomobject][ordered]@{ kind='unary'; operator='neg'; operand=(Parse-AriaUnaryExpression $State) } }
    return (Parse-AriaPrimaryExpression $State)
}

function Parse-AriaBinaryLevel {
    param($State,[scriptblock]$Next,[string[]]$Operators)
    $left = & $Next $State
    while ((Get-AriaCurrentExpressionToken $State).kind -eq 'operator' -and (Get-AriaCurrentExpressionToken $State).text -in $Operators) {
        $operator = [string](Get-AriaCurrentExpressionToken $State).text
        Move-AriaExpressionToken $State
        $right = & $Next $State
        $left = [pscustomobject][ordered]@{ kind='binary'; operator=$operator; left=$left; right=$right }
    }
    return $left
}

function Parse-AriaMultiplicativeExpression { param($State) return (Parse-AriaBinaryLevel $State ${function:Parse-AriaUnaryExpression} @('*','/')) }
function Parse-AriaAdditiveExpression { param($State) return (Parse-AriaBinaryLevel $State ${function:Parse-AriaMultiplicativeExpression} @('+','-')) }
function Parse-AriaComparisonExpression { param($State) return (Parse-AriaBinaryLevel $State ${function:Parse-AriaAdditiveExpression} @('<','<=','>','>=')) }
function Parse-AriaEqualityExpression { param($State) return (Parse-AriaBinaryLevel $State ${function:Parse-AriaComparisonExpression} @('==','!=')) }
function Parse-AriaAndExpression { param($State) return (Parse-AriaBinaryLevel $State ${function:Parse-AriaEqualityExpression} @('and')) }
function Parse-AriaOrExpression { param($State) return (Parse-AriaBinaryLevel $State ${function:Parse-AriaAndExpression} @('or')) }

function Parse-AriaPipeExpression {
    param($State)

    $value = Parse-AriaOrExpression $State

    while (Test-AriaExpressionToken $State 'pipe' '≫') {
        Move-AriaExpressionToken $State

        $stage = Read-AriaExpressionToken `
            -State $State `
            -Kind 'identifier'

        $value = [pscustomobject][ordered]@{
            kind = 'call'
            name = [string]$stage.value
            arguments = @($value)
        }
    }

    return $value
}

function ConvertFrom-AriaExpression {
    param([Parameter(Mandatory=$true)][string]$Text,[int]$Line=0)
    [object[]]$tokens = @(Get-AriaExpressionTokens -Text $Text -Line $Line)
    $state = [pscustomobject]@{ tokens=$tokens; index=0; line=$Line }
    $expression = Parse-AriaPipeExpression $state
    if (-not (Test-AriaExpressionToken $state 'eof')) { $token=Get-AriaCurrentExpressionToken $state; throw "Unexpected expression token '$($token.text)' on line ${Line}." }
    return $expression
}

Export-ModuleMember -Function Remove-AriaComment, Get-AriaLexedLines, ConvertFrom-AriaLiteral, ConvertFrom-AriaExpression
