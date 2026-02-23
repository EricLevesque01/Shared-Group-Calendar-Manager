"use client";
import { useState, useEffect } from "react";
import { useUser } from "@/context/UserContext";
import { useTheme } from "@/context/ThemeContext";
import { useRouter } from "next/navigation";
import { updateUser } from "@/lib/api";

export default function ProfilePage() {
    const { currentUser, setCurrentUser, refreshUsers } = useUser();
    const { theme, setTheme } = useTheme();
    const router = useRouter();

    const [displayName, setDisplayName] = useState("");
    const [timezone, setTimezone] = useState("");
    const [dndStart, setDndStart] = useState("");
    const [dndEnd, setDndEnd] = useState("");
    const [aliases, setAliases] = useState("");
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    useEffect(() => {
        if (!currentUser) {
            router.push("/");
            return;
        }
        setDisplayName(currentUser.display_name || "");
        setTimezone(currentUser.default_timezone || "UTC");
        setDndStart(currentUser.dnd_window_start_local || "");
        setDndEnd(currentUser.dnd_window_end_local || "");
        setAliases((currentUser.aliases || []).join(", "));
    }, [currentUser, router]);

    const handleSave = async (e) => {
        e.preventDefault();
        setSaving(true);
        setSaved(false);
        try {
            const updated = await updateUser(currentUser.user_id, {
                display_name: displayName,
                default_timezone: timezone,
                dnd_window_start_local: dndStart || null,
                dnd_window_end_local: dndEnd || null,
                aliases: aliases
                    .split(",")
                    .map((a) => a.trim())
                    .filter(Boolean),
            });
            setCurrentUser(updated);
            await refreshUsers();
            setSaved(true);
            setTimeout(() => setSaved(false), 3000);
        } catch (err) {
            alert(err.message);
        } finally {
            setSaving(false);
        }
    };

    if (!currentUser) return null;

    return (
        <div style={{ background: "var(--bg-secondary)", minHeight: "100vh" }}>
            <nav className="navbar" style={{ background: "var(--bg-primary)" }}>
                <div className="navbar__left">
                    <button className="navbar__hamburger" onClick={() => router.push("/calendar")}>
                        ←
                    </button>
                    <div className="navbar__logo">
                        <div className="navbar__logo-icon">GC</div>
                        Profile
                    </div>
                </div>
                <div className="navbar__right">
                    <button
                        className="navbar__avatar"
                        style={{ background: "linear-gradient(135deg, var(--accent-violet), var(--accent-cyan))" }}
                    >
                        {currentUser.display_name.charAt(0).toUpperCase()}
                    </button>
                </div>
            </nav>

            <div className="profile-page">
                <h1>Edit Profile</h1>
                <form onSubmit={handleSave}>
                    <div className="profile-section">
                        <h3 className="profile-section__title">Personal Info</h3>
                        <div className="profile-field">
                            <label className="input-label">Display Name</label>
                            <input
                                className="input"
                                value={displayName}
                                onChange={(e) => setDisplayName(e.target.value)}
                            />
                        </div>
                        <div className="profile-field">
                            <label className="input-label">Timezone</label>
                            <select
                                className="input"
                                value={timezone}
                                onChange={(e) => setTimezone(e.target.value)}
                            >
                                {Intl.supportedValuesOf("timeZone").map((tz) => (
                                    <option key={tz} value={tz}>{tz}</option>
                                ))}
                            </select>
                        </div>
                        <div className="profile-field">
                            <label className="input-label">Aliases (comma-separated)</label>
                            <input
                                className="input"
                                value={aliases}
                                onChange={(e) => setAliases(e.target.value)}
                                placeholder="e.g. Eric, E, EL"
                            />
                        </div>
                    </div>

                    <div className="profile-section">
                        <h3 className="profile-section__title">Quiet Hours (Do Not Disturb)</h3>
                        <p style={{ fontSize: 13, color: "var(--text-tertiary)", marginBottom: 12 }}>
                            Hard-constraint events cannot be scheduled during these hours in your local timezone.
                        </p>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                            <div className="profile-field">
                                <label className="input-label">Start Time</label>
                                <input
                                    className="input"
                                    type="time"
                                    value={dndStart}
                                    onChange={(e) => setDndStart(e.target.value)}
                                />
                            </div>
                            <div className="profile-field">
                                <label className="input-label">End Time</label>
                                <input
                                    className="input"
                                    type="time"
                                    value={dndEnd}
                                    onChange={(e) => setDndEnd(e.target.value)}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="profile-section">
                        <h3 className="profile-section__title">Appearance</h3>
                        <div className="profile-field">
                            <label className="input-label">Theme</label>
                            <div style={{ display: "flex", gap: 8 }}>
                                {[
                                    { value: "light", label: "Light" },
                                    { value: "dark", label: "Dark" },
                                    { value: "system", label: "System" },
                                ].map((t) => (
                                    <button
                                        key={t.value}
                                        type="button"
                                        className={`btn ${theme === t.value ? "btn-primary" : "btn-secondary"}`}
                                        onClick={() => setTheme(t.value)}
                                    >
                                        {t.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
                        <button type="submit" className="btn btn-primary btn-lg" disabled={saving}>
                            {saving ? "Saving..." : "Save Changes"}
                        </button>
                        <button
                            type="button"
                            className="btn btn-secondary btn-lg"
                            onClick={() => router.push("/calendar")}
                        >
                            Back to Calendar
                        </button>
                    </div>

                    {saved && (
                        <div className="toast toast-success" style={{ position: "relative", bottom: "auto", right: "auto", marginTop: 16 }}>
                            ✓ Profile saved successfully!
                        </div>
                    )}
                </form>
            </div>
        </div>
    );
}
