# nightreign-boss-timer

[English](README.md) | **简体中文** | [繁體中文](README.zh-TW.md)

通过读取屏幕上的 Boss 血条，记录《艾尔登法环 黑夜君临》（ELDEN RING NIGHTREIGN）中每场 Boss 战的用时。
设计目标是不对游戏帧数造成可测量的影响。

> 本页由 AI 翻译，尚未经母语者审校。如与[英文版](README.md)有出入，以英文版为准。

> **状态：早期版本，作者本人在用。** 记录、悬浮窗、托盘菜单、主窗口、区域标定、全局快捷键和初次设置
> 均可使用，界面支持 English、简体中文和繁體中文。作者在 2560x1440、游戏语言为简体中文的环境下使用，
> 检测逻辑用 21 段 1920x1080 和 2560x1440 的战斗录像做过测试。其他分辨率、超宽屏、游戏语言为英文或
> 繁体中文的情况尚未测试，对帧数的影响也还没有实测。

## 快速开始

不需要安装 Python，也不需要下载源代码。

1. 打开本仓库的 [Releases 页面](https://github.com/tomstao/nightreign-boss-timer/releases/latest)，
   下载 `nightreign-boss-timer-<版本>-windows.zip`。
2. 把整个 ZIP 解压到一个可写的文件夹，例如 `C:\Tools\nightreign-boss-timer`。
3. 运行其中的 `nightreign-boss-timer.exe`。Windows 可能弹出 SmartScreen 警告，因为程序没有签名：
   点击 **更多信息**，再点击 **仍要运行**。
4. 把游戏设为 **窗口化** 或 **无边框窗口**，然后去打 Boss。记录是自动的。

程序图标在系统托盘里（时钟旁边，可能藏在 **^** 箭头后面）。点击它可以打开主窗口。

## 功能

- Boss 血条出现时开始计时，Boss 血量归零时停止。
- 每场战斗保存为 CSV 文件中的一行，可直接用 Excel 打开：日期时间、表格、Boss 名称、用时、开始和结束时的
  Boss 血量百分比、你的等级，以及你设置的角色。
- Boss 血条清空或出现击败文字时，记为 `complete`（已完成）；血条消失而 Boss 还有血量时，记为
  `incomplete`（未完成）。
- 回到之前打过的残血 Boss，会作为一条新记录，从当时的血量百分比开始。
- 记录按表格分组：`Arena`（Boss 竞技场 Mod 练习）、`Normal`（正常游戏），也可以自己添加。
- 在一个小悬浮窗上显示表格、Boss、计时和 Boss 血量。悬浮窗不会拦截鼠标点击。
- 全局快捷键可以自行修改，用于暂停、切换表格等操作。
- 能读取 English、简体中文和繁體中文的 Boss 名称，内置 210 个 Boss 的三语名称。无论游戏是什么语言，
  都按你选择的语言保存和显示名称。
- 记录列表支持筛选、显示每个 Boss 的最佳用时，并可以删除记录。

## 安装

### 系统要求

| | |
|---|---|
| 操作系统 | 64 位 Windows 10 或 Windows 11。建议 Windows 10 2004 或更高版本 |
| 游戏 | ELDEN RING NIGHTREIGN，**窗口化** 或 **无边框窗口** 模式 |
| 游戏语言 | English、简体中文或繁體中文 |
| 磁盘空间 | 约 180 MB |
| 内存 | 运行时约 200 MB |

不需要安装其他东西。程序自带 Python 和所需的一切。

### 下载并运行

见上面的[快速开始](#快速开始)。请保持文件夹内的所有文件在一起，不要直接在 ZIP 里运行程序。
只运行从本仓库下载的 ZIP。

### 第一次启动

1. 系统托盘（时钟旁边）会出现一个图标，可能藏在 **^** 箭头后面。
2. 会打开一个简短的设置向导：选择语言、检查是否找到游戏、选择表格和保存记录的文件夹。
   可以跳过，之后再改。
3. 把游戏设为窗口化或无边框窗口，去打 Boss。记录是自动的。
4. 如果游戏画面不是 16:9，或者战斗没有被记录，请标定两个区域：让 Boss 血条出现在屏幕上，
   然后按 `Ctrl+Alt+C`。

点击托盘图标打开主窗口：记录、表格、快捷键、区域和设置。**退出** 在托盘图标的右键菜单里。
各部分的说明见[用户指南](docs/USER_GUIDE.md)（英文）。

### 文件位置

记录和设置保存在程序文件夹之外，所以更新或删除程序不会影响它们。

| 内容 | 位置 |
|---|---|
| 记录 | `文档\nightreign-boss-timer\records.csv`，除非你选择了其他文件夹 |
| 设置 | `%APPDATA%\nightreign-boss-timer\settings.json` |
| 日志（反馈问题时用） | `%LOCALAPPDATA%\nightreign-boss-timer\logs\app.log` |

把路径粘贴到文件资源管理器的地址栏即可打开。

### 更新

1. 从托盘图标退出程序。
2. 删除或重命名旧的程序文件夹。
3. 解压新的 ZIP，运行新的 `nightreign-boss-timer.exe`。

### 卸载

1. 从托盘图标退出程序。
2. 删除程序文件夹。
3. 如需彻底清除，再删除 `%APPDATA%\nightreign-boss-timer` 和
   `%LOCALAPPDATA%\nightreign-boss-timer`。只有在不再需要战斗记录时，才删除
   `文档\nightreign-boss-timer`。

本工具不安装驱动和服务，不写注册表，也不往游戏文件夹里写任何东西。

### 遇到问题

| 问题 | 可以尝试 |
|---|---|
| 运行后好像没有反应 | 在系统托盘 **^** 箭头后面找图标。点击图标之前，程序没有窗口。 |
| 程序完全无法启动 | 先把整个 ZIP 解压出来。检查杀毒软件有没有删除文件夹里的文件。查看日志文件。 |
| 托盘图标上有一个金色圆点 | 没有找到游戏窗口。请以窗口化或无边框窗口模式启动游戏。 |
| 战斗没有被记录 | 屏幕上有 Boss 血条时，打开主窗口的 **区域** 页面，可以看到工具看到的画面。用 `Ctrl+Alt+C` 标定。 |
| 快捷键没有反应 | 打开 **快捷键** 页面。标有“未生效”的快捷键被其他程序占用了，请换一个。 |
| 看不到悬浮窗 | 把游戏设为窗口化或无边框窗口。检查托盘菜单里的 **显示悬浮窗**。 |
| 录屏里没有悬浮窗 | 在 **设置** 页面打开“在截图和录像中显示悬浮窗”。OBS 请使用“显示器采集”。 |

更多内容见[用户指南](docs/USER_GUIDE.md#troubleshooting)。反馈问题时，请附上日志文件，并说明游戏语言、
分辨率和窗口模式。

## 自己构建

需要 [Git](https://git-scm.com/) 和 [uv](https://docs.astral.sh/uv/)。uv 会自动下载合适的 Python。

```powershell
git clone https://github.com/tomstao/nightreign-boss-timer.git
cd nightreign-boss-timer
uv sync --dev
uv run python tools/fetch_model.py
uv run python tools/build_exe.py
```

`fetch_model.py` 下载用于读取 Boss 名称的文字识别模型（21 MB，只需一次）并校验。`build_exe.py` 生成
`dist\nightreign-boss-timer` 文件夹和对应的 ZIP，大约需要两分钟。

从源码直接运行（用于开发）：`uv run python -m nightreign_boss_timer.ui.app`。

## 工作原理

本工具是一个独立的程序，只看屏幕像素。

1. 它复制游戏窗口中的几个小区域：Boss 血条、击败文字，以及战斗开始时的 Boss 名称和玩家等级。
2. 战斗中每秒对血条做十次颜色和形状检查，得到 Boss 血量百分比。这一步不使用模型，所以开销很小。
3. 文字识别每场战斗只运行几次，在 CPU 上进行，用来在血条出现时读取 Boss 名称和等级。
4. 击败文字是通过外观识别的，不会被当作文字读取，所以不需要处理语言。

## 安全性

本工具不读取游戏内存，不注入代码，也不修改游戏文件。其他读取屏幕的黑夜君临工具用的也是这种方式。
但没有任何第三方工具能保证与反作弊软件绝对兼容，使用风险由你自行承担。

本项目与 FromSoftware 和 Bandai Namco 没有任何关联。

## 关于 AI 的使用

本仓库中的大部分代码、测试和文档是在维护者的指导和审查下，用 AI 编程助手（Anthropic 的 Claude Code）
编写的。这样产生的提交带有 `Co-Authored-By: Claude` 一行。

这对你意味着：

- 做什么由维护者决定，每个改动由维护者合并，并且必须通过测试。检测逻辑用战斗录像验证，见
  [docs/observations.md](docs/observations.md)。
- AI 写的代码可能看起来正确但其实有错。没有测试过的地方，文档里会写明。请把它当作早期软件，
  遇到问题欢迎反馈。
- 程序本身不运行任何 AI 服务，也不向任何地方发送数据。Boss 名称由一个在你自己电脑上运行的小型
  文字识别模型读取。
- 界面的中文文本和本页都由 AI 编写，尚未经母语者审校。

正如[许可证](LICENSE)所说，本软件不提供任何担保。

## 文档

以下文档目前只有英文：

- [用户指南](docs/USER_GUIDE.md)：设置、日常使用、记录、表格、快捷键、疑难解答
- [安装说明](docs/INSTALL.md)：更详细的安装步骤
- [参与贡献](CONTRIBUTING.md)、[更新日志](CHANGELOG.md)、[安全策略](SECURITY.md)

## 许可证

[MIT](LICENSE)。打包后的程序还包含其他开源软件和一个文字识别模型，各自遵循其许可证，见
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
