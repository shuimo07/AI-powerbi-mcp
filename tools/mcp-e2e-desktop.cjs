// E2E check: official powerbi-modeling MCP against a RUNNING Power BI Desktop
// local Analysis Services instance (discovered via ListLocalInstances).
// Usage: node tools/mcp-e2e-desktop.cjs [serverAddress]
//   serverAddress defaults to the first instance returned by ListLocalInstances.
// Requires the MCP SDK on NODE_PATH (same environment as @deepseek-ai/dsh-mcp-client).
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');

const serverArg = process.argv[2];
const baseEnv = Object.assign({}, process.env, {
  NPM_CONFIG_CACHE: process.env.NPM_CONFIG_CACHE || 'E:\\.npm-cache',
  TEMP: process.env.TEMP || 'E:\\Temp',
  TMP: process.env.TMP || 'E:\\Temp',
});

async function call(client, name, args) {
  const res = await client.callTool({ name, arguments: args });
  return (res.content || []).filter((c) => c.type === 'text').map((c) => c.text).join('\n');
}

(async () => {
  const t0 = Date.now();
  try {
    const transport = new StdioClientTransport({
      command: 'npx',
      args: ['-y', '@microsoft/powerbi-modeling-mcp', '--start'],
      env: baseEnv,
      stderr: 'pipe',
    });
    const client = new Client({ name: 'dsh-e2e-desktop', version: '1.0.0' });
    await client.connect(transport);

    const instances = await call(client, 'connection_operations', { request: { operation: 'ListLocalInstances' } });
    console.log('DISCOVER:', instances.slice(0, 700));

    let address = serverArg;
    if (!address) {
      const parsed = JSON.parse(instances);
      const first = (parsed.data || [])[0];
      if (!first) {
        console.log('No local instance found — is Power BI Desktop running with a report open?');
        await client.close();
        process.exit(0);
      }
      address = `localhost:${first.port}`;
    }
    console.log('TARGET:', address);

    const connect = await call(client, 'connection_operations', {
      request: { operation: 'Connect', connectionString: `data source=${address}` },
    });
    console.log('CONNECT:', connect.slice(0, 500));

    const dbs = await call(client, 'database_operations', { request: { operation: 'List' } });
    console.log('DATABASES:', dbs.slice(0, 600));

    const model = await call(client, 'model_operations', { request: { operation: 'Get' } });
    console.log('MODEL:', model.slice(0, 400));

    console.log(`DESKTOP_E2E_OK elapsed=${Date.now() - t0}ms`);
    await client.close();
  } catch (e) {
    console.log(`DESKTOP_E2E_FAIL error=${e && e.message ? e.message : String(e)}`);
  }
  process.exit(0);
})();
