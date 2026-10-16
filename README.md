# video_down

一个带桌面界面的通用视频/音乐下载器。粘贴页面链接即可下载；遇到网站将音轨和画面分开提供时，会通过 FFmpeg **自动下载并合并**，无需人工处理。

底层优先使用 [yt-dlp](https://github.com/yt-dlp/yt-dlp)，失败时可自动回退到 [you-get](https://github.com/soimort/you-get)。常见站点包括哔哩哔哩、YouTube、抖音，以及两个引擎支持的其他站点。站点规则会变化，请保持依赖为最新版本。

当前引擎覆盖情况：哔哩哔哩、YouTube 和抖音由 `yt-dlp` 直接支持；酷狗由 `you-get` 回退引擎支持。是否能下载某一条具体内容仍取决于登录状态、地区、版权和站点接口。

> “任何网站”无法被下载工具绝对保证：DRM 加密内容、付费内容、直播协议限制或站点更新都可能阻止下载。请只下载你有权保存的内容，并遵守网站条款及当地法律。

## 安装和启动

需要 Python 3.10 或更高版本。

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e .
python -m video_down
```

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e .
python -m video_down
```

依赖中的 `imageio-ffmpeg` 会提供 FFmpeg；如果系统已安装 FFmpeg，程序会优先使用系统版本。

## 使用提示

- 默认下载最高画质视频，并自动合并为 MP4。
- 选择“仅音频”会提取为 MP3。
- 哔哩哔哩高清内容、年龄限制或需要登录的网站：先在 Chrome/Edge/Firefox 登录，再在“登录浏览器”中选择对应浏览器。
- YouTube 在部分网络环境下需要在“代理”中填写代理，如 `http://127.0.0.1:7890`。
- 酷狗等音乐站点如果页面链接不被支持，可尝试歌曲的分享链接；受版权保护或 DRM 加密的内容无法下载。
- 默认只下载当前内容，勾选“下载播放列表”后才会下载整个列表。

## 命令行

```bash
video-down "https://example.com/video" -o ./downloads
video-down "https://example.com/music" --audio
video-down "https://example.com/video" --browser chrome --proxy http://127.0.0.1:7890
```

查看全部参数：

```bash
video-down --help
```

## 打包 Windows 安装包

在装有 `uv` 和 Inno Setup 6 的 Windows PowerShell 中运行：

```powershell
.\scripts\build_windows.ps1
```

生成结果为 `dist\installer\video_down-Setup.exe`。安装包内包含 Python 运行时、下载引擎和 FFmpeg，目标电脑不需要另装 Python。

仓库也提供了 `.github/workflows/windows-installer.yml`。将项目推送到 GitHub 后，在 Actions 页面手动运行 **Build Windows installer**，完成后从构建产物中下载 `video_down-Windows-installer` 即可。

## 常见问题

### 下载突然失效

视频网站经常调整接口。先更新下载器：

```bash
pip install -U yt-dlp you-get
```

### 提示需要登录或 Cookie

关闭正在运行的隐私/无痕窗口，在受支持的浏览器中正常登录站点，然后在软件里选择该浏览器。浏览器的 Cookie 只由下载器在本机读取，不会被本软件上传。

### 图形界面无法启动（Linux）

安装 Tk：Ubuntu/Debian 可执行 `sudo apt install python3-tk`。服务器没有桌面环境时请使用命令行模式。
