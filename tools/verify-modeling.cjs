/**
 * verify-modeling.cjs — Microsoft 官方 powerbi-modeling-mcp 端到端自检
 *
 * 做四件事：
 *   1. initialize 握手，列出工具清单并落盘到 artifacts/modeling-tools.json
 *   2. connection_operations / ListLocalInstances  —— 发现运行中的 Power BI Desktop 实例
 *   3. ConnectFolder（或 desktop 模式下的 Connect）—— 连上语义模型
 *   4. table_operations / measure_operations List  —— 只读读取模型
 *   全部通过则打印 VERIFICATION_PASSED。
 *
 * 路径约定（可用环境变量覆盖）：
 *   POWERBI_MCP_HOME  仓库根目录，默认取本脚本的上一级
 *   POWERBI_MCP_EXE   powerbi-modeling-mcp.exe 路径，默认取 tools/runtime/node_modules 下
 *
 * 用法：
 *   node tools/verify-modeling.cjs             # 连本地 PBIP 文件夹（artifacts/CodexConnectionCheck）
 *   node tools/verify-modeling.cjs inspect     # 只握手 + 列工具
 *   node tools/verify-modeling.cjs desktop     # 连已打开 CodexConnectionCheck 的 Desktop 实例
 *
 * 前置：
 *   cd tools/runtime && npm install
 */
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');

const HOME = process.env.POWERBI_MCP_HOME || path.resolve(__dirname, '..');
const RUNTIME = path.join(HOME, 'tools', 'runtime');

const runtimeRequire = createRequire(path.join(RUNTIME, 'package.json'));
const { Client } = runtimeRequire('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = runtimeRequire('@modelcontextprotocol/sdk/client/stdio.js');

const EXE = process.env.POWERBI_MCP_EXE || path.join(
  RUNTIME, 'node_modules', '@microsoft', 'powerbi-modeling-mcp-win32-x64',
  'dist', 'powerbi-modeling-mcp.exe');

const OUT = path.join(HOME, 'artifacts', 'modeling-tools.json');
const MODELFOLDER = path.join(HOME, 'artifacts', 'CodexConnectionCheck',
                              'Check.SemanticModel', 'definition');
const TMP = path.join(HOME, 'temp');

const mode = process.argv[2] || 'folder';
fs.mkdirSync(TMP, { recursive: true });
fs.mkdirSync(path.dirname(OUT), { recursive: true });

const client = new Client({ name: 'powerbi-modeling-verification', version: '1.0.0' });
const transport = new StdioClientTransport({
  command: EXE,
  args: ['--start', '--require-confirmation'],
  env: { ...process.env, TEMP: TMP, TMP },
  cwd: RUNTIME,
  stderr: 'pipe',
});

let stderr = '';
transport.stderr?.on('data', d => { stderr = (stderr + d.toString()).slice(-12000); });

async function call(name, request) {
  const result = await client.callTool({ name, arguments: { request } }, undefined, { timeout: 45000 });
  const text = result.content?.filter(c => c.type === 'text').map(c => c.text).join('\n') || '';
  if (result.isError) throw new Error(`${name}: ${text}`);
  let data;
  try { data = JSON.parse(text); } catch { throw new Error(`${name}: non-JSON result: ${text.slice(0, 1000)}`); }
  if (data.success === false) throw new Error(`${name}: ${JSON.stringify(data)}`);
  return data;
}

(async () => {
  try {
    await client.connect(transport, { timeout: 45000 });

    const tools = await client.listTools();
    fs.writeFileSync(OUT, JSON.stringify(tools, null, 2), 'utf-8');
    console.log(JSON.stringify({
      stage: 'initialize',
      server: client.getServerVersion(),
      toolCount: tools.tools.length,
      tools: tools.tools.map(t => t.name),
    }));

    const discovery = await call('connection_operations', { operation: 'ListLocalInstances' });
    console.log(JSON.stringify({ stage: 'discover', result: discovery }));

    if (mode === 'inspect') { console.log('VERIFICATION_PASSED'); return; }

    if (mode === 'desktop') {
      const selected = (discovery.data || []).find(i => JSON.stringify(i).includes('CodexConnectionCheck'));
      if (!selected) {
        throw new Error('未找到 CodexConnectionCheck 的 Desktop 实例（请先打开 artifacts/CodexConnectionCheck/CodexConnectionCheck.pbip）。');
      }
      const connect = await call('connection_operations',
        { operation: 'Connect', connectionString: `Data Source=localhost:${selected.port}` });
      console.log(JSON.stringify({ stage: 'connect-desktop', result: connect }));
    } else {
      const connect = await call('connection_operations',
        { operation: 'ConnectFolder', folderPath: MODELFOLDER });
      console.log(JSON.stringify({ stage: 'connect-folder', result: connect }));
    }

    for (const name of ['table_operations', 'measure_operations']) {
      console.log(JSON.stringify({ stage: name, result: await call(name, { operation: 'List' }) }));
    }

    if (mode === 'desktop') {
      console.log(JSON.stringify({
        stage: 'dax',
        result: await call('dax_query_operations',
          { operation: 'Execute', query: 'EVALUATE ROW("ConnectionCheck", 1 + 1)' }),
      }));
    }

    console.log('VERIFICATION_PASSED');
  } catch (error) {
    console.error(error.stack || error.message);
    if (stderr) console.error(stderr);
    process.exitCode = 1;
  } finally {
    await client.close();
  }
})();
