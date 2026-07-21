export * as PublicEventManifest from "./public-event-manifest"

import { Event } from "@kage/schema/event"
import { EventManifest } from "@kage/schema/event-manifest"

export const Definitions = EventManifest.ServerDefinitions
export const Latest = Event.latest(Definitions)
