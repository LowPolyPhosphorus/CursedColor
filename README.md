# CursedColor

CursedColor is a Krita plugin that reads CPU and GPU temperatures and shifts your foreground color vased on them. Instead of picking your color, your creation is influenced by your computers resources

- **R** and **G** channels drift up or down based on how far your CPU/GPU temps are from a baseline you set (by default)
- **B** channel reacts to the rate of change between CPU and GPU temp
- Settings tab lets you remap which channels reads which source, and tune drift rate and baseline
<img width="314" height="211" alt="image" src="https://github.com/user-attachments/assets/2746b5cc-d343-4229-8b08-a38ab2f8f5bf" />
<img width="317" height="205" alt="image" src="https://github.com/user-attachments/assets/99792528-410e-40bc-bc6d-79913451a8ad" />

## Requirements

- Windows
- Krita, **ran as Administrator** (required for CPU temp reading)
- Python packages `pythonnet` installed into a shared libs folder
- `LibreHardwareMonitorLib.dll` (net472 build) plus a few (alot) small dependency DLLs

Full setup instructions, including troubleshooting for common install errors, are in [docs/SETUP.md](docs/SETUP.md).

## Install

Download [`install_dependencies.ps1`](scripts/install_dependencies.ps1) and run it in Powershell:

```powershell
.\install_dependencies.ps1
```

This installs the plugin and all needed components without needing to clone the repo (the dlls are not inside the repo!)
It will:

- Download the plugin files to the `pykrita` folder
- Download `LibreHardwareMonitorLib.dll` and its like 8 dependencies
- Install the `pythonnet` python package
- Fix file permissions so Krita can read everything

After it finishes:

1. Restart Krita
2. Enable CursedColor in Settings > Configure Krita > Python Plugin Manager
3. Restart Krita (with ADMINISTRATOR for temp reading ability) and then open a document
4. Enable the docker by opening Settings > Dockers > CursedColor

Full technical setup details and troubleshooting are in [docs/SETUP.md](docs/SETUP.md).

## Usage

Open a document, and the docker will start reading your CPU/GPU temps and shifting your current foreground color every half second. Adjust channel sources, drift rate, and baseline temp in the Settings tab.

## Troubleshooting 

You can find these steps linked in the docker where it says "Why isn't it working?"
Most issues will come down to Krita not running as Administrator.

## License

[MIT LICENSE](LICENSE)
