# artifacts/ — 接入实测产物

这里放的是**跑出来的证据**，不是配置也不是脚本。用来证明「这套接入真的连上了 Power BI」，也用来在没有 Power BI 环境时对拍接口形状。

| 产物 | 大小 | 说明 |
|---|---|---|
| `modeling-tools.json` | ~209 KB | `powerbi-modeling-mcp` 的**完整工具清单快照**（`tools/list` 原样落盘）：21 个工具的名称、描述、`inputSchema`。想不装服务就了解它暴露哪些能力，直接翻这个文件 |
| `CodexConnectionCheck/` | 小 | **端到端连通性验证工程**（PBIP 最小工程）：1 个语义模型 + 1 张表 + 1 个报表页，专门用来验「发现 Desktop 实例 → 连接 → 读模型」链路 |

## 怎么重新生成

```powershell
cd tools\runtime ; npm install

# 只握手 + 重新导出工具清单（不碰 Power BI）
node ..\verify-modeling.cjs inspect

# 连文件夹模式的语义模型（无需打开 Power BI Desktop）
node ..\verify-modeling.cjs

# 连已经打开 CodexConnectionCheck 的 Desktop 实例（含 DAX 查询验证）
node ..\verify-modeling.cjs desktop
```

三种模式全部通过时打印 `VERIFICATION_PASSED`。

## `CodexConnectionCheck` 结构

```
CodexConnectionCheck/
├── CodexConnectionCheck.pbip                       # 工程入口
├── Check.Report/definition/                        # 空报表（1 页，验 PBIR 可读）
└── Check.SemanticModel/definition/
    ├── model.tmdl
    └── tables/ConnectionCheck.tmdl                 # 单表，用于 List 验证
```

`desktop` 模式会在这张模型上跑 `EVALUATE ROW("ConnectionCheck", 1 + 1)`，返回 `2` 即证明 DAX 通道可用。
