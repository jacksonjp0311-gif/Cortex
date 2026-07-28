Set-StrictMode -Version Latest

$typedCorePath=Join-Path $PSScriptRoot 'Aria.TypedCore.psm1'
if(-not(Get-Module Aria.TypedCore)){
    Import-Module $typedCorePath -DisableNameChecking
}

function New-AriaSourceError {
    param(
        [string]$Code,
        [string]$Message,
        [int]$Line=0,
        [int]$Column=0
    )

    [pscustomobject][ordered]@{
        code=$Code
        message=$Message
        line=$Line
        column=$Column
    }
}

function Test-AriaSourceTypeName {
    param([AllowEmptyString()][string]$Name)
    $Name-in@('Int','Text','Bool')
}

function Throw-AriaSourceFailure {
    param(
        [string]$Code,
        [string]$Message,
        $Node=$null
    )

    $exception=New-Object System.Exception($Message)
    [void]$exception.Data.Add('AriaCode',$Code)
    if($null-ne$Node){
        if($Node.PSObject.Properties.Name-contains'line'){
            [void]$exception.Data.Add('AriaLine',[int]$Node.line)
        }
        if($Node.PSObject.Properties.Name-contains'column'){
            [void]$exception.Data.Add('AriaColumn',[int]$Node.column)
        }
    }
    throw $exception
}

function ConvertFrom-AriaSourceException {
    param(
        [Parameter(Mandatory=$true)]$Exception,
        [string]$DefaultCode
    )

    $code=$DefaultCode
    $line=0
    $column=0
    if($Exception.Data.Contains('AriaCode')){$code=[string]$Exception.Data['AriaCode']}
    if($Exception.Data.Contains('AriaLine')){$line=[int]$Exception.Data['AriaLine']}
    if($Exception.Data.Contains('AriaColumn')){$column=[int]$Exception.Data['AriaColumn']}
    New-AriaSourceError $code $Exception.Message $line $column
}

function ConvertTo-AriaSourceTokens {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$Source)

    $tokens=New-Object 'System.Collections.Generic.List[object]'
    $index=0
    $line=1
    $column=1

    function Add-Token([string]$Kind,[object]$Value,[int]$TokenLine,[int]$TokenColumn){
        [void]$tokens.Add([pscustomobject][ordered]@{
            kind=$Kind
            value=$Value
            line=$TokenLine
            column=$TokenColumn
        })
    }

    while($index-lt$Source.Length){
        $char=$Source[$index]

        if($char-eq"`r"){
            $index++
            continue
        }

        if($char-eq"`n"){
            $line++
            $column=1
            $index++
            continue
        }

        if([char]::IsWhiteSpace($char)){
            $column++
            $index++
            continue
        }

        if($char-eq'#'){
            while($index-lt$Source.Length -and $Source[$index]-ne"`n"){
                $index++
                $column++
            }
            continue
        }

        $tokenLine=$line
        $tokenColumn=$column

        if([char]::IsDigit($char)){
            $start=$index
            while($index-lt$Source.Length -and [char]::IsDigit($Source[$index])){
                $index++
                $column++
            }
            $text=$Source.Substring($start,$index-$start)
            Add-Token 'Int' ([int64]::Parse($text,[Globalization.CultureInfo]::InvariantCulture)) $tokenLine $tokenColumn
            continue
        }

        if([char]::IsLetter($char) -or $char-eq'_'){
            $start=$index
            while($index-lt$Source.Length){
                $candidate=$Source[$index]
                if(-not([char]::IsLetterOrDigit($candidate) -or $candidate-eq'_')){break}
                $index++
                $column++
            }
            $text=$Source.Substring($start,$index-$start)
            $kind=switch($text){
                'let' {'Let'}
                'fn' {'Fn'}
                'emit' {'Emit'}
                'if' {'If'}
                'else' {'Else'}
                'true' {'Bool'}
                'false' {'Bool'}
                default {'Identifier'}
            }
            $value=if($kind-eq'Bool'){$text-eq'true'}else{$text}
            Add-Token $kind $value $tokenLine $tokenColumn
            continue
        }

        if($char-eq'"'){
            $index++
            $column++
            $builder=New-Object Text.StringBuilder
            $closed=$false

            while($index-lt$Source.Length){
                $current=$Source[$index]
                if($current-eq'"'){
                    $closed=$true
                    $index++
                    $column++
                    break
                }
                if($current-eq'\'){
                    if($index+1-ge$Source.Length){break}
                    $next=$Source[$index+1]
                    switch($next){
                        'n' {[void]$builder.Append("`n")}
                        'r' {[void]$builder.Append("`r")}
                        't' {[void]$builder.Append("`t")}
                        '"' {[void]$builder.Append('"')}
                        '\' {[void]$builder.Append('\')}
                        default {throw "Unknown string escape \${next} at ${tokenLine}:${tokenColumn}."}
                    }
                    $index+=2
                    $column+=2
                    continue
                }
                if($current-eq"`n"){throw "Unterminated string at ${tokenLine}:${tokenColumn}."}
                [void]$builder.Append($current)
                $index++
                $column++
            }

            if(-not$closed){throw "Unterminated string at ${tokenLine}:${tokenColumn}."}
            Add-Token 'Text' $builder.ToString() $tokenLine $tokenColumn
            continue
        }

        $two=if($index+1-lt$Source.Length){$Source.Substring($index,2)}else{''}
        if($two-in@('==','!=','<=','>=','&&','||','->')){
            Add-Token $two $two $tokenLine $tokenColumn
            $index+=2
            $column+=2
            continue
        }

        if([string]$char-in@('+','-','*','/','<','>','!','=',':',',',';','(',')','{','}')){
            $text=[string]$char
            Add-Token $text $text $tokenLine $tokenColumn
            $index++
            $column++
            continue
        }

        throw "Unexpected character '$char' at ${line}:${column}."
    }

    Add-Token 'EOF' $null $line $column
    @($tokens.ToArray())
}

function New-AriaSourceParser {
    param([Parameter(Mandatory=$true)][object[]]$Tokens)

    [pscustomobject]@{
        tokens=$Tokens
        index=0
    }
}

function Get-AriaSourceCurrentToken {
    param($Parser)
    $Parser.tokens[$Parser.index]
}

function Test-AriaSourceToken {
    param($Parser,[string]$Kind)
    [string](Get-AriaSourceCurrentToken $Parser).kind-eq$Kind
}

function Read-AriaSourceToken {
    param($Parser,[string]$Kind)

    $token=Get-AriaSourceCurrentToken $Parser
    if([string]$token.kind-ne$Kind){
        throw "Expected '$Kind' at $($token.line):$($token.column), found '$($token.kind)'."
    }
    $Parser.index++
    $token
}

function Get-AriaSourcePrecedence {
    param([string]$Operator)
    switch($Operator){
        '||' {1}
        '&&' {2}
        '==' {3}
        '!=' {3}
        '<' {4}
        '<=' {4}
        '>' {4}
        '>=' {4}
        '+' {5}
        '-' {5}
        '*' {6}
        '/' {6}
        default {-1}
    }
}

function Read-AriaSourcePrimary {
    param($Parser)

    $token=Get-AriaSourceCurrentToken $Parser

    if($token.kind-in@('Int','Text','Bool')){
        $Parser.index++
        return [pscustomobject][ordered]@{
            kind='literal'
            value=$token.value
            literalType=switch($token.kind){'Int'{'Int'}'Text'{'Text'}'Bool'{'Bool'}}
            line=[int]$token.line
            column=[int]$token.column
        }
    }

    if($token.kind-eq'Identifier'){
        $Parser.index++
        $name=[string]$token.value
        if(Test-AriaSourceToken $Parser '('){
            $null=Read-AriaSourceToken $Parser '('
            $arguments=New-Object 'System.Collections.Generic.List[object]'
            if(-not(Test-AriaSourceToken $Parser ')')){
                while($true){
                    [void]$arguments.Add((Read-AriaSourceExpression $Parser 0))
                    if(Test-AriaSourceToken $Parser ','){$null=Read-AriaSourceToken $Parser ',';continue}
                    break
                }
            }
            $null=Read-AriaSourceToken $Parser ')'
            return [pscustomobject][ordered]@{
                kind='call'
                name=$name
                arguments=@($arguments.ToArray())
                line=[int]$token.line
                column=[int]$token.column
            }
        }

        return [pscustomobject][ordered]@{
            kind='name'
            name=$name
            line=[int]$token.line
            column=[int]$token.column
        }
    }

    if($token.kind-eq'If'){
        $null=Read-AriaSourceToken $Parser 'If'
        $condition=Read-AriaSourceExpression $Parser 0
        $null=Read-AriaSourceToken $Parser '{'
        $then=Read-AriaSourceExpression $Parser 0
        $null=Read-AriaSourceToken $Parser '}'
        $null=Read-AriaSourceToken $Parser 'Else'
        $null=Read-AriaSourceToken $Parser '{'
        $otherwise=Read-AriaSourceExpression $Parser 0
        $null=Read-AriaSourceToken $Parser '}'
        return [pscustomobject][ordered]@{
            kind='if'
            condition=$condition
            then=$then
            otherwise=$otherwise
            line=[int]$token.line
            column=[int]$token.column
        }
    }

    if($token.kind-eq'('){
        $null=Read-AriaSourceToken $Parser '('
        $expression=Read-AriaSourceExpression $Parser 0
        $null=Read-AriaSourceToken $Parser ')'
        return $expression
    }

    if($token.kind-in@('-','!')){
        $Parser.index++
        return [pscustomobject][ordered]@{
            kind='unary'
            operator=[string]$token.kind
            operand=Read-AriaSourcePrimary $Parser
            line=[int]$token.line
            column=[int]$token.column
        }
    }

    throw "Expected expression at $($token.line):$($token.column)."
}

function Read-AriaSourceExpression {
    param($Parser,[int]$MinimumPrecedence=0)

    $left=Read-AriaSourcePrimary $Parser

    while($true){
        $token=Get-AriaSourceCurrentToken $Parser
        $precedence=Get-AriaSourcePrecedence ([string]$token.kind)
        if($precedence-lt$MinimumPrecedence){break}

        $Parser.index++
        $right=Read-AriaSourceExpression $Parser ($precedence+1)
        $left=[pscustomobject][ordered]@{
            kind='binary'
            operator=[string]$token.kind
            left=$left
            right=$right
            line=[int]$token.line
            column=[int]$token.column
        }
    }

    $left
}

function Read-AriaSourceProgram {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$Source)

    $parser=New-AriaSourceParser (ConvertTo-AriaSourceTokens $Source)
    $declarations=New-Object 'System.Collections.Generic.List[object]'

    while(-not(Test-AriaSourceToken $parser 'EOF')){
        if(Test-AriaSourceToken $parser 'Let'){
            $declarationToken=Read-AriaSourceToken $parser 'Let'
            $name=Read-AriaSourceToken $parser 'Identifier'
            $null=Read-AriaSourceToken $parser ':'
            $type=Read-AriaSourceToken $parser 'Identifier'
            $null=Read-AriaSourceToken $parser '='
            $expression=Read-AriaSourceExpression $parser 0
            $null=Read-AriaSourceToken $parser ';'
            [void]$declarations.Add([pscustomobject][ordered]@{
                kind='let'
                name=[string]$name.value
                type=[string]$type.value
                expression=$expression
                line=[int]$declarationToken.line
                column=[int]$declarationToken.column
            })
            continue
        }

        if(Test-AriaSourceToken $parser 'Fn'){
            $declarationToken=Read-AriaSourceToken $parser 'Fn'
            $name=Read-AriaSourceToken $parser 'Identifier'
            $null=Read-AriaSourceToken $parser '('
            $parameters=New-Object 'System.Collections.Generic.List[object]'
            if(-not(Test-AriaSourceToken $parser ')')){
                while($true){
                    $parameterName=Read-AriaSourceToken $parser 'Identifier'
                    $null=Read-AriaSourceToken $parser ':'
                    $parameterType=Read-AriaSourceToken $parser 'Identifier'
                    [void]$parameters.Add([pscustomobject][ordered]@{
                        name=[string]$parameterName.value
                        type=[string]$parameterType.value
                        line=[int]$parameterName.line
                        column=[int]$parameterName.column
                    })
                    if(Test-AriaSourceToken $parser ','){$null=Read-AriaSourceToken $parser ',';continue}
                    break
                }
            }
            $null=Read-AriaSourceToken $parser ')'
            $null=Read-AriaSourceToken $parser '->'
            $returnType=Read-AriaSourceToken $parser 'Identifier'
            $null=Read-AriaSourceToken $parser '{'
            $body=Read-AriaSourceExpression $parser 0
            $null=Read-AriaSourceToken $parser '}'
            [void]$declarations.Add([pscustomobject][ordered]@{
                kind='fn'
                name=[string]$name.value
                parameters=@($parameters.ToArray())
                returnType=[string]$returnType.value
                body=$body
                line=[int]$declarationToken.line
                column=[int]$declarationToken.column
            })
            continue
        }

        if(Test-AriaSourceToken $parser 'Emit'){
            $declarationToken=Read-AriaSourceToken $parser 'Emit'
            $expression=Read-AriaSourceExpression $parser 0
            $null=Read-AriaSourceToken $parser ';'
            [void]$declarations.Add([pscustomobject][ordered]@{
                kind='emit'
                expression=$expression
                line=[int]$declarationToken.line
                column=[int]$declarationToken.column
            })
            continue
        }

        $token=Get-AriaSourceCurrentToken $parser
        throw "Expected let, fn, or emit at $($token.line):$($token.column)."
    }

    [pscustomobject][ordered]@{
        schema='aria.source-ast/0.7'
        declarations=@($declarations.ToArray())
    }
}

function Get-AriaSourceExpressionType {
    param(
        $Expression,
        [hashtable]$Bindings,
        [hashtable]$Functions
    )

    switch([string]$Expression.kind){
        'literal' {return [string]$Expression.literalType}
        'name' {
            if(-not$Bindings.ContainsKey([string]$Expression.name)){
                Throw-AriaSourceFailure 'E_SOURCE_UNKNOWN_BINDING' "Unknown binding '$($Expression.name)'." $Expression
            }
            return [string]$Bindings[[string]$Expression.name]
        }
        'unary' {
            $operand=Get-AriaSourceExpressionType $Expression.operand $Bindings $Functions
            if($Expression.operator-eq'-' -and $operand-eq'Int'){return 'Int'}
            if($Expression.operator-eq'!' -and $operand-eq'Bool'){return 'Bool'}
            Throw-AriaSourceFailure 'E_SOURCE_OPERATOR' "Invalid unary operator '$($Expression.operator)' for '$operand'." $Expression
        }
        'binary' {
            $left=Get-AriaSourceExpressionType $Expression.left $Bindings $Functions
            $right=Get-AriaSourceExpressionType $Expression.right $Bindings $Functions
            $operator=[string]$Expression.operator

            if($operator-in@('+','-','*','/')){
                if($operator-eq'+' -and $left-eq'Text' -and $right-eq'Text'){return 'Text'}
                if($left-eq'Int' -and $right-eq'Int'){return 'Int'}
            }
            if($operator-in@('<','<=','>','>=') -and $left-eq'Int' -and $right-eq'Int'){return 'Bool'}
            if($operator-in@('==','!=') -and $left-eq$right){return 'Bool'}
            if($operator-in@('&&','||') -and $left-eq'Bool' -and $right-eq'Bool'){return 'Bool'}

            Throw-AriaSourceFailure 'E_SOURCE_OPERATOR' "Invalid binary operation '$left $operator $right'." $Expression
        }
        'if' {
            $condition=Get-AriaSourceExpressionType $Expression.condition $Bindings $Functions
            if($condition-ne'Bool'){Throw-AriaSourceFailure 'E_SOURCE_CONDITION' 'If condition must be Bool.' $Expression.condition}
            $then=Get-AriaSourceExpressionType $Expression.then $Bindings $Functions
            $otherwise=Get-AriaSourceExpressionType $Expression.otherwise $Bindings $Functions
            if($then-ne$otherwise){Throw-AriaSourceFailure 'E_SOURCE_BRANCH_TYPE' "If branches disagree: '$then' and '$otherwise'." $Expression}
            return $then
        }
        'call' {
            $name=[string]$Expression.name
            if(-not$Functions.ContainsKey($name)){Throw-AriaSourceFailure 'E_SOURCE_UNKNOWN_FUNCTION' "Unknown function '$name'." $Expression}
            $signature=$Functions[$name]
            if(@($Expression.arguments).Count-ne@($signature.parameters).Count){
                Throw-AriaSourceFailure 'E_SOURCE_ARGUMENT_COUNT' "Function '$name' expects $(@($signature.parameters).Count) arguments." $Expression
            }
            for($index=0;$index-lt@($Expression.arguments).Count;$index++){
                $actual=Get-AriaSourceExpressionType $Expression.arguments[$index] $Bindings $Functions
                $expected=[string]$signature.parameters[$index].type
                if($actual-ne$expected){
                    Throw-AriaSourceFailure 'E_SOURCE_ARGUMENT_TYPE' "Function '$name' argument $($index+1) expects '$expected', got '$actual'." $Expression.arguments[$index]
                }
            }
            return [string]$signature.returnType
        }
        default {Throw-AriaSourceFailure 'E_SOURCE_EXPRESSION' "Unknown expression kind '$($Expression.kind)'." $Expression}
    }
}

function Get-AriaSourceFunctionCalls {
    param($Expression)

    $calls=New-Object 'System.Collections.Generic.List[object]'
    switch([string]$Expression.kind){
        'call' {
            [void]$calls.Add([pscustomobject][ordered]@{
                name=[string]$Expression.name
                line=[int]$Expression.line
                column=[int]$Expression.column
            })
            foreach($argument in @($Expression.arguments)){
                foreach($call in @(Get-AriaSourceFunctionCalls $argument)){[void]$calls.Add($call)}
            }
        }
        'unary' {
            foreach($call in @(Get-AriaSourceFunctionCalls $Expression.operand)){[void]$calls.Add($call)}
        }
        'binary' {
            foreach($call in @(Get-AriaSourceFunctionCalls $Expression.left)){[void]$calls.Add($call)}
            foreach($call in @(Get-AriaSourceFunctionCalls $Expression.right)){[void]$calls.Add($call)}
        }
        'if' {
            foreach($child in @($Expression.condition,$Expression.then,$Expression.otherwise)){
                foreach($call in @(Get-AriaSourceFunctionCalls $child)){[void]$calls.Add($call)}
            }
        }
    }
    @($calls.ToArray())
}

function Get-AriaSourceRecursionErrors {
    param([hashtable]$Functions)

    $errors=New-Object 'System.Collections.Generic.List[object]'
    $state=@{}
    $stack=New-Object 'System.Collections.Generic.List[string]'
    $reported=@{}
    $visit=$null
    $visit={
        param([string]$Name)

        $state[$Name]=1
        [void]$stack.Add($Name)
        foreach($call in @(Get-AriaSourceFunctionCalls $Functions[$Name].body)){
            $target=[string]$call.name
            if(-not$Functions.ContainsKey($target)){continue}
            $targetState=if($state.ContainsKey($target)){[int]$state[$target]}else{0}
            if($targetState-eq0){
                & $visit $target
            }
            elseif($targetState-eq1){
                $start=$stack.IndexOf($target)
                $cycle=@($stack.GetRange($start,$stack.Count-$start))+@($target)
                $key=(@($cycle[0..($cycle.Count-2)]|Sort-Object)-join'|')
                if(-not$reported.ContainsKey($key)){
                    $reported[$key]=$true
                    [void]$errors.Add((New-AriaSourceError `
                        'E_SOURCE_RECURSION' `
                        ("Recursive function cycle is not allowed: {0}."-f($cycle-join' -> ')) `
                        ([int]$call.line) `
                        ([int]$call.column)))
                }
            }
        }
        $stack.RemoveAt($stack.Count-1)
        $state[$Name]=2
    }

    foreach($name in @($Functions.Keys|Sort-Object)){
        if(-not$state.ContainsKey($name)){& $visit $name}
    }
    @($errors.ToArray())
}

function Test-AriaSourceProgram {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Program)

    $errors=New-Object 'System.Collections.Generic.List[object]'
    $bindings=@{}
    $functions=@{}
    $emitTypes=New-Object 'System.Collections.Generic.List[string]'

    foreach($declaration in @($Program.declarations)){
        if($declaration.kind-eq'fn'){
            if($functions.ContainsKey([string]$declaration.name) -or $bindings.ContainsKey([string]$declaration.name)){
                [void]$errors.Add((New-AriaSourceError 'E_SOURCE_DUPLICATE' "Duplicate name '$($declaration.name)'."))
                continue
            }
            $functions[[string]$declaration.name]=$declaration
            foreach($parameter in @($declaration.parameters)){
                if(-not(Test-AriaSourceTypeName ([string]$parameter.type))){
                    [void]$errors.Add((New-AriaSourceError `
                        'E_SOURCE_TYPE_NAME' `
                        "Unknown source type '$($parameter.type)'." `
                        ([int]$parameter.line) `
                        ([int]$parameter.column)))
                }
            }
            if(-not(Test-AriaSourceTypeName ([string]$declaration.returnType))){
                [void]$errors.Add((New-AriaSourceError `
                    'E_SOURCE_TYPE_NAME' `
                    "Unknown source type '$($declaration.returnType)'." `
                    ([int]$declaration.line) `
                    ([int]$declaration.column)))
            }
        }
    }
    foreach($error in @(Get-AriaSourceRecursionErrors $functions)){[void]$errors.Add($error)}

    foreach($declaration in @($Program.declarations)){
        try{
            switch([string]$declaration.kind){
                'fn' {
                    $local=@{}
                    foreach($parameter in @($declaration.parameters)){
                        if($local.ContainsKey([string]$parameter.name)){
                            throw "Duplicate parameter '$($parameter.name)'."
                        }
                        $local[[string]$parameter.name]=[string]$parameter.type
                    }
                    $actual=Get-AriaSourceExpressionType $declaration.body $local $functions
                    if($actual-ne[string]$declaration.returnType){
                        throw "Function '$($declaration.name)' returns '$actual', declared '$($declaration.returnType)'."
                    }
                }
                'let' {
                    if($bindings.ContainsKey([string]$declaration.name) -or $functions.ContainsKey([string]$declaration.name)){
                        throw "Duplicate name '$($declaration.name)'."
                    }
                    if(-not(Test-AriaSourceTypeName ([string]$declaration.type))){
                        Throw-AriaSourceFailure 'E_SOURCE_TYPE_NAME' "Unknown source type '$($declaration.type)'." $declaration
                    }
                    $actual=Get-AriaSourceExpressionType $declaration.expression $bindings $functions
                    if($actual-ne[string]$declaration.type){
                        throw "Binding '$($declaration.name)' has '$actual', declared '$($declaration.type)'."
                    }
                    $bindings[[string]$declaration.name]=[string]$declaration.type
                }
                'emit' {
                    [void]$emitTypes.Add((Get-AriaSourceExpressionType $declaration.expression $bindings $functions))
                }
            }
        }
        catch{
            [void]$errors.Add((ConvertFrom-AriaSourceException $_.Exception 'E_SOURCE_TYPE'))
        }
    }

    [pscustomobject][ordered]@{
        valid=($errors.Count-eq0)
        errors=@($errors.ToArray())
        emitTypes=@($emitTypes.ToArray())
    }
}

function ConvertTo-AriaCheckedInt64 {
    param(
        [Parameter(Mandatory=$true)][Numerics.BigInteger]$Value,
        $Node
    )

    $minimum=[Numerics.BigInteger]::Parse('-9223372036854775808',[Globalization.CultureInfo]::InvariantCulture)
    $maximum=[Numerics.BigInteger]::Parse('9223372036854775807',[Globalization.CultureInfo]::InvariantCulture)
    if($Value-lt$minimum -or $Value-gt$maximum){
        Throw-AriaSourceFailure 'E_SOURCE_INTEGER_OVERFLOW' 'Int operation exceeds the signed 64-bit range.' $Node
    }
    [int64]$Value
}

function Invoke-AriaSourceExpression {
    param(
        $Expression,
        [hashtable]$Bindings,
        [hashtable]$Functions
    )

    switch([string]$Expression.kind){
        'literal' {return $Expression.value}
        'name' {return $Bindings[[string]$Expression.name]}
        'unary' {
            $value=Invoke-AriaSourceExpression $Expression.operand $Bindings $Functions
            if($Expression.operator-eq'-'){
                return ConvertTo-AriaCheckedInt64 (-[Numerics.BigInteger]([int64]$value)) $Expression
            }
            if($Expression.operator-eq'!'){return -not[bool]$value}
        }
        'binary' {
            $left=Invoke-AriaSourceExpression $Expression.left $Bindings $Functions
            $operator=[string]$Expression.operator

            if($operator-eq'&&'){
                if(-not[bool]$left){return $false}
                return [bool](Invoke-AriaSourceExpression $Expression.right $Bindings $Functions)
            }
            if($operator-eq'||'){
                if([bool]$left){return $true}
                return [bool](Invoke-AriaSourceExpression $Expression.right $Bindings $Functions)
            }

            $right=Invoke-AriaSourceExpression $Expression.right $Bindings $Functions
            switch($operator){
                '+' {
                    if($left-is[string]){return ([string]$left)+([string]$right)}
                    return ConvertTo-AriaCheckedInt64 `
                        ([Numerics.BigInteger]([int64]$left)+[Numerics.BigInteger]([int64]$right)) `
                        $Expression
                }
                '-' {
                    return ConvertTo-AriaCheckedInt64 `
                        ([Numerics.BigInteger]([int64]$left)-[Numerics.BigInteger]([int64]$right)) `
                        $Expression
                }
                '*' {
                    return ConvertTo-AriaCheckedInt64 `
                        ([Numerics.BigInteger]([int64]$left)*[Numerics.BigInteger]([int64]$right)) `
                        $Expression
                }
                '/' {
                    if([int64]$right-eq0){
                        Throw-AriaSourceFailure 'E_SOURCE_DIVISION_ZERO' 'Division by zero.' $Expression
                    }
                    return ConvertTo-AriaCheckedInt64 `
                        ([Numerics.BigInteger]::Divide(
                            [Numerics.BigInteger]([int64]$left),
                            [Numerics.BigInteger]([int64]$right))) `
                        $Expression
                }
                '==' {return $left-eq$right}
                '!=' {return $left-ne$right}
                '<' {return [int64]$left-lt[int64]$right}
                '<=' {return [int64]$left-le[int64]$right}
                '>' {return [int64]$left-gt[int64]$right}
                '>=' {return [int64]$left-ge[int64]$right}
            }
        }
        'if' {
            if([bool](Invoke-AriaSourceExpression $Expression.condition $Bindings $Functions)){
                return Invoke-AriaSourceExpression $Expression.then $Bindings $Functions
            }
            return Invoke-AriaSourceExpression $Expression.otherwise $Bindings $Functions
        }
        'call' {
            $function=$Functions[[string]$Expression.name]
            $local=@{}
            for($index=0;$index-lt@($function.parameters).Count;$index++){
                $local[[string]$function.parameters[$index].name]=
                    Invoke-AriaSourceExpression $Expression.arguments[$index] $Bindings $Functions
            }
            return Invoke-AriaSourceExpression $function.body $local $Functions
        }
    }

    throw "Cannot evaluate expression '$($Expression.kind)'."
}

function ConvertTo-AriaSourceIr {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Program)

    $identity=[ordered]@{
        schema='aria.source-ir/0.7'
        declarations=@($Program.declarations)
        effects=@()
    }
    $digest=Get-AriaSha256Hex (ConvertTo-AriaStableJson $identity)

    [pscustomobject][ordered]@{
        schema=$identity.schema
        declarations=@($identity.declarations)
        effects=@()
        id="sha256:$digest"
    }
}

function Invoke-AriaSourceProgram {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Program)

    $validation=Test-AriaSourceProgram $Program
    if(-not$validation.valid){
        return [pscustomobject][ordered]@{
            valid=$false
            errors=@($validation.errors)
            output=@()
            ir=$null
        }
    }

    $bindings=@{}
    $functions=@{}
    $output=New-Object 'System.Collections.Generic.List[object]'

    foreach($declaration in @($Program.declarations)){
        if($declaration.kind-eq'fn'){
            $functions[[string]$declaration.name]=$declaration
        }
    }

    foreach($declaration in @($Program.declarations)){
        switch([string]$declaration.kind){
            'let' {
                $bindings[[string]$declaration.name]=
                    Invoke-AriaSourceExpression $declaration.expression $bindings $functions
            }
            'emit' {
                [void]$output.Add((Invoke-AriaSourceExpression $declaration.expression $bindings $functions))
            }
        }
    }

    [pscustomobject][ordered]@{
        valid=$true
        errors=@()
        output=@($output.ToArray())
        ir=ConvertTo-AriaSourceIr $Program
    }
}

function Invoke-AriaSourceText {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$Source)

    try{$program=Read-AriaSourceProgram $Source}
    catch{
        [pscustomobject][ordered]@{
            valid=$false
            errors=@(ConvertFrom-AriaSourceException $_.Exception 'E_SOURCE_PARSE')
            output=@()
            ir=$null
        }
        return
    }

    try{Invoke-AriaSourceProgram $program}
    catch{
        [pscustomobject][ordered]@{
            valid=$false
            errors=@(ConvertFrom-AriaSourceException $_.Exception 'E_SOURCE_RUNTIME')
            output=@()
            ir=$null
        }
    }
}

function Invoke-AriaSourceFile {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$Path)

    if(-not(Test-Path $Path -PathType Leaf)){
        return [pscustomobject][ordered]@{
            valid=$false
            errors=@(New-AriaSourceError 'E_SOURCE_FILE' "Source file not found: $Path")
            output=@()
            ir=$null
        }
    }

    Invoke-AriaSourceText ([IO.File]::ReadAllText((Resolve-Path $Path)))
}

Export-ModuleMember -Function `
    ConvertTo-AriaSourceTokens, `
    Read-AriaSourceProgram, `
    Test-AriaSourceProgram, `
    ConvertTo-AriaSourceIr, `
    Invoke-AriaSourceProgram, `
    Invoke-AriaSourceText, `
    Invoke-AriaSourceFile
