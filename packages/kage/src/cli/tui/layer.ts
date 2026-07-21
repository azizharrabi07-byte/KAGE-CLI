import { run as runTui, type TuiInput } from "@kage/tui"
import { Global } from "@kage/core/global"
import { AppNodeBuilder } from "@kage/core/effect/app-node-builder"
import { Effect } from "effect"

export function run(input: TuiInput) {
  return runTui(input).pipe(Effect.provide(AppNodeBuilder.build(Global.node)))
}
