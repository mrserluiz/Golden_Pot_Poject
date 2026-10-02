# Golden Pot

Golden Pot is a safe, generic folder comparison tool. It was originally designed
to compare an accumulated Minecraft Bedrock resource pack with a new Rainbow
output, but it does not depend on Minecraft, Rainbow, Geyser, or any specific
folder structure.

The current version is **v0.1 (Comparator)**. It is read-only: Golden Pot never
copies, edits, overwrites, or removes files while comparing folders.

## What it does

Choose any two folders:

- **Base folder**: the existing or reference state.
- **Comparison folder**: the new state you want to inspect.

Golden Pot classifies every relative path as:

- `ADDED`: exists only in the comparison folder.
- `UNCHANGED`: exists in both folders with the same SHA-256 hash.
- `MODIFIED`: exists in both folders, but its contents differ.
- `PRESERVED`: exists only in the base folder.
- `PROTECTED`: differs, but matches a configured protected path.
- `ERROR`: could not be read safely.

It produces a detailed JSON report and a human-readable TXT report.

## Download for Windows

Download `GoldenPot.exe` from the latest GitHub release. It is a portable
application: no installation or separate Python download is required.

1. Open `GoldenPot.exe`.
2. Select the base folder and the comparison folder.
3. Select where the reports will be saved.
4. Click **Analyze folders**.

Windows may display a SmartScreen warning because this community build is not
digitally signed. Use **More info** and **Run anyway** only when the file was
downloaded from this official repository.

## Requirements for running from source

- Python 3.11 or newer.
- Tkinter for the graphical interface. It is included with the standard Windows
  Python installer.

No third-party Python packages are required to run Golden Pot.

## Installation

Download or clone the repository, open a terminal in its folder, and run:

```powershell
python -m pip install .
```

After that, the `golden-pot` and `golden-pot-gui` commands will be available.

## Graphical interface

After installation:

```powershell
golden-pot-gui
```

You can also run `python -m golden_pot` from an editable development installation.

Select the base folder, comparison folder, and report destination, then click
**Analyze folders**.

## Command line

```powershell
python -m golden_pot compare \`
  --base "E:\Packs\Main" \`
  --comparison "E:\Packs\New" \`
  --output "E:\Packs\Reports"
```

To use a custom configuration:

```powershell
python -m golden_pot compare \`
  --base "E:\Folder A" \`
  --comparison "E:\Folder B" \`
  --output "E:\Reports" \`
  --config "E:\golden-pot.json"
```

## Configuration

The default configuration is located at `config/golden-pot.json`.

```json
{
  "hash_algorithm": "sha256",
  "protected_paths": [
    "manifest.json",
    "textures/block/crop/"
  ],
  "ignored_paths": [
    ".git/",
    "reports/",
    "output/",
    "__pycache__/"
  ]
}
```

Protected and ignored paths use forward slashes and are relative to each selected
folder. A path ending in `/` applies to the entire directory.

## Development

Run the automated tests from the repository root:

```powershell
python -m unittest discover -s tests -v
```

### Build the Windows executable

Install PyInstaller and build from the repository root on Windows:

```powershell
python -m pip install . pyinstaller
python -m PyInstaller --noconfirm --clean GoldenPot.spec
```

The executable will be created at `dist/GoldenPot.exe`. The GitHub Actions
workflow performs the same build, runs the tests, and attaches the executable
to every tagged release.

## Project roadmap

- **v0.1**: generic read-only folder comparison and reports.
- **v0.2**: optional safe merge into a new output folder.
- **v0.3**: semantic merge strategies for JSON and other structured files.

The original files will remain untouched by default in every future version.
