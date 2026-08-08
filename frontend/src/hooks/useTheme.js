import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "schemasense.theme";

function getStoredTheme() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "light" || stored === "dark" ? stored : null;
  } catch {
    return null;
  }
}

export function useTheme() {
  const [theme, setTheme] = useState(() => getStoredTheme());

  useEffect(() => {
    const root = document.documentElement;
    if (theme) {
      root.setAttribute("data-theme", theme);
    } else {
      root.removeAttribute("data-theme");
    }
    try {
      if (theme) {
        localStorage.setItem(STORAGE_KEY, theme);
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // localStorage unavailable — theme choice just won't persist
    }
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((current) => {
      if (current === "dark") return "light";
      if (current === "light") return "dark";
      // No explicit choice yet — flip away from whatever the system prefers.
      const systemPrefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
      return systemPrefersDark ? "light" : "dark";
    });
  }, []);

  return { theme, toggle };
}
