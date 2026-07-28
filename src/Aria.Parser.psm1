Set-StrictMode -Version 2.0

function Test-AriaTypeName {
    param([string]$Type)
    return (Test-AriaDeclaredTypeName -Type $Type)
}

function ConvertFrom-AriaParameterList {
    param([AllowEmptyString()][string]$Text,[int]$Line)
    $parameters = New-Object System.Collections.Generic.List[object]
    if ([string]::IsNullOrWhiteSpace($Text)) { return $parameters.ToArray() }
    foreach ($part in @($Text -split ',')) {
        $trimmed = $part.Trim()
        if ($trimmed -notmatch '^([A-Za-z_][A-Za-z0-9_.]*)\s*:\s*(Any|Text|Number|Bool|Null|Sequence<(?:Text|Number|Bool|Null)>)$') { throw "Invalid function parameter '$trimmed' on line ${Line}." }
        $parameters.Add([pscustomobject][ordered]@{ name=$matches[1]; type=$matches[2]; line=$Line })
    }
    return $parameters.ToArray()
}

function Get-AriaExecutableGlyphAliases {
    [CmdletBinding()]
    param()

    @(
        [pscustomobject][ordered]@{
            schema = 'aria.executable-glyph-aliases/0.1'
            glyph = '∿'
            keyword = 'flow'
            category = 'declaration'
            authority = 'none'
        }

        [pscustomobject][ordered]@{
            schema = 'aria.executable-glyph-aliases/0.1'
            glyph = '↔'
            keyword = 'connect'
            category = 'connection'
            authority = 'protocol'
        }

        [pscustomobject][ordered]@{
            schema = 'aria.executable-glyph-aliases/0.1'
            glyph = '🜁'
            keyword = 'intent'
            category = 'connection'
            authority = 'operator-intent'
        }

        [pscustomobject][ordered]@{
            schema = 'aria.executable-glyph-aliases/0.1'
            glyph = '🜂'
            keyword = 'propose'
            category = 'connection'
            authority = 'agent-proposal'
        }

        [pscustomobject][ordered]@{
            schema = 'aria.executable-glyph-aliases/0.1'
            glyph = '⛨'
            keyword = 'consent'
            category = 'authority'
            authority = 'explicit-human'
        }

        [pscustomobject][ordered]@{
            schema = 'aria.executable-glyph-aliases/0.1'
            glyph = '◆'
            keyword = 'disconnect'
            category = 'connection'
            authority = 'closure'
        }

        [pscustomobject][ordered]@{
            schema = 'aria.executable-glyph-aliases/0.1'
            glyph = '▷'
            keyword = 'call'
            category = 'expression'
            authority = 'none'
        }

        [pscustomobject][ordered]@{
            schema = 'aria.executable-glyph-aliases/0.1'
            glyph = '↩'
            keyword = 'return'
            category = 'control'
            authority = 'none'
        }

        [pscustomobject][ordered]@{
            schema = 'aria.executable-glyph-aliases/0.1'
            glyph = '≫'
            keyword = 'pipe'
            category = 'composition'
            authority = 'none'
        }
    )
}

function ConvertFrom-AriaExecutableGlyphSurface {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$Text
    )

    if (
        $Text -match
        '^∿\s+([A-Za-z_][A-Za-z0-9_.-]*)\s*\{$'
    ) {
        return ('flow {0} {{' -f $matches[1])
    }

    if (
        $Text -match
        '^↔\s+([A-Za-z_][A-Za-z0-9_.-]*)$'
    ) {
        return ('connect {0}' -f $matches[1])
    }

    if (
        $Text -match
        '^🜁\s+([A-Za-z_][A-Za-z0-9_.-]*)\s*(?:<-|←)\s*(.+)$'
    ) {
        return (
            'intent {0} <- {1}' -f
                $matches[1],
                $matches[2]
        )
    }

    if (
        $Text -match
        '^🜂\s+([A-Za-z_][A-Za-z0-9_.-]*)\s*(?:<-|←)\s*(.+)$'
    ) {
        return (
            'propose {0} <- {1}' -f
                $matches[1],
                $matches[2]
        )
    }

    if (
        $Text -match
        '^⛨\s+([A-Za-z_][A-Za-z0-9_.-]*)\s*(?:<-|←)\s*(.+)$'
    ) {
        return (
            'consent {0} <- {1}' -f
                $matches[1],
                $matches[2]
        )
    }

    if (
        $Text -match
        '^◆\s+([A-Za-z_][A-Za-z0-9_.-]*)$'
    ) {
        return ('disconnect {0}' -f $matches[1])
    }

    if ($Text -match '^↩(?:\s+(.+))?$') {
        if ($matches[1]) {
            return ('return {0}' -f $matches[1])
        }

        return 'return'
    }

    return $Text
}
function Read-AriaStatementSequence {
    param([object[]]$Lines,$State,$Diagnostics)
    $statements = New-Object System.Collections.Generic.List[object]
    while ($State.index -lt $Lines.Count) {
        $line = $Lines[$State.index]
        $text = [string](ConvertFrom-AriaExecutableGlyphSurface -Text ([string]$line.text))
        $number = [int]$line.number
        try {
            if ($text -eq '}') { $State.index++; return [pscustomobject]@{ statements=$statements.ToArray(); terminator='close' } }
            if ($text -eq '} else {') { $State.index++; return [pscustomobject]@{ statements=$statements.ToArray(); terminator='else' } }

            if ($text -match '^if\s+(.+)\s*\{$') {
                $condition = ConvertFrom-AriaExpression -Text $matches[1] -Line $number
                $State.index++
                $thenBlock = Read-AriaStatementSequence -Lines $Lines -State $State -Diagnostics $Diagnostics
                $elseStatements = @()
                if ($thenBlock.terminator -eq 'else') {
                    $elseBlock = Read-AriaStatementSequence -Lines $Lines -State $State -Diagnostics $Diagnostics
                    if ($elseBlock.terminator -ne 'close') { throw 'Malformed else block.' }
                    $elseStatements = @($elseBlock.statements)
                }
                elseif ($thenBlock.terminator -ne 'close') { throw 'Malformed if block.' }
                $statements.Add([pscustomobject][ordered]@{ op='if'; condition=$condition; then=@($thenBlock.statements); else=$elseStatements; line=$number })
                continue
            }
            if ($text -match '^repeat\s+(.+?)(?:\s+as\s+([A-Za-z_][A-Za-z0-9_.]*))?\s*\{$') {
                $countExpression = ConvertFrom-AriaExpression -Text $matches[1] -Line $number
                $iterator = if ($matches[2]) { $matches[2] } else { 'index' }
                $State.index++
                $body = Read-AriaStatementSequence -Lines $Lines -State $State -Diagnostics $Diagnostics
                if ($body.terminator -ne 'close') { throw 'Malformed repeat block.' }
                $statements.Add([pscustomobject][ordered]@{ op='repeat'; count=$countExpression; iterator=$iterator; body=@($body.statements); line=$number })
                continue
            }
            # Alchemical glyph surface: syntax sugar lowered into established ARIA operations.
            if ($text -match '^🜁\s+([A-Za-z_][A-Za-z0-9_.-]*)\.([A-Za-z_][A-Za-z0-9_.-]*)\s*->\s*([A-Za-z_][A-Za-z0-9_.]*)(?:\s*:\s*(Any|Text|Number|Bool|Null|Sequence<(?:Text|Number|Bool|Null)>))?$') { $statements.Add([pscustomobject][ordered]@{ op='recall'; memory=$matches[1]; key=$matches[2]; name=$matches[3]; declaredType=$(if($matches[4]){$matches[4]}else{$null}); surface='🜁'; line=$number }); $State.index++; continue }
            if ($text -match '^🜁\s+([A-Za-z_][A-Za-z0-9_.]*)(?:\s*:\s*(Any|Text|Number|Bool|Null|Sequence<(?:Text|Number|Bool|Null)>))?\s*=\s*(.+)$') { $statements.Add([pscustomobject][ordered]@{ op='let'; name=$matches[1]; declaredType=$(if($matches[2]){$matches[2]}else{$null}); expression=(ConvertFrom-AriaExpression $matches[3] $number); surface='🜁'; line=$number }); $State.index++; continue }
            if ($text -match '^🜂\s+(.+)$') { $statements.Add([pscustomobject][ordered]@{ op='emit'; expression=(ConvertFrom-AriaExpression $matches[1] $number); surface='🜂'; line=$number }); $State.index++; continue }
            if ($text -match '^🜄\s+([A-Za-z_][A-Za-z0-9_.-]*)\.([A-Za-z_][A-Za-z0-9_.-]*)\s*=\s*(.+)$') { $statements.Add([pscustomobject][ordered]@{ op='remember'; memory=$matches[1]; key=$matches[2]; expression=(ConvertFrom-AriaExpression $matches[3] $number); surface='🜄'; line=$number }); $State.index++; continue }            if ($text -match '^emit\s+(.+)$') { $statements.Add([pscustomobject][ordered]@{ op='emit'; expression=(ConvertFrom-AriaExpression $matches[1] $number); line=$number }); $State.index++; continue }
            if ($text -match '^signal\s+(pulse|pass|warn|fail|info)\s+(.+)$') { $statements.Add([pscustomobject][ordered]@{ op='signal'; state=$matches[1]; expression=(ConvertFrom-AriaExpression $matches[2] $number); line=$number }); $State.index++; continue }
            if ($text -match '^let\s+([A-Za-z_][A-Za-z0-9_.]*)(?:\s*:\s*(Any|Text|Number|Bool|Null|Sequence<(?:Text|Number|Bool|Null)>))?\s*=\s*(.+)$') { $statements.Add([pscustomobject][ordered]@{ op='let'; name=$matches[1]; declaredType=$(if($matches[2]){$matches[2]}else{$null}); expression=(ConvertFrom-AriaExpression $matches[3] $number); line=$number }); $State.index++; continue }
            if ($text -match '^set\s+([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(.+)$') { $statements.Add([pscustomobject][ordered]@{ op='set'; name=$matches[1]; expression=(ConvertFrom-AriaExpression $matches[2] $number); line=$number }); $State.index++; continue }
            if ($text -match '^remember\s+([A-Za-z_][A-Za-z0-9_.-]*)\.([A-Za-z_][A-Za-z0-9_.-]*)\s*=\s*(.+)$') { $statements.Add([pscustomobject][ordered]@{ op='remember'; memory=$matches[1]; key=$matches[2]; expression=(ConvertFrom-AriaExpression $matches[3] $number); line=$number }); $State.index++; continue }
            if ($text -match '^recall\s+([A-Za-z_][A-Za-z0-9_.-]*)\.([A-Za-z_][A-Za-z0-9_.-]*)\s*->\s*([A-Za-z_][A-Za-z0-9_.]*)(?:\s*:\s*(Any|Text|Number|Bool|Null|Sequence<(?:Text|Number|Bool|Null)>))?$') { $statements.Add([pscustomobject][ordered]@{ op='recall'; memory=$matches[1]; key=$matches[2]; name=$matches[3]; declaredType=$(if($matches[4]){$matches[4]}else{$null}); line=$number }); $State.index++; continue }
            if ($text -match '^require\s+([A-Za-z_][A-Za-z0-9_.-]*)$') { $statements.Add([pscustomobject][ordered]@{ op='require'; capability=$matches[1]; line=$number }); $State.index++; continue }
            if ($text -match '^assert\s+(.+)$') { $statements.Add([pscustomobject][ordered]@{ op='assert'; expression=(ConvertFrom-AriaExpression $matches[1] $number); line=$number }); $State.index++; continue }
            if ($text -match '^read\s+(.+?)\s*->\s*([A-Za-z_][A-Za-z0-9_.]*)(?:\s*:\s*Text)?$') { $statements.Add([pscustomobject][ordered]@{ op='read'; path=(ConvertFrom-AriaExpression $matches[1] $number); name=$matches[2]; line=$number }); $State.index++; continue }
            if ($text -match '^write\s+(.+?)\s*<-\s*(.+)$') { $statements.Add([pscustomobject][ordered]@{ op='write'; path=(ConvertFrom-AriaExpression $matches[1] $number); expression=(ConvertFrom-AriaExpression $matches[2] $number); line=$number }); $State.index++; continue }
            if ($text -match '^dispatch\s+([A-Za-z_][A-Za-z0-9_.-]*)\s*<-\s*(.+)$') { $statements.Add([pscustomobject][ordered]@{ op='dispatch'; agent=$matches[1]; expression=(ConvertFrom-AriaExpression $matches[2] $number); line=$number }); $State.index++; continue }
            if ($text -match '^connect\s+([A-Za-z_][A-Za-z0-9_.-]*)$') { $statements.Add([pscustomobject][ordered]@{ op='connect'; connection=$matches[1]; line=$number }); $State.index++; continue }
            if ($text -match '^intent\s+([A-Za-z_][A-Za-z0-9_.-]*)\s*<-\s*(.+)$') { $statements.Add([pscustomobject][ordered]@{ op='intent'; connection=$matches[1]; expression=(ConvertFrom-AriaExpression $matches[2] $number); line=$number }); $State.index++; continue }
            if ($text -match '^propose\s+([A-Za-z_][A-Za-z0-9_.-]*)\s*<-\s*(.+)$') { $statements.Add([pscustomobject][ordered]@{ op='propose'; connection=$matches[1]; expression=(ConvertFrom-AriaExpression $matches[2] $number); line=$number }); $State.index++; continue }
            if ($text -match '^consent\s+([A-Za-z_][A-Za-z0-9_.-]*)\s*<-\s*(.+)$') { $statements.Add([pscustomobject][ordered]@{ op='consent'; connection=$matches[1]; expression=(ConvertFrom-AriaExpression $matches[2] $number); line=$number }); $State.index++; continue }
            if ($text -match '^disconnect\s+([A-Za-z_][A-Za-z0-9_.-]*)$') { $statements.Add([pscustomobject][ordered]@{ op='disconnect'; connection=$matches[1]; line=$number }); $State.index++; continue }
            if ($text -match '^return(?:\s+(.+))?$') { $expr = if ($matches[1]) { ConvertFrom-AriaExpression $matches[1] $number } else { $null }; $statements.Add([pscustomobject][ordered]@{ op='return'; expression=$expr; line=$number }); $State.index++; continue }
            if ($text -eq 'halt') { $statements.Add([pscustomobject][ordered]@{ op='halt'; line=$number }); $State.index++; continue }
            throw "Invalid executable statement: $text"
        }
        catch {
            $Diagnostics.Add((New-AriaDiagnostic -Severity error -Code 'ARIA1001' -Message $_.Exception.Message -Line $number))
            $State.index++
        }
    }
    return [pscustomobject]@{ statements=$statements.ToArray(); terminator='eof' }
}

function Parse-AriaSource {
    param([Parameter(Mandatory=$true)][string]$Source,[string]$SourceName='<memory>')
    $diagnostics = New-Object System.Collections.Generic.List[object]
    $model = [ordered]@{ format='aria.ir'; sourceName=$SourceName; specVersion=$null; moduleName=$null; moduleVersion=$null; programName=$null; programVersion=$null; entry=$null; memories=@(); capabilities=@(); agents=@(); connections=@(); graphs=@(); functions=@(); flows=@() }
    [object[]]$lines = @(Get-AriaLexedLines -Source $Source)
    if ($lines.Count -gt 0 -and $lines[0].text -notmatch '^aria\s+') { $diagnostics.Add((New-AriaDiagnostic error 'ARIA1006' 'The first declaration must be the aria language header.' $lines[0].number)) }
    $index = 0
    while ($index -lt $lines.Count) {
        $line=$lines[$index]; $text=[string](ConvertFrom-AriaExecutableGlyphSurface -Text ([string]$line.text)); $number=[int]$line.number
        try {
            if ($text -match '^aria\s+([^\s]+)$') { if($null-ne$model.specVersion){throw 'ARIA header may appear only once.'}; $model.specVersion=$matches[1]; $index++; continue }
            if ($text -match '^module\s+([A-Za-z_][A-Za-z0-9_.-]*)\s+version\s+([^\s]+)$') { if($null-ne$model.moduleName){throw 'Module declaration may appear only once.'}; $model.moduleName=$matches[1]; $model.moduleVersion=$matches[2]; $index++; continue }
            if ($text -match '^program\s+([A-Za-z_][A-Za-z0-9_.-]*)\s+version\s+([^\s]+)$') { if($null-ne$model.programName){throw 'Program declaration may appear only once.'}; $model.programName=$matches[1]; $model.programVersion=$matches[2]; $index++; continue }
            if ($text -match '^entry\s+([A-Za-z_][A-Za-z0-9_.-]*)$') { if($null-ne$model.entry){throw 'Entry declaration may appear only once.'}; $model.entry=$matches[1]; $index++; continue }
            if ($text -match '^function\s+([A-Za-z_][A-Za-z0-9_.]*)\s*\((.*)\)\s*->\s*(Any|Text|Number|Bool|Null|Sequence<(?:Text|Number|Bool|Null)>)\s*\{$') {
                $name=$matches[1]; $parameters=ConvertFrom-AriaParameterList $matches[2] $number; $returnType=$matches[3]; $state=[pscustomobject]@{index=($index+1)}; $body=Read-AriaStatementSequence -Lines $lines -State $state -Diagnostics $diagnostics; $index=$state.index; if($body.terminator-ne'close'){throw "Unterminated function '$name'."}; $model.functions += ,[pscustomobject][ordered]@{name=$name;line=$number;parameters=@($parameters);returnType=$returnType;statements=@($body.statements)}; continue
            }
            if ($text -match '^flow\s+([A-Za-z_][A-Za-z0-9_.-]*)\s*\{$') { $name=$matches[1]; $state=[pscustomobject]@{index=($index+1)}; $body=Read-AriaStatementSequence -Lines $lines -State $state -Diagnostics $diagnostics; $index=$state.index; if($body.terminator-ne'close'){throw "Unterminated flow '$name'."}; $model.flows += ,[pscustomobject][ordered]@{name=$name;line=$number;statements=@($body.statements)}; continue }
            if ($text -match '^(memory|capability|agent|connection|graph)\s+([A-Za-z_][A-Za-z0-9_.-]*)\s*\{$') {
                $kind=$matches[1]; $name=$matches[2]; $index++; $entries=New-Object System.Collections.Generic.List[object]
                while ($index -lt $lines.Count -and $lines[$index].text -ne '}') {
                    $inner=$lines[$index]; $innerText=[string]$inner.text; $innerLine=[int]$inner.number
                    try {
                        switch ($kind) {
                            'memory' { if($innerText-notmatch '^([A-Za-z_][A-Za-z0-9_.-]*)(?:\s*:\s*(Any|Text|Number|Bool|Null|Sequence<(?:Text|Number|Bool|Null)>))?\s*=\s*(.+)$'){throw "Invalid memory entry: $innerText"}; $entries.Add([pscustomobject][ordered]@{key=$matches[1];declaredType=$(if($matches[2]){$matches[2]}else{$null});expression=(ConvertFrom-AriaExpression $matches[3] $innerLine);line=$innerLine}) }
                            'capability' { if($innerText-notmatch '^(effect|scope)\s*=\s*(.+)$'){throw "Invalid capability property: $innerText"}; $expr=ConvertFrom-AriaExpression $matches[2] $innerLine; if($expr.kind-ne'literal'-or-not($expr.value-is[string])){throw 'Capability effect and scope must be strings.'}; $entries.Add([pscustomobject][ordered]@{key=$matches[1];expression=$expr;line=$innerLine}) }
                            'agent' { if($innerText-notmatch '^grant\s+([A-Za-z_][A-Za-z0-9_.-]*)$'){throw "Invalid agent statement: $innerText"}; $entries.Add([pscustomobject][ordered]@{capability=$matches[1];line=$innerLine}) }
                            'connection' { if($innerText-notmatch '^(operator|agent|protocol)\s*=\s*(.+)$'){throw "Invalid connection property: $innerText"}; $expr=ConvertFrom-AriaExpression $matches[2] $innerLine; if($expr.kind-ne'literal'-or-not($expr.value-is[string])){throw 'Connection operator, agent, and protocol must be Text literals.'}; $entries.Add([pscustomobject][ordered]@{key=$matches[1];value=[string]$expr.value;line=$innerLine}) }
                            'graph' { if($innerText-match '^node\s+(\S+)\s+(operator|agent|repository|service|surface|memory|artifact|policy|stream|system)\s+([A-Za-z_][A-Za-z0-9_.-]*)$'){ $entries.Add([pscustomobject][ordered]@{statement='node';glyph=$matches[1];nodeKind=$matches[2];name=$matches[3];line=$innerLine}) } elseif($innerText-match '^link\s+([A-Za-z_][A-Za-z0-9_.-]*)\s*->\s*([A-Za-z_][A-Za-z0-9_.-]*)\s+as\s+([A-Za-z_][A-Za-z0-9_.-]*)$'){ $entries.Add([pscustomobject][ordered]@{statement='link';source=$matches[1];target=$matches[2];relation=$matches[3];line=$innerLine}) } else { throw "Invalid graph statement: $innerText" } }
                        }
                    } catch { $diagnostics.Add((New-AriaDiagnostic error 'ARIA1001' $_.Exception.Message $innerLine)) }
                    $index++
                }
                if($index-ge$lines.Count){throw "Unterminated $kind block '$name'."}; $index++
                switch($kind){
                    'memory'{$model.memories += ,[pscustomobject][ordered]@{name=$name;line=$number;values=@($entries.ToArray())}}
                    'capability'{$effect=@($entries|Where-Object{$_.key-eq'effect'});$scope=@($entries|Where-Object{$_.key-eq'scope'});$model.capabilities += ,[pscustomobject][ordered]@{name=$name;line=$number;effect=$(if($effect.Count-eq1){$effect[0].expression.value}else{$null});scope=$(if($scope.Count-eq1){$scope[0].expression.value}else{$null})}}
                    'agent'{$model.agents += ,[pscustomobject][ordered]@{name=$name;line=$number;grants=@($entries.ToArray())}}
                    'connection'{$operator=@($entries|Where-Object{$_.key-eq'operator'});$agent=@($entries|Where-Object{$_.key-eq'agent'});$protocol=@($entries|Where-Object{$_.key-eq'protocol'});$model.connections += ,[pscustomobject][ordered]@{name=$name;line=$number;operator=$(if($operator.Count-eq1){$operator[0].value}else{$null});agent=$(if($agent.Count-eq1){$agent[0].value}else{$null});protocol=$(if($protocol.Count-eq1){$protocol[0].value}else{$null})}}
                    'graph'{$model.graphs += ,[pscustomobject][ordered]@{name=$name;line=$number;nodes=@($entries|Where-Object{$_.statement-eq'node'});links=@($entries|Where-Object{$_.statement-eq'link'})}}
                }
                continue
            }
            if ($text -eq '}' -or $text -eq '} else {') { throw 'Unexpected closing block.' }
            throw "Unknown top-level declaration: $text"
        } catch { $diagnostics.Add((New-AriaDiagnostic error 'ARIA1001' $_.Exception.Message $number)); $index++ }
    }
    if($null-eq$model.specVersion){$diagnostics.Add((New-AriaDiagnostic error 'ARIA1003' 'Missing aria language header.' 0))}
    if($null-eq$model.programName){$diagnostics.Add((New-AriaDiagnostic error 'ARIA1004' 'Missing program declaration.' 0))}
    if($null-eq$model.entry){$diagnostics.Add((New-AriaDiagnostic error 'ARIA1005' 'Missing entry declaration.' 0))}
    return [pscustomobject][ordered]@{model=[pscustomobject]$model;diagnostics=$diagnostics.ToArray()}
}

Export-ModuleMember -Function Get-AriaExecutableGlyphAliases, Parse-AriaSource
