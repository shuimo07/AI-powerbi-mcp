# Power BI Desktop 接入记录

三个 MCP 服务器与 Power BI Desktop 的联动之所以成立，是因为 Desktop 启动时会拉起一个**本地 Analysis Services 实例**（`msmdsrv.exe`），在 `%LOCALAPPDATA%\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces\AnalysisServicesWorkspace_<guid>\` 下留工作区，并把监听端口写进 `msmdsrv.port.txt`。三个 server 各自用不同方式接上它。

## 1. 实测结果（参考机，Desktop 2.157.879.0）

| server | Desktop 能力 | 状态 | 证据 |
|---|---|---|---|
| `powerbi-modeling` | 本地实例发现 + 直连 + 模型读取 | ✅ 原生支持 | `connection_operations ListLocalInstances` 找到 `port 53243`（`parentProcessName=PBIDesktop`）→ `Connect` 成功 → `database_operations List` 列出 1 个库（compatibilityLevel 1606）→ `model_operations Get` 读到模型 |
| `powerbi-designer` | PBIDesktop 定位（doctor / 视觉 QA 探针） | ✅ 配置即通 | 设 `POWERBI_DESKTOP_PATH` 后 `powerbi-mcp-doctor` 输出 `[OK] powerbi_desktop: <...>\PBIDesktop.exe`；QA 类工具可用 `pbidesktop_path` 参数传入 |
| `powerbi` (AjvoGod) | `pbix_discover_desktop_models`、`pbix_extract_desktop_semantic_model` | ✅ 打补丁后可用 | 发现返回 `count=1`、`localhost:53243`；提取返回 server/database 与各 DMV 数组 |

## 2. 环境事实（参考机）

- Desktop 程序本体放在 **E 盘**（`<tools>\bin\PBIDesktop.exe` + `msmdsrv.exe`），两者签名均由 Microsoft Corporation 签发且校验有效。
- 开始菜单快捷方式已指向该 E 盘路径；HKLM 保留了原 MSI 安装记录（详见"注意事项"）。
- 工作区端口文件实际位置：`<workspace>\Data\msmdsrv.port.txt`，内容为**端口号，UTF-16LE 编码**。
- 本地 AS 实例监听 `127.0.0.1:<port>`，随 Desktop 启停。

## 3. 对 AjvoGod 服务器所做的修复

上游 `src/pbix/desktopModelExtractor.ts` 在**较新的 Power BI Desktop 构建**上有两处会导致功能完全不可用，另有若干兼容性问题。补丁见同仓库 `patches/powerbi-mcp-desktop-discovery.patch`：

```bash
git clone https://github.com/AjvoGod/powerbi-mcp
cd powerbi-mcp
git apply /path/to/powerbi-mcp-desktop-discovery.patch
npm install && npm run build
```

四处改动：

1. **端口文件位置**：上游只找 `<workspace>\msmdsrv.port.txt`；当前 Desktop 写在 `<workspace>\Data\msmdsrv.port.txt` → 改为两处都找。
2. **端口文件编码**：上游按 UTF-8 读；实际是 UTF-16LE → 改为两种解码都试并提取数字（否则解析出 `NaN` 并被静默跳过，表现为"找不到任何实例"）。
3. **ADOMD 程序集加载**：上游只尝试 GAC 与 SQL Server feature pack 路径（多数机器没有）→ 改为三级回退：
   1. `ADOMD_DLL` 环境变量指向的程序集；
   2. 官方 `%ProgramFiles%\Microsoft.NET\ADOMD.NET\{160,150}\...`；
   3. **从运行中的 `msmdsrv.exe` 进程路径自动加载 Power BI Desktop 自带的 `Microsoft.PowerBI.AdomdClient.dll`**（该程序集含完整 ADOMD API，`PublicKeyToken=89845dcd8080cc91`，实测可连本地 AS）。
   同时把两处写死的程序集限定名 `[type]::GetType('…AdomdDataAdapter, Microsoft.AnalysisServices.AdomdClient')` 改为从已加载程序集解析，避免因程序集名不同而返回 `$null`。
4. **DMV 列集差异**：上游按旧架构写死列名（`TMSCHEMA_COLUMNS.Name/DataType`、`TMSCHEMA_PARTITIONS.SourceType`），在 compatibilityLevel 1606 上直接报"找不到指定的列" → 五条 DMV 改为 `SELECT *`（跨版本稳健）；`Invoke-Dmv` 用 `return ,$rows` 保住空数组，避免 PowerShell 把空数组展开成 `$null`。

> 重新构建后，需让 MCP 客户端重新加载该 server（DSH 下改动该条目的 `env` 即触发 HMR 重载），新进程才会加载新的 `dist`。

## 4. 配置片段（DSH）

```yaml
    - id: mcp-powerbi-designer
      config:
        # …
        env:
          POWERBI_DESKTOP_PATH: 'E:\PowerBI_Tools\bin\PBIDesktop.exe'

    - id: mcp-powerbi
      config:
        # …
        env:
          POWERBI_PBIX_ROOT: 'E:\PowerBI_Projects'
          ADOMD_DLL: 'E:\PowerBI_Tools\bin\Microsoft.PowerBI.AdomdClient.dll'
          LOG_LEVEL: 'info'
```

## 5. 验证方式

`tools/mcp-e2e-desktop.cjs`（需把 `BASE_ENV` 里的缓存目录按自己机器调整）：

```powershell
$env:NODE_PATH = '<dsh 包所在 node_modules 目录>'
node tools\mcp-e2e-desktop.cjs
```

它会依次执行 `ListLocalInstances → Connect → database_operations List → model_operations Get` 并打印结果。

## 6. 注意事项

- **未打开报表时结果是空的**：Desktop 停在欢迎/空白页时，本地 AS 里没有已处理的模型，DMV 返回 0 行——这属正常，不代表接入失败；打开任意报表（或 PBIP/PBIX 项目）后再读即可。
- **把程序移出 C 盘会让 MSI 记录失效**：程序文件移走后，HKLM 里那条 MSI 安装记录仍指向原位置，日后升级/修复会出问题。建议要么重装到目标盘、要么接受"便携布局 + 手工更新"。
- **用户数据仍在 C 盘**：`%LOCALAPPDATA%\Microsoft\Power BI Desktop`（工作区、WebView2 缓存、AutoRecovery、Traces）由 Desktop 强制写入，无法重定向。
- 端口文件的位置与编码在不同 Desktop 版本间有过变化，补丁已同时兼容两种；若后续构建再次变化，这两处是最先要看的地方。
