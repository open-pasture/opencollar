// Chart labels for FenceGossip.tla.
export const title = "Fence gossip: beacon hint vs signed manifest (spec section 4)";

export const state = (v: any) => {
  const p = v.pending.kind === "hint" ? "waiting on a beacon's hint"
    : v.pending.kind === "real" ? "assembling a signed fence" : "idle";
  return `Fence ${v.active} in force, ${p}`;
};

const LABEL: Record<string, string> = {
  beacon: "hears a newer beacon",
  manifest: "gets a signed manifest",
  activate: "all fragments check out",
};
export const step = (_a: string, from: any, to: any) =>
  to.lastStep === from.lastStep && JSON.stringify(to) === JSON.stringify(from) ? null : LABEL[to.lastStep] ?? null;
