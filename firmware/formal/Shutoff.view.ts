// Chart labels for Shutoff.tla, in a caretaker's words.
export const title = "Collar welfare shut-off (main)";

export const state = (v: any) => {
  if (v.enforcementOff) return "Shut off: no cues";
  if (v.pulseCutoff) return "Outside, cues cut off";
  if (v.escaping) return "Outside, cueing";
  if (v.crossedOut) return "Escaped, not yet back inside";
  if (v.armed) return "Armed";
  return "Not armed";
};

export const group = (v: any) => (v.enforcementOff ? "off" : "on");
export const colors = { on: "blue", off: "orange" };

const LABEL: Record<string, string> = {
  inside: "fix inside",
  warning: "fix in warning zone",
  outside: "fix outside",
  boundary: "new fence",
  caretaker: "caretaker re-arms",
  day: "24 h window ends",
  reboot: "power cycle",
};
export const step = (_action: string, _from: any, to: any) => LABEL[to.lastStep] ?? to.lastStep;
