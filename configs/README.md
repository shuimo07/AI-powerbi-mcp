# configs/ — MCP 配置与调用样例

本目录是接入方案的**可复制配置**：怎么起三个 MCP 服务、怎么在不开图形客户端的情况下直接调它们的工具、以及改动前要备份什么。

> ⚠️ 所有路径都是**参考机（Windows）实测值**，换机器请按下面的说明替换。

## 文件清单

| 文件 | 作用 |
|---|---|
| `mcp.servers.json` | **三个 MCP 服务器的启动配置**（`npx` / venv python / 本地 node 构建），是 `tools/mcp-inspect.cjs` 的输入 |
| `call-spec-powerbi-modeling.json` | Microsoft 官方 `powerbi-modeling-mcp` 的单服务调用 spec |
| `call-args-list-local-instances.json` | 参数样例：列出本机 Power BI Desktop 实例 |
| `call-args-list-connections.json` | 参数样例：列出当前已连接的数据源 |
| `call-args-connect-folder.json` | 参数样例：连接一个 PBIP 语义模型文件夹 |
| `codex-config-before-powerbi-20260913.sanitized.toml` | **Codex 配置改动前的备份**（已脱敏：抹掉用户名、删除个人项目信任列表）。用途是回滚参照 —— 对照它能看出接入 Power BI Modeling MCP 到底加了什么 |

## `mcp.servers.json` 的三个服务

```jsonc
[
  // ① 微软官方：语义模型（表 / 度量 / 关系 / DAX）
  { "name": "modeling", "command": "npx",
    "args": ["-y", "@microsoft/powerbi-modeling-mcp", "--start"], "timeoutMs": 150000 },

  // ② 报表视觉层：file-first 编辑 PBIP / PBIR
  { "name": "designer", "command": "<venv>\\Scripts\\python.exe",
    "args": ["-m", "powerbi_mcp.server"], "timeoutMs": 60000 },

  // ③ PBIX 分析 / 语义模型提取 / 报表导出 / 云操作
  { "name": "powerbi", "command": "<node.exe>",
    "args": ["<repo>\\powerbi-mcp\\dist\\index.js"], "timeoutMs": 60000 }
]
```

**换机器要改的三处**

| 项 | 参考机值 | 说明 |
|---|---|---|
| `designer` 的解释器 | `E:\PowerBI_Tools\designer-venv\Scripts\python.exe` | 用 venv 而非 `uvx`：Microsoft Store 版 Python 有 EFS 复制错误 |
| `powerbi` 的解释器 | `D:\AI\固件\node.exe` | 任一 Node 18+ 均可 |
| `powerbi` 的入口 | `<repo>\powerbi-mcp\dist\index.js` | 需本地构建：`npm i && npm run build`（参考机 `npx github:` 因 git TLS 证书链异常不可用） |

## 用参数样例直调 MCP 工具

```powershell
# 列本机 Desktop 实例（确认服务活着、能发现 Power BI）
node tools\mcp-call.cjs configs\call-spec-powerbi-modeling.json `
     connection_operations configs\call-args-list-local-instances.json

# 连一个 PBIP 语义模型（把 folderPath 改成你自己的）
node tools\mcp-call.cjs configs\call-spec-powerbi-modeling.json `
     connection_operations configs\call-args-connect-folder.json
```

## 关于 `call-args-connect-folder.json`

里面的 `folderPath` 指向 `.SemanticModel\definition` 目录（不是 `.pbip` 文件本身）：

```
E:\PowerBI_Projects\Focus\Focus.SemanticModel\definition
```

官方 `powerbi-modeling-mcp` 的 `--require-confirmation` 默认开启，写操作会要求确认；本目录的样例全部是**只读**操作。
