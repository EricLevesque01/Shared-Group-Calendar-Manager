"use client";
import { createContext, useContext, useState, useEffect } from "react";
import { getUsers } from "@/lib/api";

const UserContext = createContext({
    currentUser: null,
    setCurrentUser: () => { },
    users: [],
    refreshUsers: () => { },
});

export function UserProvider({ children }) {
    const [currentUser, setCurrentUser] = useState(null);
    const [users, setUsers] = useState([]);

    const refreshUsers = async () => {
        try {
            const data = await getUsers();
            setUsers(data);
        } catch (e) {
            console.error("Failed to fetch users:", e);
        }
    };

    useEffect(() => {
        refreshUsers();
        // Restore previous session user
        const savedId = localStorage.getItem("currentUserId");
        if (savedId) {
            getUsers().then((list) => {
                const found = list.find((u) => u.user_id === savedId);
                if (found) setCurrentUser(found);
            });
        }
    }, []);

    const selectUser = (user) => {
        setCurrentUser(user);
        localStorage.setItem("currentUserId", user.user_id);
    };

    return (
        <UserContext.Provider
            value={{ currentUser, setCurrentUser: selectUser, users, refreshUsers }}
        >
            {children}
        </UserContext.Provider>
    );
}

export const useUser = () => useContext(UserContext);
