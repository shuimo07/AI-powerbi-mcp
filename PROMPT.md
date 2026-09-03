# 【最终版】DSH × Power BI MCP 全家桶接入任务（本机定制）

> 使用方法：把以下整段内容粘贴给 DSH（模型建议选 DeepSeek-V4-Pro）。
> 本版已按本机实测修正：Node@`D:\AI\固件`、Python 3.12 商店版@C 盘、`DSH_HOME=E:\.dsh`（活动 profile=web）、Power BI Desktop 未安装、当前非管理员、npm 全局 prefix 在 C 盘、沙箱可能无外网、写文件会弹审批。
> 存储原则：**所有新建/下载/缓存/临时内容一律优先 E 盘**；已装好的系统组件（Node/Python/git/pnpm/dsh 本体）不迁移、不重装、不改全局配置。

---

## 一、角色与目标

你是运行在 DeepSeek Harness（DSH）中的 AI 助手。目标：在本机把三个 Power BI 相关 MCP 服务器接入 DSH 的**活动 profile**，让 DSH 中的模型能像 Codex + MCP 方案那样直接调用 Power BI 的语义建模、报表设计（PBIP/PBIR）与 PBIX/云操作能力，并完成连通性验收。

执行铁律：
1. **先查后改**：一切以本机实测为准；写文件前先读原文件。
2. 每阶段结束给简短中文报告（做了什么 / 结果 / 下一步）。
3. 需要用户手动的事（下载、双击安装、登录、UAC、GUI 审批弹窗）→ 立即暂停，说清要用户做什么、完成标准是什么、如何让任务继续。
4. 出错先自动修复一次并记录；修复失败则暂停询问，不要无限重试。
5. 全程不要触碰凭据文件（`.credentials.yaml` 等），不要输出密钥。

## 二、核心约束（按优先级）

- **C1 存储策略**：所有新建目录、下载包、缓存、临时文件、日志**尽可能放 E 盘**。每个会写缓存的子进程统一重定向：`TEMP/TMP=E:\Temp`、`NPM_CONFIG_CACHE=E:\.npm-cache`、`UV_CACHE_DIR=E:\.uv-cache`、`UV_TOOL_DIR=E:\.uv-tools`、`UV_PYTHON_INSTALL_DIR=E:\.uv-python`、`PIP_CACHE_DIR=E:\Downloads\pip-cache`。
- **C2 组件不动**：已安装的 Node（`D:\AI\固件`）、Python（商店版@C）、git、pnpm、DSH 本体**不迁移、不重装、不改全局配置**。尤其禁止 `npm config set prefix`、禁止改系统 PATH/注册表、禁止改用户 `.npmrc`。npm/npx 缓存重定向只通过环境变量（`NPM_CONFIG_CACHE`）做，不写配置文件。
- **C3 最小豁免**：仅当某应用强制写系统路径且无法重定向（例：Power BI Desktop 的用户数据 `%LOCALAPPDATA%\Microsoft\Power BI Desktop`）时，允许最小写入，但**必须在最终报告中逐条列出这些 C 盘写入点**。
- **C4 改动边界**：禁止修改 DSH 核心文件；`C:\Users\legion\.dsh` 是**旧的非活动 home，只读禁写**（改错地方=白改）。活动 home 由 `$env:DSH_HOME` 决定（本机=`E:\.dsh`）。只允许三处改动：① 追加式修改活动 profile 的 `cordis.patch.yml`；② 在 `$env:DSH_HOME\skills` 下新增技能目录；③ 在 E 盘创建/修改工作文件。
- **C5 环境**：Windows 10/11 x64。执行环境为 DSH 网页客户端，工具以 pwsh、文件读写、web_search、后台任务为准。

## 三、阶段 0：事实核查（只读，先做）

0.1 输出环境表并核对（不要假设，全部实测）：
- Node：`node -p "process.execPath+' | v'+process.versions.node"`（预期 v24.19.0@D:\AI\固件）
- npm：`npm --version`、`npm config get prefix`（预期 C:\Users\legion\AppData\Roaming\npm，**不得修改**）、`npm config get cache`（预期 C 盘 → 后续全部用 `NPM_CONFIG_CACHE` 环境变量重定向）
- Python：`python -c "import sys;print(sys.executable)"`、`py -0p`、`python -m pip --version`（预期 3.12 商店版@C，够用不装新的）
- 工具：`uv --version`（预期没有）、`git --version`
- 权限：`whoami /groups`（预期非管理员）
- 网络：对 `https://registry.npmjs.org/` 做一次 8 秒超时的连通测试（Invoke-RestMethod/curl）。**若无外网 → 暂停**，请用户改为在能联网的终端执行安装命令，或由用户下载到 `E:\Downloads` 后本地安装。
0.2 DSH 配置定位：
- 确认 `$env:DSH_HOME`（≠ C:\Users\legion\.dsh），列出 `$env:DSH_HOME\profiles` 下的 profile 目录；
- 确认活动 profile（含 `cordis.patch.yml` 且与正在运行的 web 实例一致的那个；本机预期为 `web`）→ 配置目标文件 = `$env:DSH_HOME\profiles\<活动profile>\cordis.patch.yml`；
- 通读该文件现有全部内容（后续只追加，不删改任何现有条目）。
0.3 报告结论表，等待用户确认后进入阶段 1。

## 四、阶段 1：目录与运行时准备（全部 E 盘）

1.1 创建目录：`E:\PowerBI_Projects`（PBIP/PBIX 项目）、`E:\Downloads`（下载）、`E:\Temp`、`E:\.npm-cache`、`E:\.uv-cache`、`E:\.uv-tools`、`E:\.uv-python`、`E:\PowerBI_Tools`（工具与源码克隆）。
1.2 安装 uv 到 E 盘（供 uvx 跑 designer）：若 `uv --version` 不可用 → 下载 `uv-x86_64-pc-windows-msvc.zip`（GitHub releases）到 `E:\Downloads`，解压到 `E:\PowerBI_Tools\uv`，确认 `E:\PowerBI_Tools\uv\uvx.exe` 存在。下载需外网；若不通 → 暂停请用户下载并放入 `E:\Downloads`。**不修改系统 PATH**：后续在 YAML 里直接用全路径 `E:\PowerBI_Tools\uv\uvx.exe`。
1.3 技能包（可选推荐）：把 bi-superpowers 相关内容取到 `E:\PowerBI_Tools\bi-superpowers`（npm pack 或 git clone；注意**不要执行 `super install --agent dsh`**——DSH 不在 superpowers 官方 agent 列表，预期失败）。若其技能是 `<技能名>\SKILL.md` + YAML frontmatter（name/description）结构 → 复制到 `$env:DSH_HOME\skills\`（本机 `E:\.dsh\skills`），保持目录结构；复制后确认 DSH 技能目录能识别（参考现有技能如 niu-san-* 的存放方式）。格式不兼容则记录差异并暂停询问是否继续。

## 五、阶段 2：核实三个 MCP 服务器的真实安装方式（先核实后配置）

对每个 server 做"证据优先"核实（本地 README + web_search + npm view/pip index），**不要把下面的默认值当真理**：

2.1 **powerbi-modeling（官方语义建模）**：`@microsoft/powerbi-modeling-mcp`。核实：npm 包名与最新版、启动方式（npx -y）、Node 版本要求、**运行模式与认证要求**——官方文档（learn.microsoft.com "Power BI MCP 服务器"）表明通常需要 Power BI 服务工作区 + 认证（用户登录态或服务主体）。若需要服务主体/租户管理员授权 → 属人工步骤，进阶段 6 暂停等用户，不要自行猜测凭据。
2.2 **powerbi-designer（报表视觉/布局，PBIP/PBIR file-first）**：仓库 `dbru540/powerbi-mcp-designer`。git clone 或下载 zip 到 `E:\PowerBI_Tools\powerbi-mcp-designer`，**必须通读 README.md 与 README_INSTALL.md**，确认：语言/运行时（Python→uvx 还是 Node→npx）、包名与入口、是否需要 Power BI Desktop 或本地 PBIP 项目、官方给的 MCP 配置示例。若 `pip install powerbi-mcp-designer` 或 PyPI 包名不成立 → 以 README 为准（大概率是 `uvx powerbi-mcp-designer`）。
2.3 **powerbi（PBIX 分析/语义模型提取/报表导出/云操作）**：仓库 `AjvoGod/powerbi-mcp`。clone 到 `E:\PowerBI_Tools\powerbi-mcp` 并通读 README，确认：运行方式（`npx -y github:AjvoGod/powerbi-mcp` 是否可行 / 是否需本地构建 / 是否 Python）、**它真实要求的环境变量名**（`POWERBI_PBIX_ROOT` 待证实，不同名则以 README 为准）、外部依赖（是否需 PBIX 文件/Power BI Desktop/云账号）、官方 MCP 配置示例。
2.4 **预热下载（可选但推荐）**：若走 npx 方案，先手动执行一次 `npx -y <包> --help`（超时 15 秒即终止）把包下载进 `E:\.npm-cache`，避免 server 首启时卡住 MCP 的 60 秒初始化超时。
2.5 把三个 server 的最终"启动命令 + env"汇总给用户过目（与附录 A 不一致时说明差异与依据），确认后进入阶段 3。

## 六、阶段 3：配置 DSH（唯一改动 DSH 的地方）

3.1 编辑 `$env:DSH_HOME\profiles\<活动profile>\cordis.patch.yml`：
- 在文件末尾**追加一个** `- insert:` 块（内容见附录 A，如阶段 2 核实结果有出入则以核实结果为准）；
- 不删除、不修改任何现有条目；注意该文件顶层是补丁数组，**新插件必须包在 insert 列表内**，不要写成顶层裸条目；
- 保留现有注释风格，缩进用 2 空格。
3.2 保存后**重读文件**自查：YAML 缩进正确、三个 id（mcp-powerbi-modeling / mcp-powerbi-designer / mcp-powerbi）不与现有 id 重复、路径引号正确（Windows 反斜杠路径建议用 YAML 单引号，如 `'E:\Temp'`）。
3.3 让 DSH 重载配置（HMR 热重载或重启 web 后端 / 执行 `E:\.dsh\go.bat` 对应启动方式），观察日志中 mcp-client 的连接结果。
3.4 验证工具注册：工具列表应出现 `mcp__powerbi_modeling__*`、`mcp__powerbi_designer__*`、`mcp__powerbi__*`（前缀=serverName）。逐个 server 调用一个只读工具冒烟测试（如列出数据集/列/工具清单）。故障排查：
- 日志报 spawn/ENOENT/EINVAL（Windows 下 npx 是 `npx.cmd`、无 `npx.exe`，可能无法直接 spawn）→ 把该条目 `command` 改为 `cmd`、`args` 改为 `['/c', 'npx', '-y', '<包>', ...]`，或把 command 换成 npm bin 目录全路径（如 `D:\AI\固件\npx.cmd`），其余字段不变，重载；
- 首次连接超时/激活慢（MCP SDK 60 秒初始化超时 + npx 首次下载）→ 检查 reconnect 日志，通常自动重试可恢复；仍不行则回到 2.4 预热；
- 需要账号/授权 → 记入阶段 6 人工清单，该 server 记为"待认证"；
- 其余错误：看日志定位，自动修复一次，失败暂停询问。
3.5 报告：每个 server 的工具数量、连接状态、冒烟结果。

## 七、阶段 4：工作区内容准备（E 盘）

4.1 在 `E:\PowerBI_Projects` 下建立测试项目结构：`.pbip` 目录 + `definition`（如无可用的真实项目，则用 designer/官方文档的最小 PBIP 模板生成骨架，不假装成功——生成不了就如实说）。
4.2 若用户有现成 `.pbix`/`.pbip`，请其放到 `E:\PowerBI_Projects`（任务暂停等待）。

## 八、阶段 5：端到端验收（每项都要有可复现结果）

5.1 建模：用 powerbi-modeling 对某个语义模型做只读检查（列出表/度量/关系）——若无可用模型/账号，则只验证"工具可调、报错信息可解释"。
5.2 设计：用 powerbi-designer 对 `E:\PowerBI_Projects` 下的 PBIP 项目做一次只读检查或最小改动后还原。
5.3 综合：用 powerbi 对 pbix/pbip 做结构分析或报表导出（若该能力需 Desktop/云，如实记录）。
5.4 输出最终报告（保存到 `E:\PowerBI_Projects\接入报告.md`）：
- 环境事实表（各组件位置）；
- 安装清单（每个组件的精确路径，全部应在 E 盘）；
- **C 盘写入点清单**（豁免项逐条列出）；
- 三个 server 的工具数量、连接与冒烟结果；
- 遗留问题与下一步建议；
- **回滚方案**：删除追加的 insert 块并重载即可，不触碰其他内容。

## 九、阶段 6：人工前置清单（暂停等用户，逐项确认后补测）

6.1 **Power BI Desktop（必须）**：本机未安装，且当前非管理员、零售版安装器不支持自定义安装目录（INSTALLLOCATION 无官方支持）→ **由用户手动完成**：从官方渠道下载并安装（https://aka.ms/pbidesktopsetup 或微软官网 Power BI 下载页），安装后**打开一次并登录** Power BI 账号。DSH 侧不做静默安装。默认装到 C 盘 Program Files、用户数据在 `%LOCALAPPDATA%` → 记入豁免清单。
6.2 **云操作认证（可选）**：若要操作 Power BI 服务工作区（语义模型 MCP workspace 模式 / 云操作），需要：Desktop 登录态或 Azure AD 服务主体 + 相应许可证/租户管理员授权。由用户在其 Power BI 门户完成；DSH 只接收"已就绪"的确认，不接触凭据。
6.3 用户提供测试文件或账号就绪后，回到阶段 5 补测，最后更新接入报告。

## 附录 A：默认 YAML（追加到活动 profile 的 cordis.patch.yml 末尾）

如阶段 2 核实结果与下列不同，**以核实结果为准**并修改对应字段后使用。

```yaml
# ===== Power BI MCP servers (appended; do not touch entries above) =====
- insert:
    - id: mcp-powerbi-modeling
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: powerbi-modeling
        transport: stdio
        command: npx
        args: ['-y', '@microsoft/powerbi-modeling-mcp']
        env:
          NPM_CONFIG_CACHE: 'E:\.npm-cache'
          TEMP: 'E:\Temp'
          TMP: 'E:\Temp'
        toolCallTimeoutMs: 120000

    - id: mcp-powerbi-designer
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: powerbi-designer
        transport: stdio
        command: 'E:\PowerBI_Tools\uv\uvx.exe'
        args: ['powerbi-mcp-designer']
        env:
          UV_CACHE_DIR: 'E:\.uv-cache'
          UV_TOOL_DIR: 'E:\.uv-tools'
          UV_PYTHON_INSTALL_DIR: 'E:\.uv-python'
          TEMP: 'E:\Temp'
          TMP: 'E:\Temp'
        toolCallTimeoutMs: 120000

    - id: mcp-powerbi
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: powerbi
        transport: stdio
        command: npx
        args: ['-y', 'github:AjvoGod/powerbi-mcp']
        env:
          POWERBI_PBIX_ROOT: 'E:\PowerBI_Projects'
          NPM_CONFIG_CACHE: 'E:\.npm-cache'
          TEMP: 'E:\Temp'
          TMP: 'E:\Temp'
        toolCallTimeoutMs: 120000
```

**Windows spawn 兜底**：若某 server 报 spawn ENOENT（npx 无 .exe），把该条 `command` 改为 `cmd`、`args` 改为 `['/c', 'npx', '-y', '<包>', ...]`（或 command 用 `D:\AI\固件\npx.cmd` 全路径），env 不变。

## 附录 B：允许的 C 盘写入豁免（报告必须逐条列出）

- 已存在组件本体：Node@D:\AI\固件、Python/pip@C 盘 WindowsApps、git@C:\Program Files\Git、npm 全局包与 pnpm@C:\Users\legion\AppData\Roaming\npm（**不迁移**）；
- DSH 本体@C:\Users\legion\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh（只读使用）；
- Power BI Desktop（如用户安装）：安装目录与 `%LOCALAPPDATA%\Microsoft\Power BI Desktop` 用户数据；
- 其它任何 C 盘写入必须先在报告中申报，能重定向的必须重定向到 E 盘。
