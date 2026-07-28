import { tool } from "@opencode-ai/plugin"
import { readFile, unlink } from "node:fs/promises"
import { join } from "node:path"

export default tool({
  description: "Stop the managed local 3D viewer UI server.",
  args: {},
  async execute(_args, context) {
    const root = context.worktree || context.directory
    const pidFile = join(root, ".opencode", "ui-server.pid")
    let record

    try {
      record = JSON.parse(await readFile(pidFile, "utf8"))
    } catch (error) {
      if (error?.code === "ENOENT") return "UI is not running."
      await unlink(pidFile).catch(() => {})
      return "Removed an invalid UI server PID record; no process was stopped."
    }

    try {
      process.kill(record.pid, 0)
    } catch {
      await unlink(pidFile).catch(() => {})
      return "Removed a stale UI server PID record; the UI was already stopped."
    }

    const command = await Bun.$`ps -p ${record.pid} -o command=`.nothrow().quiet()
    const commandText = `${command.stdout}`
    if (command.exitCode !== 0 || !commandText.includes("python-cad") || !commandText.includes("serve")) {
      await unlink(pidFile).catch(() => {})
      throw new Error("PID record did not identify a python-cad serve process; no process was stopped.")
    }

    process.kill(record.pid, "SIGTERM")
    await unlink(pidFile).catch(() => {})
    return `Stopped the managed UI process ${record.pid}.`
  },
})
