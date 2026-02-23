"use client";
import { useState, useEffect, useMemo, useCallback } from "react";
import { useUser } from "@/context/UserContext";
import { useTheme } from "@/context/ThemeContext";
import { useRouter } from "next/navigation";
import {
    getEvents,
    getGroups,
    createEvent,
    updateEvent,
    cancelEvent,
    rsvp,
    createGroup,
    addMember,
    chatWithAgent,
} from "@/lib/api";

/* ── Helpers ── */
const HOURS = Array.from({ length: 18 }, (_, i) => i + 6); // 6am–11pm
const DAY_NAMES = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
const MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
];
const EVENT_COLORS = [
    "var(--event-1)", "var(--event-2)", "var(--event-3)",
    "var(--event-4)", "var(--event-5)", "var(--event-6)",
];

function getWeekStart(date) {
    const d = new Date(date);
    d.setDate(d.getDate() - d.getDay());
    d.setHours(0, 0, 0, 0);
    return d;
}

function isSameDay(a, b) {
    return (
        a.getFullYear() === b.getFullYear() &&
        a.getMonth() === b.getMonth() &&
        a.getDate() === b.getDate()
    );
}

function formatTime(date) {
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function formatHour(h) {
    if (h === 0) return "12 AM";
    if (h < 12) return `${h} AM`;
    if (h === 12) return "12 PM";
    return `${h - 12} PM`;
}

/* ════════════════════════════════════════════════════
   MAIN CALENDAR PAGE
   ════════════════════════════════════════════════════ */
export default function CalendarPage() {
    const { currentUser } = useUser();
    const { theme, setTheme, resolvedTheme } = useTheme();
    const router = useRouter();

    const [events, setEvents] = useState([]);
    const [groups, setGroups] = useState([]);
    const [currentDate, setCurrentDate] = useState(new Date());
    const [viewMode, setViewMode] = useState("week");
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [chatOpen, setChatOpen] = useState(true);
    const [showEventModal, setShowEventModal] = useState(false);
    const [showGroupModal, setShowGroupModal] = useState(false);
    const [selectedEvent, setSelectedEvent] = useState(null);
    const [eventModalDate, setEventModalDate] = useState(null);

    // Chat state
    const [chatMessages, setChatMessages] = useState([
        {
            role: "assistant",
            content: "Hey! I can help you schedule events, check availability, or manage your calendar. What would you like to do?",
        },
    ]);
    const [chatInput, setChatInput] = useState("");
    const [chatLoading, setChatLoading] = useState(false);

    // Redirect if no user selected
    useEffect(() => {
        if (!currentUser) router.push("/");
    }, [currentUser, router]);

    // Fetch data
    const loadData = useCallback(async () => {
        try {
            const [evts, grps] = await Promise.all([getEvents(), getGroups()]);
            setEvents(evts);
            setGroups(grps);
        } catch (e) {
            console.error("Failed to load data:", e);
        }
    }, []);

    useEffect(() => {
        if (currentUser) loadData();
    }, [currentUser, loadData]);

    // Week calculations
    const weekStart = useMemo(() => getWeekStart(currentDate), [currentDate]);
    const weekDays = useMemo(
        () => Array.from({ length: 7 }, (_, i) => {
            const d = new Date(weekStart);
            d.setDate(d.getDate() + i);
            return d;
        }),
        [weekStart]
    );

    const navigate = (dir) => {
        const d = new Date(currentDate);
        if (viewMode === "week") d.setDate(d.getDate() + dir * 7);
        else if (viewMode === "month") d.setMonth(d.getMonth() + dir);
        else d.setDate(d.getDate() + dir);
        setCurrentDate(d);
    };

    const goToday = () => setCurrentDate(new Date());

    // Get events for a specific day
    const getEventsForDay = (day) =>
        events.filter((evt) => {
            if (evt.status === "Cancelled") return false;
            const start = new Date(evt.start_time_utc);
            return isSameDay(start, day);
        });

    // Color for a group
    const groupColor = (groupId) => {
        const idx = groups.findIndex((g) => g.group_id === groupId);
        return EVENT_COLORS[idx % EVENT_COLORS.length] || EVENT_COLORS[0];
    };

    // Handle chat
    const sendChat = async () => {
        if (!chatInput.trim() || chatLoading) return;
        const msg = chatInput.trim();
        setChatInput("");
        setChatMessages((m) => [...m, { role: "user", content: msg }]);
        setChatLoading(true);
        try {
            const res = await chatWithAgent({
                message: msg,
                user_id: currentUser?.user_id,
                group_id: groups[0]?.group_id || null,
            });
            setChatMessages((m) => [
                ...m,
                { role: "assistant", content: res.response || res.message || "Done!" },
            ]);
            loadData(); // Refresh events after agent action
        } catch (e) {
            setChatMessages((m) => [
                ...m,
                {
                    role: "assistant",
                    content: `I'm not fully connected yet, but I'm here to help! Error: ${e.message}`,
                },
            ]);
        } finally {
            setChatLoading(false);
        }
    };

    // Theme toggle
    const cycleTheme = () => {
        const order = ["light", "dark", "system"];
        const next = order[(order.indexOf(theme) + 1) % order.length];
        setTheme(next);
    };

    const themeLabel = theme === "dark" ? "Dark" : theme === "light" ? "Light" : "Auto";

    if (!currentUser) return null;

    const dateLabel = `${MONTH_NAMES[currentDate.getMonth()]} ${currentDate.getFullYear()}`;

    return (
        <div className="app-layout">
            {/* ── LEFT SIDEBAR ── */}
            <aside className={`sidebar-left ${sidebarOpen ? "" : "collapsed"}`}>
                <div className="sidebar-left__header">
                    <button
                        className="create-event-btn"
                        onClick={() => {
                            setEventModalDate(null);
                            setSelectedEvent(null);
                            setShowEventModal(true);
                        }}
                    >
                        <span style={{ fontSize: 20 }}>+</span> Create Event
                    </button>
                </div>

                <MiniCalendar
                    currentDate={currentDate}
                    onDateSelect={(d) => setCurrentDate(d)}
                    events={events}
                />

                <div className="group-list">
                    <div className="group-list__header">
                        <span className="group-list__title">My Groups</span>
                        <button
                            className="group-list__add-btn"
                            onClick={() => setShowGroupModal(true)}
                            title="Create group"
                        >
                            +
                        </button>
                    </div>
                    {groups.map((g, i) => (
                        <div key={g.group_id} className="group-item">
                            <div
                                className="group-item__dot"
                                style={{ background: EVENT_COLORS[i % EVENT_COLORS.length] }}
                            />
                            <span className="group-item__name">{g.name}</span>
                            <div className="group-item__check checked">✓</div>
                        </div>
                    ))}
                    {groups.length === 0 && (
                        <p style={{ fontSize: 13, color: "var(--text-tertiary)", padding: "8px 0" }}>
                            No groups yet. Create one!
                        </p>
                    )}
                </div>
            </aside>

            {/* ── MAIN CONTENT ── */}
            <div className="main-content">
                {/* Navbar */}
                <nav className="navbar">
                    <div className="navbar__left">
                        <button className="navbar__hamburger" onClick={() => setSidebarOpen(!sidebarOpen)}>
                            ≡
                        </button>
                        <div className="navbar__logo">
                            <div className="navbar__logo-icon">GC</div>
                            Group Calendar
                        </div>
                    </div>

                    <div className="navbar__center">
                        <button className="navbar__today-btn" onClick={goToday}>
                            Today
                        </button>
                        <button className="navbar__nav-btn" onClick={() => navigate(-1)}>
                            ‹
                        </button>
                        <button className="navbar__nav-btn" onClick={() => navigate(1)}>
                            ›
                        </button>
                        <span className="navbar__date-label">{dateLabel}</span>
                        <div className="navbar__view-toggle">
                            {["day", "week", "month"].map((v) => (
                                <button
                                    key={v}
                                    className={`navbar__view-btn ${viewMode === v ? "active" : ""}`}
                                    onClick={() => setViewMode(v)}
                                >
                                    {v.charAt(0).toUpperCase() + v.slice(1)}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="navbar__right">
                        <button className="navbar__theme-btn" onClick={cycleTheme} title={`Theme: ${theme}`}>
                            {themeLabel}
                        </button>
                        <button
                            className="navbar__theme-btn"
                            onClick={() => setChatOpen(!chatOpen)}
                            title="Toggle AI Chat"
                        >
                            Chat
                        </button>
                        <button
                            className="navbar__avatar"
                            onClick={() => router.push("/profile")}
                            title="Profile"
                        >
                            {currentUser.display_name.charAt(0).toUpperCase()}
                        </button>
                    </div>
                </nav>

                {/* Photo Banner */}
                <PhotoBanner />

                {/* Calendar Grid */}
                <div className="calendar-area">
                    {viewMode === "week" && (
                        <WeekView
                            weekDays={weekDays}
                            events={events}
                            groupColor={groupColor}
                            onEventClick={(evt) => setSelectedEvent(evt)}
                            onSlotClick={(date, hour) => {
                                const d = new Date(date);
                                d.setHours(hour, 0, 0, 0);
                                setEventModalDate(d);
                                setSelectedEvent(null);
                                setShowEventModal(true);
                            }}
                        />
                    )}
                    {viewMode === "month" && (
                        <MonthView
                            currentDate={currentDate}
                            events={events}
                            groupColor={groupColor}
                            onEventClick={(evt) => setSelectedEvent(evt)}
                            onDateClick={(date) => {
                                setCurrentDate(date);
                                setViewMode("day");
                            }}
                        />
                    )}
                    {viewMode === "day" && (
                        <DayView
                            date={currentDate}
                            events={events}
                            groupColor={groupColor}
                            onEventClick={(evt) => setSelectedEvent(evt)}
                            onSlotClick={(hour) => {
                                const d = new Date(currentDate);
                                d.setHours(hour, 0, 0, 0);
                                setEventModalDate(d);
                                setSelectedEvent(null);
                                setShowEventModal(true);
                            }}
                        />
                    )}
                </div>
            </div>

            {/* ── RIGHT SIDEBAR (chat) ── */}
            <aside className={`sidebar-right ${chatOpen ? "" : "collapsed"}`}>
                <div className="sidebar-right__header">
                    <h3>AI Assistant</h3>
                    <button className="btn-ghost btn-icon" onClick={() => setChatOpen(false)}>
                        ×
                    </button>
                </div>
                <ChatPanel
                    messages={chatMessages}
                    input={chatInput}
                    onInputChange={setChatInput}
                    onSend={sendChat}
                    loading={chatLoading}
                />
            </aside>

            {/* ── Modals ── */}
            {showEventModal && (
                <EventModal
                    onClose={() => setShowEventModal(false)}
                    onSave={async (data) => {
                        try {
                            await createEvent(data);
                            await loadData();
                            setShowEventModal(false);
                        } catch (e) {
                            alert(e.message);
                        }
                    }}
                    groups={groups}
                    currentUser={currentUser}
                    initialDate={eventModalDate}
                    users={[]}
                />
            )}

            {showGroupModal && (
                <GroupModal
                    onClose={() => setShowGroupModal(false)}
                    onSave={async (data) => {
                        try {
                            await createGroup(data);
                            await loadData();
                            setShowGroupModal(false);
                        } catch (e) {
                            alert(e.message);
                        }
                    }}
                    currentUser={currentUser}
                />
            )}

            {selectedEvent && (
                <EventDetailModal
                    event={selectedEvent}
                    currentUser={currentUser}
                    groups={groups}
                    groupColor={groupColor}
                    onClose={() => setSelectedEvent(null)}
                    onUpdate={async (id, data) => {
                        try {
                            await updateEvent(id, currentUser.user_id, data);
                            await loadData();
                            setSelectedEvent(null);
                        } catch (e) {
                            alert(e.message);
                        }
                    }}
                    onCancel={async (id, data) => {
                        try {
                            await cancelEvent(id, data);
                            await loadData();
                            setSelectedEvent(null);
                        } catch (e) {
                            alert(e.message);
                        }
                    }}
                    onRsvp={async (data) => {
                        try {
                            await rsvp(data);
                            await loadData();
                        } catch (e) {
                            alert(e.message);
                        }
                    }}
                />
            )}
        </div>
    );
}

/* ════════════════════════════════
   MINI CALENDAR
   ════════════════════════════════ */
function MiniCalendar({ currentDate, onDateSelect, events }) {
    const [viewDate, setViewDate] = useState(new Date(currentDate));

    const year = viewDate.getFullYear();
    const month = viewDate.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const daysInPrev = new Date(year, month, 0).getDate();
    const today = new Date();

    const days = [];
    // Previous month padding
    for (let i = firstDay - 1; i >= 0; i--) {
        days.push({ date: new Date(year, month - 1, daysInPrev - i), otherMonth: true });
    }
    // Current month
    for (let i = 1; i <= daysInMonth; i++) {
        days.push({ date: new Date(year, month, i), otherMonth: false });
    }
    // Next month padding
    while (days.length % 7 !== 0) {
        days.push({ date: new Date(year, month + 1, days.length - firstDay - daysInMonth + 1), otherMonth: true });
    }

    return (
        <div className="mini-calendar">
            <div className="mini-calendar__header">
                <span className="mini-calendar__title">
                    {MONTH_NAMES[month]} {year}
                </span>
                <div className="mini-calendar__nav">
                    <button onClick={() => setViewDate(new Date(year, month - 1, 1))}>‹</button>
                    <button onClick={() => setViewDate(new Date(year, month + 1, 1))}>›</button>
                </div>
            </div>
            <div className="mini-calendar__grid">
                {["S", "M", "T", "W", "T", "F", "S"].map((d, i) => (
                    <div key={i} className="mini-calendar__day-header">{d}</div>
                ))}
                {days.map(({ date, otherMonth }, i) => (
                    <button
                        key={i}
                        className={`mini-calendar__day ${otherMonth ? "other-month" : ""} ${isSameDay(date, today) ? "today" : ""} ${isSameDay(date, currentDate) ? "selected" : ""}`}
                        onClick={() => onDateSelect(date)}
                    >
                        {date.getDate()}
                    </button>
                ))}
            </div>
        </div>
    );
}

/* ════════════════════════════════
   WEEK VIEW
   ════════════════════════════════ */
function WeekView({ weekDays, events, groupColor, onEventClick, onSlotClick }) {
    const today = new Date();
    const now = new Date();

    return (
        <div className="week-view">
            {/* Time Gutter */}
            <div className="week-view__time-gutter">
                <div style={{ height: 52 }} /> {/* Header spacer */}
                {HOURS.map((h) => (
                    <div key={h} className="week-view__time-slot">
                        {formatHour(h)}
                    </div>
                ))}
            </div>

            {/* Day Columns */}
            <div className="week-view__columns">
                {weekDays.map((day, di) => {
                    const dayEvents = events.filter((evt) => {
                        if (evt.status === "Cancelled") return false;
                        const start = new Date(evt.start_time_utc);
                        return isSameDay(start, day);
                    });

                    return (
                        <div key={di} className="week-view__column">
                            {/* Day Header */}
                            <div className="week-view__day-header">
                                <div className="week-view__day-name">{DAY_NAMES[day.getDay()]}</div>
                                <div className={`week-view__day-number ${isSameDay(day, today) ? "today" : ""}`}>
                                    {day.getDate()}
                                </div>
                            </div>

                            {/* Hour slots */}
                            {HOURS.map((h) => (
                                <div
                                    key={h}
                                    className="week-view__hour-line"
                                    onClick={() => onSlotClick(day, h)}
                                    style={{ cursor: "pointer" }}
                                />
                            ))}

                            {/* Now line */}
                            {isSameDay(day, today) && (
                                <div
                                    className="now-line"
                                    style={{
                                        top: `${52 + (now.getHours() - 6) * 60 + now.getMinutes()}px`,
                                    }}
                                />
                            )}

                            {/* Events */}
                            {dayEvents.map((evt) => {
                                const start = new Date(evt.start_time_utc);
                                const end = new Date(evt.end_time_utc);
                                const topPx = 52 + (start.getHours() - 6) * 60 + start.getMinutes();
                                const heightPx = Math.max(
                                    24,
                                    ((end - start) / (1000 * 60)) // minutes
                                );
                                const color = groupColor(evt.group_id);

                                return (
                                    <div
                                        key={evt.event_id}
                                        className="week-view__event"
                                        style={{
                                            top: `${topPx}px`,
                                            height: `${heightPx}px`,
                                            background: color,
                                        }}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onEventClick(evt);
                                        }}
                                    >
                                        <div className="week-view__event-title">{evt.title}</div>
                                        <div className="week-view__event-time">
                                            {formatTime(start)} – {formatTime(end)}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

/* ════════════════════════════════
   CHAT PANEL
   ════════════════════════════════ */
function ChatPanel({ messages, input, onInputChange, onSend, loading }) {
    return (
        <div className="chat-panel">
            <div className="chat-quick-actions">
                {["Schedule a meeting", "Check availability", "Summarize week"].map((a) => (
                    <button
                        key={a}
                        className="chat-quick-action"
                        onClick={() => {
                            onInputChange(a);
                        }}
                    >
                        {a}
                    </button>
                ))}
            </div>
            <div className="chat-messages">
                {messages.map((m, i) => (
                    <div key={i} className={`chat-message ${m.role}`}>
                        {m.content}
                    </div>
                ))}
                {loading && (
                    <div className="chat-message assistant">
                        <div className="spinner" style={{ width: 16, height: 16 }} />
                    </div>
                )}
            </div>
            <div className="chat-input-area">
                <input
                    value={input}
                    onChange={(e) => onInputChange(e.target.value)}
                    placeholder="Ask the AI assistant..."
                    onKeyDown={(e) => e.key === "Enter" && onSend()}
                />
                <button className="chat-send-btn" onClick={onSend} disabled={loading || !input.trim()}>
                    ↑
                </button>
            </div>
        </div>
    );
}

/* ════════════════════════════════
   PHOTO BANNER
   ════════════════════════════════ */
function PhotoBanner() {
    return (
        <div className="photo-banner">
            <div className="photo-banner__overlay" />
            <button className="photo-banner__edit">Edit Photos</button>
        </div>
    );
}

/* ════════════════════════════════
   MONTH VIEW
   ════════════════════════════════ */
function MonthView({ currentDate, events, groupColor, onEventClick, onDateClick }) {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const daysInPrev = new Date(year, month, 0).getDate();
    const today = new Date();

    const cells = [];
    for (let i = firstDay - 1; i >= 0; i--) {
        cells.push({ date: new Date(year, month - 1, daysInPrev - i), otherMonth: true });
    }
    for (let i = 1; i <= daysInMonth; i++) {
        cells.push({ date: new Date(year, month, i), otherMonth: false });
    }
    while (cells.length % 7 !== 0) {
        cells.push({ date: new Date(year, month + 1, cells.length - firstDay - daysInMonth + 1), otherMonth: true });
    }

    const getEventsForDay = (day) =>
        events.filter((evt) => {
            if (evt.status === "Cancelled") return false;
            const s = new Date(evt.start_time_utc);
            return isSameDay(s, day);
        });

    return (
        <div className="month-view">
            <div className="month-view__header">
                {DAY_NAMES.map((d) => (
                    <div key={d} className="month-view__day-header">{d}</div>
                ))}
            </div>
            <div className="month-view__grid">
                {cells.map(({ date, otherMonth }, i) => {
                    const dayEvents = getEventsForDay(date);
                    const isToday = isSameDay(date, today);
                    return (
                        <div
                            key={i}
                            className={`month-view__cell ${otherMonth ? "other-month" : ""}`}
                            onClick={() => onDateClick(date)}
                        >
                            <span className={`month-view__date ${isToday ? "today" : ""}`}>
                                {date.getDate()}
                            </span>
                            <div className="month-view__events">
                                {dayEvents.slice(0, 3).map((evt) => (
                                    <div
                                        key={evt.event_id}
                                        className="month-view__event-chip"
                                        style={{ background: groupColor(evt.group_id) }}
                                        onClick={(e) => { e.stopPropagation(); onEventClick(evt); }}
                                    >
                                        {evt.title}
                                    </div>
                                ))}
                                {dayEvents.length > 3 && (
                                    <div className="month-view__more">
                                        +{dayEvents.length - 3} more
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

/* ════════════════════════════════
   DAY VIEW
   ════════════════════════════════ */
function DayView({ date, events, groupColor, onEventClick, onSlotClick }) {
    const today = new Date();
    const now = new Date();
    const isToday = isSameDay(date, today);

    const dayEvents = events.filter((evt) => {
        if (evt.status === "Cancelled") return false;
        const s = new Date(evt.start_time_utc);
        return isSameDay(s, date);
    });

    return (
        <div className="day-view">
            <div className="day-view__header">
                <span className="day-view__day-name">{DAY_NAMES[date.getDay()]}</span>
                <span className={`day-view__day-number ${isToday ? "today" : ""}`}>
                    {date.getDate()}
                </span>
            </div>
            <div className="day-view__body">
                <div className="day-view__gutter">
                    {HOURS.map((h) => (
                        <div key={h} className="day-view__time-label">{formatHour(h)}</div>
                    ))}
                </div>
                <div className="day-view__column">
                    {HOURS.map((h) => (
                        <div
                            key={h}
                            className="day-view__hour-slot"
                            onClick={() => onSlotClick(h)}
                        />
                    ))}
                    {isToday && (
                        <div
                            className="now-line"
                            style={{ top: `${(now.getHours() - 6) * 60 + now.getMinutes()}px` }}
                        />
                    )}
                    {dayEvents.map((evt) => {
                        const start = new Date(evt.start_time_utc);
                        const end = new Date(evt.end_time_utc);
                        const topPx = (start.getHours() - 6) * 60 + start.getMinutes();
                        const heightPx = Math.max(24, (end - start) / (1000 * 60));
                        return (
                            <div
                                key={evt.event_id}
                                className="day-view__event"
                                style={{ top: `${topPx}px`, height: `${heightPx}px`, background: groupColor(evt.group_id) }}
                                onClick={(e) => { e.stopPropagation(); onEventClick(evt); }}
                            >
                                <div className="week-view__event-title">{evt.title}</div>
                                <div className="week-view__event-time">
                                    {formatTime(start)} – {formatTime(end)}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}

/* ════════════════════════════════
   EVENT MODAL (Create)
   ════════════════════════════════ */
function EventModal({ onClose, onSave, groups, currentUser, initialDate }) {
    const [title, setTitle] = useState("");
    const [groupId, setGroupId] = useState(groups[0]?.group_id || "");
    const [startDate, setStartDate] = useState(
        initialDate
            ? new Date(initialDate).toISOString().slice(0, 16)
            : new Date(Date.now() + 86400000).toISOString().slice(0, 16)
    );
    const [endDate, setEndDate] = useState(
        initialDate
            ? new Date(new Date(initialDate).getTime() + 3600000).toISOString().slice(0, 16)
            : new Date(Date.now() + 86400000 + 3600000).toISOString().slice(0, 16)
    );
    const [constraint, setConstraint] = useState("Soft");
    const [saving, setSaving] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!title.trim() || !groupId) return;
        setSaving(true);
        await onSave({
            group_id: groupId,
            title: title.trim(),
            start_time_utc: new Date(startDate).toISOString(),
            end_time_utc: new Date(endDate).toISOString(),
            organizer_id: currentUser.user_id,
            constraint_level: constraint,
            attendee_ids: [],
        });
        setSaving(false);
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>Create Event</h2>
                    <button className="btn-ghost btn-icon" onClick={onClose}>×</button>
                </div>
                <form onSubmit={handleSubmit}>
                    <div className="profile-field">
                        <label className="input-label">Title</label>
                        <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Event title" autoFocus />
                    </div>
                    <div className="profile-field">
                        <label className="input-label">Group</label>
                        <select className="input" value={groupId} onChange={(e) => setGroupId(e.target.value)}>
                            {groups.map((g) => (
                                <option key={g.group_id} value={g.group_id}>{g.name}</option>
                            ))}
                        </select>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                        <div className="profile-field">
                            <label className="input-label">Start</label>
                            <input className="input" type="datetime-local" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                        </div>
                        <div className="profile-field">
                            <label className="input-label">End</label>
                            <input className="input" type="datetime-local" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                        </div>
                    </div>
                    <div className="profile-field">
                        <label className="input-label">Constraint Level</label>
                        <div style={{ display: "flex", gap: 8 }}>
                            {["Soft", "Hard"].map((c) => (
                                <button
                                    key={c}
                                    type="button"
                                    className={`btn ${constraint === c ? "btn-primary" : "btn-secondary"} btn-sm`}
                                    onClick={() => setConstraint(c)}
                                >
                                    {c}
                                </button>
                            ))}
                        </div>
                        <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 4 }}>
                            {constraint === "Hard"
                                ? "Hard events cannot overlap with other hard events or DND windows."
                                : "Soft events can overlap with other events."}
                        </p>
                    </div>
                    <div className="modal-footer">
                        <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
                        <button type="submit" className="btn btn-primary" disabled={saving}>
                            {saving ? "Saving..." : "Create Event"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

/* ════════════════════════════════
   EVENT DETAIL MODAL
   ════════════════════════════════ */
function EventDetailModal({ event, currentUser, groups, groupColor, onClose, onUpdate, onCancel, onRsvp }) {
    const start = new Date(event.start_time_utc);
    const end = new Date(event.end_time_utc);
    const isOrganizer = event.organizer_id === currentUser?.user_id;
    const group = groups.find((g) => g.group_id === event.group_id);
    const myAttendee = event.attendees?.find((a) => a.user_id === currentUser?.user_id);

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 480 }}>
                <div className="modal-header">
                    <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span
                            style={{
                                width: 12, height: 12, borderRadius: "50%",
                                background: groupColor(event.group_id), display: "inline-block",
                            }}
                        />
                        {event.title}
                    </h2>
                    <button className="btn-ghost btn-icon" onClick={onClose}>×</button>
                </div>

                <div className="event-detail__meta">
                    <div className="event-detail__meta-row">
                        <span className="event-detail__meta-icon">Time</span>
                        {start.toLocaleDateString()} · {formatTime(start)} – {formatTime(end)}
                    </div>
                    <div className="event-detail__meta-row">
                        <span className="event-detail__meta-icon">Group</span>
                        {group?.name || "Unknown group"}
                    </div>
                    <div className="event-detail__meta-row">
                        <span className="event-detail__meta-icon">Type</span>
                        <span className={`badge ${event.constraint_level === "Hard" ? "badge-hard" : "badge-soft"}`}>
                            {event.constraint_level}
                        </span>
                        <span className={`badge badge-${event.status?.toLowerCase()}`} style={{ marginLeft: 4 }}>
                            {event.status}
                        </span>
                    </div>
                </div>

                {/* RSVP */}
                {myAttendee && (
                    <div style={{ marginBottom: 16 }}>
                        <label className="input-label">Your RSVP</label>
                        <div className="rsvp-buttons">
                            {["going", "maybe", "declined"].map((status) => (
                                <button
                                    key={status}
                                    className={`rsvp-btn ${myAttendee.rsvp_status === status ? `active-${status}` : ""}`}
                                    onClick={() =>
                                        onRsvp({
                                            event_id: event.event_id,
                                            user_id: currentUser.user_id,
                                            rsvp_status: status,
                                        })
                                    }
                                >
                                    {status === "going" ? "✓ Going" : status === "maybe" ? "? Maybe" : "✕ Decline"}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Attendees */}
                {event.attendees?.length > 0 && (
                    <div className="event-detail__attendees">
                        <label className="input-label">Attendees</label>
                        {event.attendees.map((a) => (
                            <div key={a.user_id} className="event-detail__attendee">
                                <span className="event-detail__attendee-name">
                                    {a.user_id === event.organizer_id ? "(organizer) " : ""}
                                    {a.display_name || a.user_id.slice(0, 8)}
                                </span>
                                <span className={`badge badge-${a.rsvp_status}`}>{a.rsvp_status}</span>
                            </div>
                        ))}
                    </div>
                )}

                {/* Actions */}
                <div className="modal-footer">
                    {isOrganizer ? (
                        <>
                            <button
                                className="btn btn-danger btn-sm"
                                onClick={() => {
                                    if (confirm("Cancel this event?")) {
                                        onCancel(event.event_id, {
                                            cancelled_by_user_id: currentUser.user_id,
                                            cancel_reason: "Cancelled by organizer",
                                            version: event.version,
                                        });
                                    }
                                }}
                            >
                                Cancel Event
                            </button>
                            <button className="btn btn-secondary btn-sm" onClick={onClose}>
                                Close
                            </button>
                        </>
                    ) : (
                        <button className="btn btn-secondary btn-sm" onClick={onClose}>
                            Close
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

/* ════════════════════════════════
   GROUP MODAL
   ════════════════════════════════ */
function GroupModal({ onClose, onSave, currentUser }) {
    const [name, setName] = useState("");
    const [saving, setSaving] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!name.trim()) return;
        setSaving(true);
        await onSave({ name: name.trim(), created_by: currentUser.user_id });
        setSaving(false);
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 400 }}>
                <div className="modal-header">
                    <h2>Create Group</h2>
                    <button className="btn-ghost btn-icon" onClick={onClose}>×</button>
                </div>
                <form onSubmit={handleSubmit}>
                    <div className="profile-field">
                        <label className="input-label">Group Name</label>
                        <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. College Friends" autoFocus />
                    </div>
                    <div className="modal-footer">
                        <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
                        <button type="submit" className="btn btn-primary" disabled={saving}>
                            {saving ? "Creating..." : "Create Group"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
