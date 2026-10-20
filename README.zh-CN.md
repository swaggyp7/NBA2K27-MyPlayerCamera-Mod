# NBA 2K27 自创球员摄影机 MOD

**语言：** [English](README.md) | 简体中文

在标准离线比赛的摄影机菜单中解锁 **MyPlayer／自创球员** 镜头（编号 35）。无需 MOD 加载器，也不会修改游戏安装目录中的文件。

## 必须离线使用

**本 MOD 必须在离线模式下使用，且 Easy Anti-Cheat（EAC）不能运行。** 如果检测到 EAC 或受保护的启动器，程序会拒绝连接游戏进程。程序不会关闭或绕过反作弊。请勿在在线模式中使用。

## 安装与使用

1. 从 [Releases](https://github.com/swaggyp7/NBA2K27-MyPlayerCamera-Mod/releases) 下载最新 ZIP，解压到游戏安装目录以外的文件夹。
2. 关闭此 MOD 的旧版本，完全重启 NBA 2K27，以未启用 EAC 的离线方式运行，并停在主菜单。
3. 运行解压目录中的 `Start-Mod.cmd`，游戏过程中保持命令窗口打开。
4. 进入离线比赛，打开摄影机设置，选择 **自创球员**（英文界面为 **MyPlayer**）。
5. 如需在本次游戏会话中关闭 MOD，先把镜头切回 **2K** 等普通镜头，再到 MOD 命令窗口按回车。完全退出游戏也会清除本次临时内存修改。如果命令窗口意外关闭，请完全退出游戏后再启动。

## 兼容性与限制

v1.0.4 移除了游戏 EXE 的 SHA-256 版本限制，但写入前仍会核对运行中的代码特征、原始摄影机列表和 10 处菜单引用。如果游戏更新改变了这些内存布局，程序会拒绝写入。移除哈希限制**不代表**支持所有未来版本。

本 MOD 只修改运行时的菜单列表引用及镜头编号 35 的可选标记，不修改摄影机有效性检查或比赛初始化函数。此前的游戏构建已实测连续两场 MyNBA 正常开球，且死球后裁判能捡球并恢复比赛。更新后的构建通过了只读内存布局检查；该构建的比赛流程以及其他离线模式尚未充分验证。

## 源码与测试

实现代码位于 [`src/myplayer_camera_minimal.py`](src/myplayer_camera_minimal.py)，Windows 进程辅助代码位于 [`src/camera_state.py`](src/camera_state.py)。运行生命周期测试：

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

安装 PyInstaller 后，可用以下命令构建独立的 Windows 程序：

```powershell
pyinstaller --onefile --console --name NBA2K27-MyPlayerCamera-Minimal src/myplayer_camera_minimal.py
```

部分 Conda Python 环境需要用 PyInstaller 的 `--add-binary` 参数额外打包 `Library\bin\ffi.dll`。
