import { Context } from "effect"
import type { InstanceContext } from "@/project/instance-context"
import type { WorkspaceV2 } from "@kage/core/workspace"

export const InstanceRef = Context.Reference<InstanceContext | undefined>("~kage/InstanceRef", {
  defaultValue: () => undefined,
})

export const WorkspaceRef = Context.Reference<WorkspaceV2.ID | undefined>("~kage/WorkspaceRef", {
  defaultValue: () => undefined,
})
