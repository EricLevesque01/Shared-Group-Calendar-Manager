"use client";
import { useState } from "react";
import { useUser } from "@/context/UserContext";
import { useRouter } from "next/navigation";
import { createUser } from "@/lib/api";

export default function LandingPage() {
  const { users, setCurrentUser, refreshUsers } = useUser();
  const router = useRouter();
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone
  );
  const [loading, setLoading] = useState(false);

  const selectUser = (user) => {
    setCurrentUser(user);
    router.push("/calendar");
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    try {
      const user = await createUser({
        display_name: name.trim(),
        default_timezone: timezone,
      });
      await refreshUsers();
      selectUser(user);
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="landing">
      <div className="landing__card">
        <div className="navbar__logo-icon" style={{ width: 48, height: 48, fontSize: 18, margin: "0 auto 16px", borderRadius: 12 }}>
          GC
        </div>
        <h1 className="landing__title">Group Calendar</h1>
        <p className="landing__subtitle">
          AI-powered shared scheduling for your friend group
        </p>

        {users.length > 0 && (
          <div className="landing__user-list">
            {users.map((u) => (
              <button
                key={u.user_id}
                className="landing__user-btn"
                onClick={() => selectUser(u)}
              >
                <div className="landing__user-avatar">
                  {u.display_name.charAt(0).toUpperCase()}
                </div>
                <div>
                  <div style={{ fontWeight: 600 }}>{u.display_name}</div>
                  <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                    {u.default_timezone}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        <div className="landing__divider">
          {users.length > 0 ? "or create a new user" : "Get started"}
        </div>

        {!showCreate && users.length > 0 ? (
          <button
            className="btn btn-primary btn-lg"
            style={{ width: "100%" }}
            onClick={() => setShowCreate(true)}
          >
            + Create New User
          </button>
        ) : (
          <form onSubmit={handleCreate}>
            <div className="profile-field">
              <label className="input-label">Display Name</label>
              <input
                className="input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                autoFocus
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
                  <option key={tz} value={tz}>
                    {tz}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              className="btn btn-primary btn-lg"
              style={{ width: "100%", marginTop: 8 }}
              disabled={loading}
            >
              {loading ? "Creating..." : "Create & Continue"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
