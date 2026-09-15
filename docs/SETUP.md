# Cursed Color | Setup and Workings i guess

This document explains how CursedColor actually works under the hood, why its built the way it is, and how to set it up manually if you don't trust my super safe and secure but not shady seeming `install_dependencies.ps1`

## Overview

CursedColor is a Krita docker plugin written in Python, using Krita's built-in `pykrita` plugin system and PyQt5 for its UI. Every 500ms, it reads your CPU and GPU temperature from the operating system, computes new values from them, and applies the result to Krita's active foreground color.

## Why sensor reading is kinda stupid and annoying and pissed me off

Windows doesn't expose CPU/GPU temps through a standard python library (booo). `psutil.sensors_temperatures()`, the usual go-to, is Linux-only, it silently returns nothing on Windows. Getting the actual temp data on windows means either running a seperate application, a vendor SDK, or directly loading a hardware-monitoring library inside your own process

CursedColor uses the 3rd option, loading the **LHM** library (`LibreHardwareMonitorLib.dll`) directly into Krita`s Python process. This avoids depending on a seperate app running in the background at all once set up.

## Why its loaded through memory + reflection

Krita bundles its own .NET framework 4.x runtime for `pythonnet` (the library that lets Python talk to .Net/C# code). LHM's mainline builds now target modern .NET which is completely different and incompatible as a runtime. 

The fix is to use the net472 specific build of the dll which ships inside the official NuGet package and NOT the same DLL inside the desktop app itself (that runs on modern .NET), and NOT anything under a `ref/` folder in the NuGet package.

Even the correct `net472` build needs a few small dependencies that .NET doesn't ship by default (`System.Memory`, `System.Buffers`, `System.Numerics.Vectors`, `System.Runtime.CompilerServices.Unsafe`) which are smaller polyfill packages that back-port modern .NET APIs to older runtimes. 

On top of the version problem, .NET framework's assembly loader refuses to `LoadFrom(path)` a DLL under certain security policies(a legacy CAS/zone restriction, unrelated to Windows' file-download "Mark of the Web" flagging). The workaround is to read the DLL's raw bytes and use `Assembly.Load(byte[])` instead, which loads from memory rather than a file path and sidesteps this check entirely. Loading this way also means Python's normal `from Namespace import Type` import style doesn't register correctly so instead it uses .NET reflection directly.

## Why Krita must run as Administrator

Reading GPU temperature (via NVIDIA's driver interface) doesn't need elevated permissions. Reading **CPU** temperature does, LibreHardwareMonitor needs a kernel-level driver to read CPU MSRs (model-specific registers) directly, and that driver only loads successfully when the host process is elevated. Without Admistrator, CPU sensors silently report `0.0` instead of throwing an error, which is what makes this failure mode so easy to miss, everything looks like its working but with a stuck value.

## Color Logic

Instead of snapping R/G directly to a normalized temp reading each tick (which locks the pallete to whatever narrow temp band your hardware idles in), CursedColor reads the current foreground color and nudges it: 
`step = (current_temp - baseline_temp) * (drift_rate / 100) * dt`
`new_channel_value = clamp(current_channel_value + step, 0, 255)`

So the color changes from wherever its already at instead of resetting every half second, sustained heat pushes a channel towards its extreme over time, sustained cool pushes it back down, and manually picking a color becomes the new starting point for future drift instead of getting overwritten.

The B channel works differently, it tracks the smoothed rate of change of (CPU temp, GPU temp), spiking when the two are diverging quickly and staying low at steady rate.


## Manual Setup (its kinda rude that you dont trust my super safe script btw)

1. Download the DLLs into C:\KritaPluginLibs\:
   - LibreHardwareMonitorLib.dll
     https://cdn.hackclub.com/01a0a2d0-e87d-7535-8650-beae11343cb1/LibreHardwareMonitorLib.dll
   - System.Memory.dll
     https://cdn.hackclub.com/01a0a2d0-eca2-7635-9715-351e1add57a2/System.Memory.dll
   - System.Buffers.dll
     https://cdn.hackclub.com/01a0a2d0-eabe-704c-be2d-01138c570874/System.Buffers.dll
   - System.Numerics.Vectors.dll
     https://cdn.hackclub.com/01a0a2d0-ee5d-755f-87b2-f0943a0703e1/System.Numerics.Vectors.dll
   - System.Runtime.CompilerServices.Unsafe.dll
     https://cdn.hackclub.com/01a0a2d0-f00d-7672-959a-9de24f71c713/System.Runtime.CompilerServices.Unsafe.dll

2. python -m pip install pythonnet --target "C:\KritaPluginLibs"

3. Copy plugin files into %APPDATA%\krita\pykrita\:
   - cursedcolor\__init__.py
   - cursedcolor\cursedcolor_docker.py
   - cursedcolor.desktop   (sits next to the folder, not inside it)

4. Unblock + fix permissions on both C:\KritaPluginLibs and the cursedcolor folder:
   Get-ChildItem <path> -Recurse | Unblock-File
   icacls <path> /grant "$env:USERDOMAIN\$env:USERNAME:(F)" /T

5. Restart Krita, enable the plugin, restart again AS ADMINISTRATOR,
   open a document, show the docker.


Troubleshooting

- Grayed-out plugin -> failed to load; hover for a tooltip, or launch with
  & "krita.exe" *> log.txt to capture the error.
- "Sensors not found" -> not running as Administrator, or a DLL is missing.
- CPU stuck at 0.0 -> not elevated. Restart as Administrator.
- PermissionError on a file -> broken ACLs; fix with the icacls command above.
- BadImageFormatException -> grabbed a DLL from ref/ instead of lib/.
- TypeLoadException / PlatformID error -> wrong .NET target; need the net472 build.
- FileNotFoundException for System.Memory etc. -> missing a dependency DLL.
- Not in Dockers list -> open a document first; if still missing, check
  Plugin Manager, then check .desktop file placement.