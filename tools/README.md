# tools/ — MCP 自检脚本

无需第三方 MCP 客户端即可验证服务器连通性与工具清单：

- `mcp-inspect.cjs`：对一组服务器做 `initialize` + `tools/list`，输出工具数与清单。
- `mcp-call.cjs`：对单个服务器调用一个只读工具并打印结果（冒烟/验收）。

## 前提

- Node.js 18+（与 `@deepseek-ai/dsh-mcp-client` 相同的运行环境）。
- 能解析 `@modelcontextprotocol/sdk`：设 `NODE_PATH=<dsh 包所在 node_modules 目录>`，
  例如 `C:\Users\<user>\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh\node_modules`，
  或用任意安装有 `@modelcontextprotocol/sdk` 的项目目录。

## 用法示例

```powershell
# 1) 列出三个服务器的工具（spec 写入 JSON 文件）
node tools\mcp-inspect.cjs @spec.json

# 2) 对 designer 调用只读工具 project_get_summary
node tools\mcp-call.cjs spec-designer.json project_get_summary args-summary.json
```

spec 项结构：`{ "name", "command", "args": [], "env": {}, "cwd": "", "timeoutMs": 90000 }`。
脚本内缓存目录等默认值均可用同名环境变量覆盖（`NPM_CONFIG_CACHE`、`TEMP`、`POWERBI_PBIX_ROOT` 等）。
