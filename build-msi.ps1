
function addDir {
  param (
        [string]$dir
  )
  write-host "addDir $dir"
  $mydir = (split-path -leaf $dir)

  if ($mydir = ".\client") {
        New-InstallerFile $dir/client.exe -Id "mainFile"
  }

  New-InstallerDirectory -DirectoryName $mydir -Content {
    Get-ChildItem $dir -file -Recurse -Depth 0 |  Where-Object -Property Name -notmatch client.exe | ForEach-Object { write-host "addFile: $dir/$_"; New-InstallerFile $dir/$_ }
    Get-ChildItem $dir -directory -Recurse -Depth 0 | split-path -Leaf | ForEach-Object { addDir $dir/$_ }
  }
}

New-Installer -ProductName "LVPN" -Manufacturer "Lethean.Space" -ProductId "672fe9ec-7d23-4d80-a194-fabe5dcc4dc6" -UpgradeCode '111a932a-b7dc-4276-a42c-241250f33483' -Version 0.1 -Content {
    New-InstallerDirectory -PredefinedDirectory "LocalAppDataFolder"  -Content {
       New-InstallerDirectory -DirectoryName "LVPN" -Content {
          addDir .\client
          New-InstallerDirectory -PredefinedDirectory "DesktopFolder" -Content {
            New-InstallerShortcut -Name "LVPN" -FileId "mainFile"
          }
       }
    }
 } -OutputDirectory (Join-Path $pwd "msi") -AddRemoveProgramsIcon "$pwd\..\config\icon.ico"
