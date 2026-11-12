/** Remembers the last project opened on this device, for "Continue where you left off". */
const KEY = "halo.lastProject";

export function getLastProject(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setLastProject(id: string | null) {
  try {
    if (id) localStorage.setItem(KEY, id);
    else localStorage.removeItem(KEY);
  } catch {
    /* storage unavailable: the projects page falls back to the newest project */
  }
}
