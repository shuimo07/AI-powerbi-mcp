// Minimal MCP inspector: spawn each configured server over stdio, do
// initialize + tools/list, print tool name counts.
// Usage:
//   node tools/mcp-inspect.cjs '<inline-json>'          # inline spec array
//   node tools/mcp-inspect.cjs @<spec-file.json>        # spec read from file
// Spec item: { name, command, args?, env?, cwd?, timeoutMs? }
// Requires the MCP SDK resolvable: set NODE_PATH to the folder containing
// node_modules/@modelcontextprotocol (e.g. the dsh package's node_modules).
const fs = require('fs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');

const specArg = process.argv[2];
const spec = specArg.startsWith('@')
  ? JSON.parse(fs.readFileSync(specArg.slice(1), 'utf8'))
  : JSON.parse(specArg);

const baseEnv = Object.assign({}, process.env, {
  NPM_CONFIG_CACHE: process.env.NPM_CONFIG_CACHE || 'E:\\.npm-cache',
  TEMP: process.env.TEMP || 'E:\\Temp', TMP: process.env.TMP || 'E:\\Temp',
  UV_CACHE_DIR: process.env.UV_CACHE_DIR || 'E:\\.uv-cache',
  UV_TOOL_DIR: process.env.UV_TOOL_DIR || 'E:\\.uv-tools',
  UV_PYTHON_INSTALL_DIR: process.env.UV_PYTHON_INSTALL_DIR || 'E:\\.uv-python',
  PIP_CACHE_DIR: process.env.PIP_CACHE_DIR || 'E:\\Downloads\\pip-cache',
  POWERBI_PBIX_ROOT: process.env.POWERBI_PBIX_ROOT || 'E:\\PowerBI_Projects',
});

(async () => {
  for (const s of spec) {
    const label = `[${s.name}]`;
    const t0 = Date.now();
    try {
      const transport = new StdioClientTransport({
        command: s.command,
        args: s.args || [],
        env: Object.assign({}, baseEnv, s.env || {}),
        cwd: s.cwd,
        stderr: 'pipe',
      });
      const client = new Client({ name: 'dsh-mcp-inspect', version: '1.0.0' });
      const timeoutMs = s.timeoutMs || 90000;
      await Promise.race([
        client.connect(transport),
        new Promise((_, rej) => setTimeout(() => rej(new Error('connect timeout')), timeoutMs)),
      ]);
      const tools = await Promise.race([
        client.listTools(),
        new Promise((_, rej) => setTimeout(() => rej(new Error('listTools timeout')), timeoutMs)),
      ]);
      const names = (tools.tools || []).map((t) => t.name);
      console.log(`${label} CONNECT_OK elapsed=${Date.now() - t0}ms toolCount=${names.length}`);
      console.log(`${label} tools=${JSON.stringify(names)}`);
      await client.close();
    } catch (e) {
      console.log(`${label} FAIL elapsed=${Date.now() - t0}ms error=${e && e.message ? e.message : String(e)}`);
    }
  }
  process.exit(0);
})();
