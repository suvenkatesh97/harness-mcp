import { tool } from "@opencode-ai/plugin"

export const HarnessMcpPlugin = async ({ $, directory }) => {
  return {
    tool: {
      harness_mcp_list: tool({
        description: "List available MCP servers from the harness-mcp catalog.",
        args: {
          tag: tool.schema.string().optional(),
          query: tool.schema.string().optional(),
        },
        async execute(args, context) {
          const tagFlag = args.tag ? ` --tag ${args.tag}` : ""
          const queryArg = args.query ? ` ${args.query}` : ""
          const result = await $`harness-mcp list${tagFlag}${queryArg} --harness opencode --cwd ${directory}`
          return result.stdout
        },
      }),

      harness_mcp_add: tool({
        description: "Add an MCP server to your OpenCode config from the harness-mcp catalog.",
        args: {
          server: tool.schema.string(),
          env: tool.schema.string().optional(),
        },
        async execute(args, context) {
          const envFlag = args.env ? ` --env '${args.env}'` : ""
          const result = await $`harness-mcp add ${args.server}${envFlag} --harness opencode --cwd ${directory}`
          return result.stdout
        },
      }),

      harness_mcp_remove: tool({
        description: "Remove an MCP server from your OpenCode config.",
        args: {
          server: tool.schema.string(),
        },
        async execute(args, context) {
          const result = await $`harness-mcp remove ${args.server} --harness opencode --cwd ${directory}`
          return result.stdout
        },
      }),

      harness_mcp_status: tool({
        description: "Show currently configured MCP servers in your harness config.",
        args: {},
        async execute(args, context) {
          const result = await $`harness-mcp status --harness opencode --cwd ${directory}`
          return result.stdout
        },
      }),

      harness_mcp_search: tool({
        description: "Search the MCP server catalog.",
        args: {
          query: tool.schema.string(),
        },
        async execute(args, context) {
          const result = await $`harness-mcp search ${args.query} --harness opencode --cwd ${directory}`
          return result.stdout
        },
      }),
    },
  }
}
