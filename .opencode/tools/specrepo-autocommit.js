import { tool } from "@opencode-ai/plugin"
import { fileURLToPath } from "node:url"

const script = fileURLToPath(new URL("./specrepo-autocommit.py", import.meta.url))

export default tool({
  description: "Commit verified changes through SpecRepo autocommit after an explicit user request.",
  args: {
    summary: tool.schema.string().trim().min(1).describe("What changed and why"),
    userExplicitlyRequestedGitCommit: tool.schema.boolean().describe(
      "Must be true only when the user explicitly asked to commit/save the changes to Git",
    ),
  },
  async execute({ summary, userExplicitlyRequestedGitCommit }, context) {
    if (!userExplicitlyRequestedGitCommit) {
      throw new Error("Autocommit requires an explicit user request to commit the changes to Git.")
    }
    const python = process.platform === "win32" ? "python" : "python3"
    const result = await Bun.$`${python} ${script} ${summary}`
      .cwd(context.worktree || context.directory)
      .nothrow()
      .quiet()
    const output = `${result.stdout}${result.stderr}`.trim()

    if (result.exitCode !== 0) throw new Error(output)
    return output || "Autocommit completed successfully."
  },
})
