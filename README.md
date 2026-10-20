# NBA 2K27 MyPlayer Camera Mod

**Language:** English | [简体中文](README.zh-CN.md)

Unlocks the **MyPlayer** camera (camera ID 35, shown as “自创球员” in Chinese) in standard offline game camera menus. It does not require a mod loader or change the game files on disk.

## Offline use only

**This mod must be used offline, with Easy Anti-Cheat (EAC) not running.** The program refuses to attach when it detects EAC or the protected launcher. It does not disable or bypass anti-cheat. Do not use it in online modes.

## Install and use

1. Download the latest ZIP from [Releases](https://github.com/swaggyp7/NBA2K27-MyPlayerCamera-Mod/releases) and extract it to a folder outside the game installation.
2. Close any older version of this mod and restart NBA 2K27 in offline mode without EAC. Go to the main menu.
3. Run `Start-Mod.cmd` from the extracted folder. Keep its console window open while playing.
4. In an offline match, open the camera settings and select **MyPlayer** (or **自创球员** in Chinese).
5. To remove the mod during the same game session, switch back to a regular camera such as **2K**, then press Enter in the mod console. Exiting the game also clears the temporary memory changes. If the console closes unexpectedly, exit the game completely before restarting it.

## Compatibility and limits

Version 1.0.4 removes the executable SHA-256 version lock. It still checks the running game's code signatures, original camera list, and ten menu descriptors before writing. If an update changes that layout, it refuses to patch the process. Removing the hash lock does **not** guarantee compatibility with future versions.

The mod changes only runtime menu-list references and the availability flag for camera ID 35. It does not hook the camera-validity or match-initialization functions. Two consecutive MyNBA games, including tip-off and dead-ball resumption, passed testing on the earlier game build. The updated game build passed read-only layout checks; its match behavior and other offline modes have not yet been fully tested.

## Source and tests

The implementation is in [`src/myplayer_camera_minimal.py`](src/myplayer_camera_minimal.py), with Windows process helpers in [`src/camera_state.py`](src/camera_state.py). Run the lifecycle tests with:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

To build a standalone Windows executable, install PyInstaller and run:

```powershell
pyinstaller --onefile --console --name NBA2K27-MyPlayerCamera-Minimal src/myplayer_camera_minimal.py
```

Some Conda Python installations require bundling `Library\bin\ffi.dll` with PyInstaller's `--add-binary` option.
