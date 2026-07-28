import { tool } from "@opencode-ai/plugin"
import { readFile, unlink, writeFile } from "node:fs/promises"
import { join } from "node:path"

async function stopManagedViewer(pidFile) {
  try {
    const record = JSON.parse(await readFile(pidFile, "utf8"))
    process.kill(record.pid, 0)
    const command = await Bun.$`ps -p ${record.pid} -o command=`.nothrow().quiet()
    const commandText = `${command.stdout}`
    if (command.exitCode !== 0 || !commandText.includes("python-cad") || !commandText.includes("serve")) {
      throw new Error("Managed PID does not identify a python-cad serve process.")
    }
    process.kill(record.pid, "SIGTERM")
  } catch (error) {
    if (error?.code !== "ENOENT" && !["ESRCH"].includes(error?.code)) throw error
  } finally {
    await unlink(pidFile).catch(() => {})
  }
}

export default tool({
  description: "Upgrade the local project installation, clean it, rebuild it, and start the UI.",
  args: {
    port: tool.schema.number().default(8080).describe("HTTP port for the UI server"),
  },
  async execute({ port }, context) {
    const root = context.worktree || context.directory
    const bin = process.platform === "win32" ? join(root, ".venv", "Scripts") : join(root, ".venv", "bin")
    const pip = join(bin, process.platform === "win32" ? "pip.exe" : "pip")
    const cad = join(bin, process.platform === "win32" ? "python-cad.exe" : "python-cad")
    const pidFile = join(root, ".opencode", "ui-server.pid")

    await stopManagedViewer(pidFile)

    const install = await Bun.$`${pip} install --upgrade .`.cwd(root).nothrow().quiet()
    if (install.exitCode !== 0) throw new Error(`Upgrade failed:\n${install.stderr}`)

    const version = await Bun.$`${cad} --version`.cwd(root).nothrow().quiet()
    if (version.exitCode !== 0) throw new Error(`Version check failed:\n${version.stderr}`)

    const clean = await Bun.$`${cad} clean`.cwd(root).nothrow().quiet()
    if (clean.exitCode !== 0) throw new Error(`Clean failed:\n${clean.stderr}`)

    const proc = Bun.spawn([cad, "serve", "--build", "--port", String(port)], {
      cwd: root,
      stdout: "pipe",
      stderr: "pipe",
    })
    await writeFile(pidFile, JSON.stringify({ pid: proc.pid, port }) + "\n")

    const reader = proc.stdout.getReader()
    const decoder = new TextDecoder()
    let output = ""
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      output += decoder.decode(value, { stream: true })
      const match = output.match(/READY\s+(\S+)/)
      if (match) return `${version.stdout}`.trim() + `\nUI running at ${match[1]}`
    }

    await unlink(pidFile).catch(() => {})
    const errText = await new Response(proc.stderr).text()
    throw new Error(`Server failed after upgrade:\n${errText}`)
  },
})
