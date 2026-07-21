// @ts-nocheck

import { KAGE } from "@kage/core"
import { ReadTool } from "@kage/core/tools"

const kage = KAGE.make({})

kage.tool.add(ReadTool)

kage.tool.add({
  name: "bash",
  schema: {
    type: "object",
    properties: {
      command: {
        type: "string",
        description: "The command to run.",
      },
    },
    required: ["command"],
  },
  execute(input, ctx) {},
})

kage.auth.add({
  provider: "openai",
  type: "api",
  value: process.env.OPENAI_API_KEY,
})

kage.agent.add({
  name: "build",
  permissions: [],
  model: {
    id: "gpt-5-5",
    provider: "openai",
    variant: "xhigh",
  },
})

const sessionID = await kage.session.create({
  agent: "build",
})

kage.subscribe((event) => {
  console.log(event)
})

await kage.session.prompt({
  sessionID,
  text: "hey what is up",
})

await kage.session.prompt({
  sessionID,
  text: "what is up with this",
  files: [
    {
      mime: "image/png",
      uri: "data:image/png;base64,xxxx",
    },
  ],
})

await kage.session.wait()

console.log(await kage.session.messages(sessionID))
