Set-StrictMode -Version 2.0
$ErrorActionPreference='Stop'

function Get-AriaSubsetNames($Object){
  if($Object-is[Collections.IDictionary]){return @($Object.Keys|ForEach-Object{[string]$_})}
  @($Object.PSObject.Properties|ForEach-Object{[string]$_.Name})
}
function Get-AriaSubsetValue($Object,[string]$Name){
  if($Object-is[Collections.IDictionary]){
    if($Object.Contains($Name)){return $Object[$Name]}
    return $null
  }
  $p=$Object.PSObject.Properties[$Name]
  if($null-ne$p){return $p.Value}
  $null
}
function Get-AriaSignalSubsetBody($Subset){
  [pscustomobject][ordered]@{
    format=[string]$Subset.format
    version=[int]$Subset.version
    purpose=[string]$Subset.purpose
    source=[string]$Subset.source
    fields=@($Subset.fields)
    excludedFields=@($Subset.excludedFields)
    sourceCount=[int]$Subset.sourceCount
    emittedCount=[int]$Subset.emittedCount
    limit=[int]$Subset.limit
    consent=$Subset.consent
    items=@($Subset.items)
  }
}
function Get-AriaSignalSubsetDigest($Subset){
  Get-AriaSha256Text (ConvertTo-AriaJson (Get-AriaSignalSubsetBody $Subset))
}
function New-AriaSignalSubset {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory=$true)][object[]]$Items,
    [Parameter(Mandatory=$true)][string[]]$Fields,
    [Parameter(Mandatory=$true)][string]$Purpose,
    [Parameter(Mandatory=$true)][string]$Source,
    [Parameter(Mandatory=$true)][string]$ConsentBasis,
    [Parameter(Mandatory=$true)][string]$ConsentScope,
    [ValidateRange(1,4096)][int]$Limit=32,
    [ValidateSet('session','day','week','release','indefinite')][string]$Retention='session'
  )
  $fields=@($Fields|ForEach-Object{([string]$_).Trim()}|Where-Object{$_}|Sort-Object -Unique)
  if($fields.Count-eq0){throw 'At least one field is required.'}
  $all=New-Object 'System.Collections.Generic.HashSet[string]'
  $selected=New-Object System.Collections.Generic.List[object]
  $sourceItems=@($Items)
  $take=[Math]::Min($Limit,$sourceItems.Count)
  for($i=0;$i-lt$sourceItems.Count;$i++){
    $item=$sourceItems[$i]
    foreach($n in @(Get-AriaSubsetNames $item)){[void]$all.Add($n)}
    if($i-ge$take){continue}
    $o=[ordered]@{}
    foreach($f in $fields){$o[$f]=Get-AriaSubsetValue $item $f}
    $selected.Add([pscustomobject]$o)
  }
  $subset=[pscustomobject][ordered]@{
    format='aria.signal-subset'
    version=1
    purpose=$Purpose
    source=$Source
    fields=$fields
    excludedFields=@($all|Where-Object{$_-notin$fields}|Sort-Object)
    sourceCount=$sourceItems.Count
    emittedCount=$selected.Count
    limit=$Limit
    consent=[pscustomobject][ordered]@{
      basis=$ConsentBasis
      scope=$ConsentScope
      retention=$Retention
    }
    items=$selected.ToArray()
    digest=''
  }
  $subset.digest=Get-AriaSignalSubsetDigest $subset
  $subset
}
function Test-AriaSignalSubset {
  [CmdletBinding()]
  param([Parameter(Mandatory=$true)]$Subset)
  $errors=New-Object System.Collections.Generic.List[string]
  if([string]$Subset.format-ne'aria.signal-subset'){$errors.Add('format mismatch')}
  if([int]$Subset.version-ne1){$errors.Add('version mismatch')}
  if(@($Subset.fields).Count-eq0){$errors.Add('fields missing')}
  if([int]$Subset.emittedCount-gt[int]$Subset.limit){$errors.Add('limit exceeded')}
  if([int]$Subset.emittedCount-gt[int]$Subset.sourceCount){$errors.Add('source count exceeded')}
  if(@($Subset.items).Count-ne[int]$Subset.emittedCount){$errors.Add('item count mismatch')}
  foreach($item in @($Subset.items)){
    if(@(Get-AriaSubsetNames $item|Where-Object{$_-notin@($Subset.fields)}).Count){
      $errors.Add('item contains non-allowlisted field')
    }
  }
  $expected=''
  try{$expected=Get-AriaSignalSubsetDigest $Subset}catch{$errors.Add($_.Exception.Message)}
  if($expected-and[string]$Subset.digest-ne$expected){$errors.Add('digest mismatch')}
  [pscustomobject][ordered]@{valid=($errors.Count-eq0);errors=$errors.ToArray();digest=$expected}
}
function New-AriaSubsetTransmission {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory=$true)]$Subset,
    [Parameter(Mandatory=$true)][string]$Channel,
    [ValidateSet('pass','reject','warn','fail','info')][string]$Status='info',
    [string]$Source='signal-subset'
  )
  $v=Test-AriaSignalSubset $Subset
  if(-not$v.valid){throw ('Signal subset rejected: '+($v.errors-join'; '))}
  New-AriaTransmission -Channel $Channel -Kind signal-subset -Status $Status -Source $Source -Payload $Subset
}
Export-ModuleMember -Function Get-AriaSignalSubsetDigest,New-AriaSignalSubset,Test-AriaSignalSubset,New-AriaSubsetTransmission