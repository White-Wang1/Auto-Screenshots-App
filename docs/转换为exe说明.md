# 如何在 Windows 上生成并运行 `.exe`

本工具提供 Windows 桌面版（一支可执行 `.exe`）。打包需在 Windows 上进行（PyInstaller 只能在 Windows 生成 Windows 程序）。有以下两种方式任选其一。

---

## 方式 A：本机一键打包（推荐）

1. **准备 Python**：在 `https://www.python.org/downloads/` 下载并安装 **Python 3.11 或更高版本**。
   - 安装时**务必勾选 “Add Python to PATH”**。
   - 若你的电脑已有多个 Python，请确保用的是这个官方版本。
2. **双击运行** 项目根目录下的 **`build_exe.bat`**。
   - 脚本会：检测 Python → 检测 pip → 自动安装依赖（mss/opencv/python-pptx/pyinstaller 等）→ 用 PyInstaller 打包。
   - 首次会联网下载依赖，请耐心等待几分钟。
3. **打包完成**：生成的程序位于 **`dist\ScreenCapturePPT.exe`**。
4. 双击 `dist\ScreenCapturePPT.exe` 即可使用；以后可把这个 `.exe` 单独复制到任意 Windows 电脑上直接运行（**无需装 Python**）。

> 若脚本中途报错，请把终端里红色/错误信息截图，通常能直接看出问题（如“No module named pip”、“No Python found”）。

---

## 方式 B：云端一键打包（本机不装 Python）

如果你不想在电脑上装 Python，可用 **GitHub Actions 在云端自动打包**：

1. 把本项目推送到一个 GitHub 仓库（或把解压后的项目提交到仓库）；
2. 打开仓库的 **Actions** 页面，工作流名为 **Build Windows EXE**；
3. 点击 **Run workflow**（也可在 push 到 main/master 时自动触发）；
4. 构建成功后，在本次运行结果页面的 **Artifacts** 里下载 `ScreenCapturePPT.zip`，解压即得 `ScreenCapturePPT.exe`。

云端使用 GitHub 官方 Python 环境，不存在“本机没有 pip”的问题。

---

## 桌面版使用说明（运行 .exe 后）

打开程序后：
1. 点击 **“框选区域”**，在屏幕上拖拽框出要监控的区域（也可在下方直接改 X/Y/宽/高 数值后点“应用”）；
2. 根据需要调整三个参数：**采样间隔(秒) / 变化阈值 / 去重阈值**；
3. 点击 **“▶ 开始检测”**，程序开始实时监控该区域，画面一变就自动截图存入 PPT；
4. 随时可点 **“⏸ 暂停/继续”** 或 **“■ 停止”**；
5. PPT 会自动保存到 `output\screenshots.pptx`，截图原图在 `output\frames\` 下。

**去重说明**：程序会把每个新画面与本会话已写入 PPT 的所有页做对比，相同画面自动跳过，避免重复页。

---

## 常见问题（FAQ）

**Q1：双击 build_exe.bat 报错 “No module named pip” / “找不到 pip”？**
说明当前 Python 是精简/捆绑版本（如某些软件自带的 Python 没有 pip）。解决办法：安装官方 Python 并勾选 “Add Python to PATH”，关闭并重开命令行/双击窗口后再运行；或改用【方式 B 云端打包】。

**Q2：报错 “python 不是内部或外部命令”？**
系统 PATH 里没有 Python。请重新运行官方 Python 安装包，勾选 “Add Python to PATH” 后重试。

**Q3：生成的 exe 打开后没有画面/黑屏预览？**
桌面版需要能读取屏幕；请确认不是在权限受限环境（如 RDP 会话收屏可能被系统阻止），一般登录本机桌面即可正常使用。

---

## 打包时涉及的文件
- `build_exe.bat`：一键打包脚本（纯英文提示，避免编码问题）
- `scripts/screen_capture_gui.py`：桌面 GUI 程序源码
- `scripts/screen_capture_ppt.py`：可选的无 GUI 命令行截图工具
- `requirements.txt`：依赖清单
- `.github/workflows/build-exe.yml`：GitHub Actions 云端打包配置