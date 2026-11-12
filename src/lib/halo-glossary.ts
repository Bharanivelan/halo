/**
 * Plain-language explanations shown next to every number, label and setting (D-41).
 * Written for a hotel owner, not an engineer. Keep each to two short sentences.
 */
export const GLOSSARY = {
  project: {
    title: "Project",
    text: "One project is one hotel. Halo keeps everything about that hotel together: the businesses around it, what the agent learned and your sales pipeline.",
  },
  radius: {
    title: "Search area",
    text: "How far from your hotel Halo looks for businesses. Companies closer to you are more likely to book rooms, so they score higher.",
  },
  prospect: {
    title: "Prospect",
    text: "A nearby business that could send you guests, meetings or events. Halo finds them on public maps and websites.",
  },
  tier: {
    title: "Hot, Warm, Cool",
    text: "A quick ranking of who to call first. Hot means a strong match with recent signs they need rooms or events. Cool means worth keeping an eye on.",
  },
  fit: {
    title: "Fit",
    text: "How well this business matches what your hotel sells: its industry, size and distance. It doesn't change from week to week.",
  },
  intent: {
    title: "Timing",
    text: "Whether something happened recently that suggests they need a hotel now, such as hiring, a new office or an event. Newer news counts more.",
  },
  confidence: {
    title: "Confidence",
    text: "How sure Halo is. It goes up when facts are backed by sources and down when information is missing. Low confidence means check it yourself.",
  },
  score: {
    title: "Score (0–100)",
    text: "Fit and timing combined into one number. Higher means call them sooner. You can see exactly which facts added points on each company's page.",
  },
  signal: {
    title: "Buying signal",
    text: "A recent event that hints they will need rooms or event space, like hiring, expanding, opening an office or hosting a conference. Each one links to where it was found.",
  },
  evidence: {
    title: "Evidence",
    text: "Every fact Halo shows comes with the web page it came from and the exact words it relied on. If Halo can't find proof, it says “Not verified” instead of guessing.",
  },
  agent: {
    title: "AI agent",
    text: "An assistant that works through steps on its own: find businesses, read their websites, look for signals, score them and draft an introduction. You review the results.",
  },
  run: {
    title: "Agent run",
    text: "One round of the agent's work for a hotel. It usually takes a few minutes. You can watch each step live and stop it at any time.",
  },
  budget: {
    title: "Spending cap",
    text: "The most the AI is allowed to spend on this run. If it reaches the cap it pauses and asks you before spending more.",
  },
  depth: {
    title: "Research depth",
    text: "Light reads fewer pages per company and costs less. Standard reads more and finds more signals.",
  },
  pitch: {
    title: "Draft pitch",
    text: "A first-draft introduction email written for this company, using only facts Halo verified. Always read and edit before sending.",
  },
  pipeline: {
    title: "Pipeline",
    text: "Deals you are working on, from first contact to won or lost. Drag a card to move it along.",
  },
  offerings: {
    title: "What you sell",
    text: "The kinds of business you want: corporate stays, meetings and events, long stays, or food and beverage. Halo looks for companies that need these.",
  },
} as const;

export type GlossaryKey = keyof typeof GLOSSARY;
