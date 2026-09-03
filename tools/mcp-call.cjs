// MCP call test: connect to ONE server (spec file), invoke ONE tool, print result.
// Usage:
//   node tools/mcp-call.cjs <spec.json> <toolName> <args.json|'-'>
// Spec item: { name, command, args?, env?, cwd?, timeoutMs? }  (single object)
const fs = require('fs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');

const [specFile, toolName, argsFile] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(specFile, 'utf8'));
const baseEnv = Object.assign({}, process.env, {
  NPM_CONFIG_CACHE: process.env.NPM_CONFIG_CACHE || 'E:\\.npm-cache',
  TEMP: process.env.TEMP || 'E:\\Temp', TMP: process.env.TMP || 'E:\\Temp',
  UV_CACHE_DIR: process.env.UV_CACHE_DIR || 'E:\\.uv-cache',
  UV_TOOL_DIR: process.env.UV_TOOL_DIR || 'E:\\.uv-tools',
  UV_PYTHON_INSTALL_DIR: process.env.UV_PYTHON_INSTALL_DIR || 'E:\\.uv-python',
  POWERBI_PBIX_ROOT: process.env.POWERBI_PBIX_ROOT || 'E:\\PowerBI_Projects',
});
const callArgs = argsFile && argsFile !== '-' ? JSON.parse(fs.readFileSync(argsFile, 'utf8')) : {};

(async () => {
  const t0 = Date.now();
  try {
    const transport = new StdioClientTransport({
      command: spec.command, args: spec.args || [],
      env: Object.assign({}, baseEnv, spec.env || {}), cwd: spec.cwd, stderr: 'pipe',
    });
    const client = new Client({ name: 'dsh-mcp-calltest', version: '1.0.0' });
    await Promise.race([
      client.connect(transport),
      new Promise((_, rej) => setTimeout(() => rej(new Error('connect timeout')), spec.timeoutMs || 90000)),
    ]);
    const res = await Promise.race([
      client.callTool({ name: toolName, arguments: callArgs }),
      new Promise((_, rej) => setTimeout(() => rej(new Error('callTool timeout')), spec.timeoutMs || 90000)),
    ]);
    console.log(`CALL_OK tool=${toolName} elapsed=${Date.now() - t0}ms`);
    console.log(`RESULT=${JSON.stringify(res).slice(0, 4000)}`);
    await client.close();
  } catch (e) {
    console.log(`CALL_FAIL tool=${toolName} elapsed=${Date.now() - t0}ms error=${e && e.message ? e.message : String(e)}`);
  }
  process.exit(0);
})();
