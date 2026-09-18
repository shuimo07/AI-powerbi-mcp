# tools/ — MCP 自检与验收脚本

无需第三方 MCP 客户端（DSH / Codex / Claude Desktop 都不用装）即可验证 MCP 服务器的连通性与工具清单。

| 脚本 | 作用 |
|---|---|
| `mcp-inspect.cjs` | 对**一组**服务器做 `initialize` + `tools/list`，输出工具数与清单 |
| `mcp-call.cjs` | 对**单个**服务器调用一个工具并打印结果（冒烟 / 验收） |
| `mcp-e2e-desktop.cjs` | Power BI Desktop 端到端：发现实例 → 连接 → 读模型 |
| `verify-modeling.cjs` | 微软官方 `powerbi-modeling-mcp` 端到端自检；顺带把工具清单导出到 `../artifacts/modeling-tools.json` |

## 前提

- Node.js 18+。
- 能解析 `@modelcontextprotocol/sdk`：设 `NODE_PATH=<dsh 包所在 node_modules 目录>`，
  例如 `C:\Users\<user>\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh\node_modules`，
  或用任意安装有 `@modelcontextprotocol/sdk` 的项目目录。
- **`verify-modeling.cjs` 例外**：它自带依赖，在 `tools/runtime/` 里独立安装——

  ```powershell
  cd tools\runtime ; npm install
  ```

  这样跑官方 modeling 服务不必污染全局或 DSH 的 node_modules。

## 用法示例

```powershell
# 1) 列出三个服务器的工具（spec 写入 JSON 文件）
node tools\mcp-inspect.cjs configs\mcp.servers.json

# 2) 对 designer 调用只读工具 project_get_summary
node tools\mcp-call.cjs spec-designer.json project_get_summary args-summary.json

# 3) 官方 modeling 服务端到端自检（三种模式）
node tools\verify-modeling.cjs inspect     # 只握手 + 列工具
node tools\verify-modeling.cjs             # 连本地 PBIP 语义模型文件夹（无需打开 Desktop）
node tools\verify-modeling.cjs desktop     # 连已打开的 Desktop 实例，含 DAX 查询验证
```

## 路径约定

`verify-modeling.cjs` 不再硬编码绝对路径：仓库根目录默认取脚本的上一级，可用环境变量覆盖。

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `POWERBI_MCP_HOME` | `tools/` 的上一级 | 仓库根目录 |
| `POWERBI_MCP_EXE` | `tools/runtime/node_modules/@microsoft/powerbi-modeling-mcp-win32-x64/dist/powerbi-modeling-mcp.exe` | 服务本体 |

其余脚本的 spec 项结构为 `{ "name", "command", "args": [], "env": {}, "cwd": "", "timeoutMs": 90000 }`；
脚本内缓存目录等默认值均可被同名环境变量覆盖（`NPM_CONFIG_CACHE`、`TEMP`、`POWERBI_PBIX_ROOT` 等）。
