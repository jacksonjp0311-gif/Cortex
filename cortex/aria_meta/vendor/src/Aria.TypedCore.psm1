Set-StrictMode -Version Latest

function New-AriaType {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][ValidateSet(
            'Unit','Bool','Int','Float','Text','Bytes','Node','Edge','List','Option','Result','Record','Function'
        )][string]$Kind,
        [object[]]$Arguments = @(),
        [hashtable]$Fields = @{}
    )

    [pscustomobject][ordered]@{
        kind = $Kind
        arguments = @($Arguments)
        fields = $Fields
    }
}

function ConvertTo-AriaCanonicalType {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Type)

    switch ([string]$Type.kind) {
        'List' {
            if (@($Type.arguments).Count -ne 1) { throw 'List requires one type argument.' }
            return "List<$(ConvertTo-AriaCanonicalType $Type.arguments[0])>"
        }
        'Option' {
            if (@($Type.arguments).Count -ne 1) { throw 'Option requires one type argument.' }
            return "Option<$(ConvertTo-AriaCanonicalType $Type.arguments[0])>"
        }
        'Result' {
            if (@($Type.arguments).Count -ne 2) { throw 'Result requires success and error type arguments.' }
            return "Result<$(ConvertTo-AriaCanonicalType $Type.arguments[0]),$(ConvertTo-AriaCanonicalType $Type.arguments[1])>"
        }
        'Record' {
            $pairs = @()
            foreach($name in @($Type.fields.Keys | Sort-Object)){
                $pairs += "${name}:$(ConvertTo-AriaCanonicalType $Type.fields[$name])"
            }
            return "Record{$($pairs -join ',')}"
        }
        'Function' {
            if (@($Type.arguments).Count -lt 1) { throw 'Function requires at least a return type.' }
            $return = ConvertTo-AriaCanonicalType $Type.arguments[-1]
            $parameters = @()
            if (@($Type.arguments).Count -gt 1){
                for($index=0;$index-lt(@($Type.arguments).Count-1);$index++){
                    $parameters += ConvertTo-AriaCanonicalType $Type.arguments[$index]
                }
            }
            return "Fn($($parameters -join ','))->$return"
        }
        default { return [string]$Type.kind }
    }
}

function Test-AriaTypeEqual {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Left,
        [Parameter(Mandatory=$true)]$Right
    )

    (ConvertTo-AriaCanonicalType $Left) -ceq (ConvertTo-AriaCanonicalType $Right)
}

function New-AriaStructuredError {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Code,
        [Parameter(Mandatory=$true)][string]$Message,
        [string]$Path = '$',
        [hashtable]$Evidence = @{}
    )

    [pscustomobject][ordered]@{
        code = $Code
        message = $Message
        path = $Path
        evidence = $Evidence
    }
}

function New-AriaScope {
    [CmdletBinding()]
    param($Parent = $null)

    [pscustomobject][ordered]@{
        parent = $Parent
        bindings = @{}
    }
}

function Add-AriaBinding {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Scope,
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)]$Type,
        [object]$Value,
        [switch]$Mutable
    )

    if ($Scope.bindings.ContainsKey($Name)) {
        return New-AriaStructuredError `
            -Code 'E_BIND_DUPLICATE' `
            -Message "Binding '$Name' already exists in this lexical scope." `
            -Path ("$.scope.{0}" -f $Name)
    }

    $Scope.bindings[$Name] = [pscustomobject][ordered]@{
        name = $Name
        type = $Type
        value = $Value
        mutable = [bool]$Mutable
    }

    return $Scope.bindings[$Name]
}

function Resolve-AriaBinding {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Scope,
        [Parameter(Mandatory=$true)][string]$Name
    )

    $cursor = $Scope
    while($null-ne$cursor){
        if($cursor.bindings.ContainsKey($Name)){return $cursor.bindings[$Name]}
        $cursor = $cursor.parent
    }

    New-AriaStructuredError `
        -Code 'E_BIND_UNKNOWN' `
        -Message "Binding '$Name' is not defined." `
        -Path ("$.scope.{0}" -f $Name)
}

function Set-AriaBindingValue {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Scope,
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)]$Type,
        [object]$Value
    )

    $binding = Resolve-AriaBinding -Scope $Scope -Name $Name
    if($null-ne$binding.PSObject.Properties['code']){return $binding}

    if(-not[bool]$binding.mutable){
        return New-AriaStructuredError `
            -Code 'E_BIND_IMMUTABLE' `
            -Message "Binding '$Name' is immutable." `
            -Path ("$.scope.{0}" -f $Name)
    }

    if(-not(Test-AriaTypeEqual -Left $binding.type -Right $Type)){
        return New-AriaStructuredError `
            -Code 'E_TYPE_ASSIGN' `
            -Message "Binding '$Name' cannot change type." `
            -Path ("$.scope.{0}" -f $Name) `
            -Evidence @{
                expected = ConvertTo-AriaCanonicalType $binding.type
                actual = ConvertTo-AriaCanonicalType $Type
            }
    }

    [void]($binding.value = $Value)
    return $binding
}

function New-AriaFunctionSignature {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [object[]]$Parameters = @(),
        [Parameter(Mandatory=$true)]$ReturnType,
        [string[]]$Effects = @(),
        [string[]]$Capabilities = @()
    )

    [pscustomobject][ordered]@{
        name = $Name
        parameters = @($Parameters)
        returnType = $ReturnType
        effects = @($Effects | Sort-Object -Unique)
        capabilities = @($Capabilities | Sort-Object -Unique)
    }
}

function Test-AriaFunctionCall {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Signature,
        [object[]]$ArgumentTypes = @(),
        [string[]]$GrantedCapabilities = @()
    )

    $errors = New-Object 'System.Collections.Generic.List[object]'

    if(@($Signature.parameters).Count-ne@($ArgumentTypes).Count){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_CALL_ARITY' `
            -Message "Function '$($Signature.name)' received the wrong number of arguments." `
            -Evidence @{ expected=@($Signature.parameters).Count; actual=@($ArgumentTypes).Count }))
    }
    else{
        for($index=0;$index-lt@($ArgumentTypes).Count;$index++){
            $expected=$Signature.parameters[$index].type
            $actual=$ArgumentTypes[$index]
            if(-not(Test-AriaTypeEqual -Left $expected -Right $actual)){
                [void]$errors.Add((New-AriaStructuredError `
                    -Code 'E_CALL_TYPE' `
                    -Message "Argument $index for '$($Signature.name)' has the wrong type." `
                    -Path ("$.arguments[{0}]" -f $index) `
                    -Evidence @{
                        expected=ConvertTo-AriaCanonicalType $expected
                        actual=ConvertTo-AriaCanonicalType $actual
                    }))
            }
        }
    }

    foreach($capability in @($Signature.capabilities)){
        if($capability-notin@($GrantedCapabilities)){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_CAPABILITY_MISSING' `
                -Message "Function '$($Signature.name)' requires capability '$capability'." `
                -Path '$.capabilities' `
                -Evidence @{ required=$capability }))
        }
    }

    [pscustomobject][ordered]@{
        valid = ($errors.Count-eq0)
        errors = @($errors.ToArray())
        returnType = $Signature.returnType
        effects = @($Signature.effects)
    }
}

function Test-AriaExhaustiveBranch {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string[]]$Variants,
        [Parameter(Mandatory=$true)][string[]]$Cases,
        [switch]$HasDefault
    )

    $missing=@($Variants | Where-Object {$_-notin$Cases} | Sort-Object -Unique)
    [pscustomobject][ordered]@{
        exhaustive = ([bool]$HasDefault -or $missing.Count-eq0)
        missing = $missing
    }
}

function Test-AriaEffectAuthority {
    [CmdletBinding()]
    param(
        [string[]]$Effects = @(),
        [string[]]$Capabilities = @()
    )

    $required=[ordered]@{
        'memory.read'='cap:memory.read'
        'memory.write'='cap:memory.write'
        'network.send'='cap:network'
        'filesystem.read'='cap:filesystem.read'
        'filesystem.write'='cap:filesystem.write'
        'provider.invoke'='cap:provider'
    }

    $errors=New-Object 'System.Collections.Generic.List[object]'
    foreach($effect in @($Effects | Sort-Object -Unique)){
        if($required.Contains($effect)){
            $capability=[string]$required[$effect]
            if($capability-notin@($Capabilities)){
                [void]$errors.Add((New-AriaStructuredError `
                    -Code 'E_EFFECT_AUTHORITY' `
                    -Message "Effect '$effect' requires '$capability'." `
                    -Path '$.effects' `
                    -Evidence @{effect=$effect;capability=$capability}))
            }
        }
    }

    [pscustomobject][ordered]@{
        valid=($errors.Count-eq0)
        errors=@($errors.ToArray())
    }
}

function ConvertTo-AriaStableJson {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)]$Value)

    $activeReferences = New-Object 'System.Collections.Generic.List[object]'

    function Test-AriaCanonicalScalar([object]$InputValue){
        if($null-eq$InputValue){return $true}

        $type=$InputValue.GetType()
        return (
            $type.IsPrimitive -or
            $type.IsEnum -or
            $InputValue-is[string] -or
            $InputValue-is[decimal] -or
            $InputValue-is[DateTime] -or
            $InputValue-is[DateTimeOffset] -or
            $InputValue-is[Guid] -or
            $InputValue-is[TimeSpan] -or
            $InputValue-is[Uri]
        )
    }

    function Convert-AriaCanonicalScalar([object]$InputValue){
        if($null-eq$InputValue){return $null}

        if($InputValue-is[DateTime]){
            return $InputValue.ToUniversalTime().ToString(
                'yyyy-MM-ddTHH:mm:ss.fffffffZ',
                [Globalization.CultureInfo]::InvariantCulture
            )
        }

        if($InputValue-is[DateTimeOffset]){
            return $InputValue.ToUniversalTime().ToString(
                'yyyy-MM-ddTHH:mm:ss.fffffffZ',
                [Globalization.CultureInfo]::InvariantCulture
            )
        }

        if($InputValue-is[TimeSpan]){
            return $InputValue.ToString(
                'c',
                [Globalization.CultureInfo]::InvariantCulture
            )
        }

        if($InputValue-is[Guid] -or
           $InputValue-is[Uri] -or
           $InputValue.GetType().IsEnum -or
           $InputValue-is[char]){
            return [string]$InputValue
        }

        return $InputValue
    }

    function Enter-AriaCanonicalReference([object]$Reference){
        if($null-eq$Reference){return $false}
        if($Reference.GetType().IsValueType -or $Reference-is[string]){return $false}

        foreach($active in $activeReferences){
            if([object]::ReferenceEquals($active,$Reference)){
                throw 'ARIA canonical JSON rejects cyclic object graphs.'
            }
        }

        [void]$activeReferences.Add($Reference)
        return $true
    }

    function Exit-AriaCanonicalReference([object]$Reference,[bool]$Entered){
        if(-not$Entered){return}

        $last=$activeReferences.Count-1
        if($last-lt0 -or -not[object]::ReferenceEquals($activeReferences[$last],$Reference)){
            throw 'ARIA canonical JSON reference stack lost coherence.'
        }

        $activeReferences.RemoveAt($last)
    }

    function Normalize-AriaCanonicalValue([object]$InputValue){
        if($null-eq$InputValue){return $null}

        # BaseObject determines scalar/container semantics. The original
        # InputValue retains the ETS property bag for PSCustomObject values.
        $baseValue=$InputValue.PSObject.BaseObject
        if($null-eq$baseValue){$baseValue=$InputValue}

        if(Test-AriaCanonicalScalar $baseValue){
            return Convert-AriaCanonicalScalar $baseValue
        }

        $isCustomObject=$baseValue-is[Management.Automation.PSCustomObject]
        $trackReference=(
            $baseValue-is[Collections.IDictionary] -or
            ($baseValue-is[Collections.IEnumerable] -and -not($baseValue-is[string]))
        )
        $reference=if($trackReference){$baseValue}else{$null}
        $entered=Enter-AriaCanonicalReference $reference

        try{
            if($baseValue-is[Collections.IDictionary]){
                $keyMap=New-Object 'System.Collections.Generic.Dictionary[string,object]'
                $keyNames=New-Object 'System.Collections.Generic.List[string]'

                foreach($actualKey in $baseValue.Keys){
                    $keyName=[string]$actualKey
                    if($keyMap.ContainsKey($keyName)){
                        throw "ARIA canonical JSON rejects duplicate string key '$keyName'."
                    }

                    $keyMap.Add($keyName,$actualKey)
                    [void]$keyNames.Add($keyName)
                }

                $keyNames.Sort([StringComparer]::Ordinal)
                $ordered=[ordered]@{}
                foreach($keyName in $keyNames){
                    $actualKey=$keyMap[$keyName]
                    $ordered[$keyName]=Normalize-AriaCanonicalValue $baseValue[$actualKey]
                }
                return $ordered
            }

            if($baseValue-is[Collections.IEnumerable] -and -not($baseValue-is[string])){
                $items=New-Object 'System.Collections.Generic.List[object]'
                foreach($item in $baseValue){
                    [void]$items.Add((Normalize-AriaCanonicalValue $item))
                }

                $array=@($items.ToArray())
                return ,$array
            }

            if($isCustomObject){
                $propertyMap=New-Object 'System.Collections.Generic.Dictionary[string,object]'
                $propertyNames=New-Object 'System.Collections.Generic.List[string]'

                # Do not inspect $baseValue.PSObject.Properties here. The
                # PSCustomObject's NoteProperty bag belongs to the original
                # PowerShell wrapper represented by $InputValue.
                foreach($property in @($InputValue.PSObject.Properties)){
                    if($property.MemberType-ne[Management.Automation.PSMemberTypes]::NoteProperty){
                        continue
                    }

                    $propertyName=[string]$property.Name
                    if($propertyMap.ContainsKey($propertyName)){
                        throw "ARIA canonical JSON rejects duplicate property '$propertyName'."
                    }

                    $propertyMap.Add($propertyName,$property)
                    [void]$propertyNames.Add($propertyName)
                }

                $propertyNames.Sort([StringComparer]::Ordinal)
                $ordered=[ordered]@{}
                foreach($propertyName in $propertyNames){
                    $property=$propertyMap[$propertyName]
                    $ordered[$propertyName]=Normalize-AriaCanonicalValue $property.Value
                }
                return $ordered
            }

            if($baseValue-is[IFormattable]){
                return $baseValue.ToString(
                    $null,
                    [Globalization.CultureInfo]::InvariantCulture
                )
            }

            return [string]$baseValue
        }
        finally{
            Exit-AriaCanonicalReference -Reference $reference -Entered $entered
        }
    }

    (Normalize-AriaCanonicalValue $Value) |
        ConvertTo-Json -Depth 64 -Compress
}

function Get-AriaSha256Hex {
    [CmdletBinding()]
    param([Parameter(Mandatory=$true)][string]$Text)

    $sha=[Security.Cryptography.SHA256]::Create()
    try{
        $bytes=[Text.Encoding]::UTF8.GetBytes($Text)
        -join($sha.ComputeHash($bytes) | ForEach-Object {$_.ToString('x2')})
    }
    finally{$sha.Dispose()}
}

function Test-AriaTypedIr {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]$Document,
        [switch]$VerifyDeclaredDigest
    )

    $errors=New-Object 'System.Collections.Generic.List[object]'

    if([string]$Document.schema-ne'aria.typed-ir/0.2'){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_IR_SCHEMA' `
            -Message 'Unsupported typed IR schema.' `
            -Path '$.schema'))
    }

    if($null-eq$Document.entry){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_IR_ENTRY' `
            -Message 'Typed IR requires an entry function.' `
            -Path '$.entry'))
    }

    $functionNames=@{}
    foreach($function in @($Document.functions)){
        if([string]::IsNullOrWhiteSpace([string]$function.name)){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_IR_FUNCTION_NAME' `
                -Message 'Function name is required.' `
                -Path '$.functions'))
            continue
        }

        if($functionNames.ContainsKey([string]$function.name)){
            [void]$errors.Add((New-AriaStructuredError `
                -Code 'E_IR_FUNCTION_DUPLICATE' `
                -Message "Duplicate function '$($function.name)'." `
                -Path '$.functions'))
        }
        else{$functionNames[[string]$function.name]=$true}

        $authority=Test-AriaEffectAuthority `
            -Effects @($function.effects) `
            -Capabilities @($function.capabilities)
        foreach($error in @($authority.errors)){[void]$errors.Add($error)}

        foreach($instruction in @($function.instructions)){
            if([string]$instruction.op-notin@(
                'const','load','store','call','branch','jump','return',
                'make.option','make.result','match','emit.event'
            )){
                [void]$errors.Add((New-AriaStructuredError `
                    -Code 'E_IR_OPCODE' `
                    -Message "Unknown opcode '$($instruction.op)'." `
                    -Path ("$.functions[{0}].instructions" -f $function.name)))
            }
        }
    }

    if($null-ne$Document.entry -and -not$functionNames.ContainsKey([string]$Document.entry)){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_IR_ENTRY_UNKNOWN' `
            -Message "Entry function '$($Document.entry)' is not defined." `
            -Path '$.entry'))
    }

    $identityDocument=[ordered]@{
        schema=$Document.schema
        entry=$Document.entry
        functions=@($Document.functions)
    }
    $canonical=ConvertTo-AriaStableJson $identityDocument
    $digest=Get-AriaSha256Hex $canonical

    if($VerifyDeclaredDigest -and [string]$Document.digest-ne$digest){
        [void]$errors.Add((New-AriaStructuredError `
            -Code 'E_IR_DIGEST' `
            -Message 'Typed IR digest mismatch.' `
            -Path '$.digest' `
            -Evidence @{expected=$digest;actual=[string]$Document.digest}))
    }

    [pscustomobject][ordered]@{
        valid=($errors.Count-eq0)
        errors=@($errors.ToArray())
        canonical=$canonical
        digest=$digest
    }
}

function Test-AriaTypedIrFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [switch]$VerifyDeclaredDigest
    )

    if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){
        return [pscustomobject][ordered]@{
            valid=$false
            errors=@(New-AriaStructuredError -Code 'E_IR_FILE' -Message 'Typed IR file not found.' -Path $Path)
            canonical=''
            digest=''
        }
    }

    try{
        $document=Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    }
    catch{
        return [pscustomobject][ordered]@{
            valid=$false
            errors=@(New-AriaStructuredError -Code 'E_IR_JSON' -Message $_.Exception.Message -Path $Path)
            canonical=''
            digest=''
        }
    }

    Test-AriaTypedIr -Document $document -VerifyDeclaredDigest:$VerifyDeclaredDigest
}

Export-ModuleMember -Function `
    New-AriaType, `
    ConvertTo-AriaCanonicalType, `
    Test-AriaTypeEqual, `
    New-AriaStructuredError, `
    New-AriaScope, `
    Add-AriaBinding, `
    Resolve-AriaBinding, `
    Set-AriaBindingValue, `
    New-AriaFunctionSignature, `
    Test-AriaFunctionCall, `
    Test-AriaExhaustiveBranch, `
    Test-AriaEffectAuthority, `
    ConvertTo-AriaStableJson, `
    Get-AriaSha256Hex, `
    Test-AriaTypedIr, `
    Test-AriaTypedIrFile