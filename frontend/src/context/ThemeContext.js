"use client";
import { createContext, useContext, useEffect, useState } from "react";

const ThemeContext = createContext({
    theme: "system",
    setTheme: () => { },
    resolvedTheme: "light",
});

export function ThemeProvider({ children }) {
    const [theme, setThemeState] = useState("system");
    const [resolvedTheme, setResolved] = useState("light");

    useEffect(() => {
        const saved = localStorage.getItem("theme") || "system";
        setThemeState(saved);
        document.documentElement.setAttribute("data-theme", saved);
    }, []);

    useEffect(() => {
        const mq = window.matchMedia("(prefers-color-scheme: dark)");
        const update = () => {
            const resolved =
                theme === "system" ? (mq.matches ? "dark" : "light") : theme;
            setResolved(resolved);
        };
        update();
        mq.addEventListener("change", update);
        return () => mq.removeEventListener("change", update);
    }, [theme]);

    const setTheme = (t) => {
        setThemeState(t);
        localStorage.setItem("theme", t);
        document.documentElement.setAttribute("data-theme", t);
    };

    return (
        <ThemeContext.Provider value={{ theme, setTheme, resolvedTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

export const useTheme = () => useContext(ThemeContext);
