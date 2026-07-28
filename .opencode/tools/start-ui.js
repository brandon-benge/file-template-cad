import { tool } from "@opencode-ai/plugin"
import { readFile, unlink, writeFile } from "node:fs/promises"
import { join } from "node:path"

async function liveManagedPid(pidFile) {
  try {
    const record = JSON.parse(await readFile(pidFile, "utf8"))
    process.kill(record.pid, 0)
    const command = await Bun.$`ps -p ${record.pid} -o command=`.nothrow().quiet()
    const commandText = `${command.stdout}`
    if (command.exitCode !== 0 || !commandText.includes("python-cad") || !commandText.includes("serve")) {
      await unlink(pidFile).catch(() => {})
      return null
    }
    return record.pid
  } catch (error) {
    if (error?.code !== "ENOENT") await unlink(pidFile).catch(() => {})
    return null
  }
}

export default tool({
  description: "Build and start the local 3D viewer UI server.",
  args: {
    port: tool.schema.number().default(8080).describe("HTTP port for the UI server"),
    build: tool.schema.boolean().default(true).describe("Run python-cad build first"),
  },
  async execute({ port, build }, context) {
    const root = context.worktree || context.directory
    const cad = process.platform === "win32"
      ? join(root, ".venv", "Scripts", "python-cad.exe")
      : join(root, ".venv", "bin", "python-cad")
    const pidFile = join(root, ".opencode", "ui-server.pid")
    const runningPid = await liveManagedPid(pidFile)
    if (runningPid) return `UI is already running as managed process ${runningPid}.`

    if (build) {
      const b = await Bun.$`${cad} build --project-root ${root}`.nothrow().quiet()
      if (b.exitCode !== 0) throw new Error(`Build failed:\n${b.stderr}`)
    }

    const proc = Bun.spawn([
      cad, "serve",
      "--project-root", root,
      "--port", String(port),
    ], { stdout: "pipe", stderr: "pipe" })
    await writeFile(pidFile, JSON.stringify({ pid: proc.pid, port }) + "\n")

    const reader = proc.stdout.getReader()
    const decoder = new TextDecoder()
    let output = ""
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      output += decoder.decode(value, { stream: true })
      const match = output.match(/READY\s+(\S+)/)
      if (match) return `UI running at ${match[1]}`
    }

    await unlink(pidFile).catch(() => {})
    const errText = await new Response(proc.stderr).text()
    throw new Error(`Server failed:\n${errText}`)
  },
})
