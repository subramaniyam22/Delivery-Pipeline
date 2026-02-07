'use client';

import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { getCurrentUser, getToken, isAuthenticated } from '@/lib/auth';
import { notificationsAPI } from '@/lib/api';
import NotificationToast from '@/components/NotificationToast';

interface Notification {
    id: string;
    message: string;
    type: 'info' | 'urgent';
    timestamp: Date;
    read: boolean;
    projectId?: string;
}

interface NotificationContextType {
    notifications: Notification[];
    unreadCount: number;
    isDrawerOpen: boolean;
    toggleDrawer: () => void;
    markAsRead: (id: string) => void;
    clearAll: () => void;
    refreshSignal: number;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
    const [notifications, setNotifications] = useState<Notification[]>([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [refreshSignal, setRefreshSignal] = useState(0);
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Only run on client side and if authenticated
        if (typeof window === 'undefined' || !isAuthenticated()) return;

        const user = getCurrentUser();
        if (!user?.id) return;
        const token = getToken();
        if (!token) return; // Avoid reconnect spam when token is missing/expired

        let baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        if (baseUrl.startsWith('https')) {
            baseUrl = baseUrl.replace(/^https/, 'wss');
        } else if (baseUrl.startsWith('http')) {
            baseUrl = baseUrl.replace(/^http/, 'ws');
        }

        const wsUrl = `${baseUrl}/ws/notifications/${user.id}?token=${encodeURIComponent(token)}`;
        console.log('Connecting to Global Notification WS:', wsUrl);

        // Other WS connections (no auth changes here):
        // - frontend/src/app/client-onboarding/[token]/page.tsx
        // - frontend/src/app/projects/[id]/page.tsx

        if (wsRef.current) {
            wsRef.current.close();
        }

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('Global Notification WS Connected');
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('Global WS Data:', data);

                if (data.type === 'REFRESH_PROJECTS') {
                    setRefreshSignal(prev => prev + 1);
                } else if (data.type === 'URGENT_ALERT' || data.type === 'ONBOARDING_SUBMISSION') {
                    // Trigger refresh to fetch from DB
                    setRefreshSignal(prev => prev + 1);

                    // Optional: Show toast immediately without waiting for DB fetch roundtrip
                    // This logic is handled by the `latestUrgent` effect which watches `notifications`
                    // But since we just triggered refresh, we rely on loadNotifications to update state
                    // To make it instant, we can append temporarily:
                    const newNotification: Notification = {
                        id: Date.now().toString(), // temporary ID
                        message: data.message,
                        type: 'urgent',
                        timestamp: new Date(),
                        read: false,
                        projectId: data.project_id
                    };
                    setNotifications(prev => [newNotification, ...prev]);
                    setUnreadCount(prev => prev + 1);
                }
            } catch (e) {
                console.error('Global WS Error', e);
            }
        };

        return () => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.close();
            }
        };
    }, []);

    const toggleDrawer = () => setIsDrawerOpen(prev => !prev);

    useEffect(() => {
        // Load Notifications from DB on mount
        if (isAuthenticated()) {
            loadNotifications();
        }
    }, [refreshSignal]); // Reload when signal changes (e.g. new WS message)

    const loadNotifications = async () => {
        try {
            const res = await notificationsAPI.list();
            // Map DB response to UI format
            const mapped = res.data.map((n: any) => ({
                id: n.id,
                message: n.message,
                type: n.type.toLowerCase().includes('urgent') ? 'urgent' : 'info',
                timestamp: new Date(n.created_at),
                read: n.is_read,
                projectId: n.project_id
            }));
            setNotifications(mapped);
            setUnreadCount(mapped.filter((n: any) => !n.read).length);
        } catch (err) {
            console.error('Failed to fetch notifications', err);
        }
    };

    const markAsRead = async (id: string) => {
        // Optimistic UI Update
        setNotifications(prev => prev.map(n =>
            n.id === id ? { ...n, read: true } : n
        ));
        setUnreadCount(prev => Math.max(0, prev - 1));

        try {
            await notificationsAPI.markRead(id);
        } catch (err) {
            console.error('Failed to mark read', err);
        }
    };

    const clearAll = async () => {
        setNotifications([]);
        setUnreadCount(0);
        try {
            await notificationsAPI.markAllRead();
        } catch (err) {
            console.error('Failed to mark all read', err);
        }
    };

    const latestUrgent = notifications.find(n => n.type === 'urgent' && !n.read && (Date.now() - new Date(n.timestamp).getTime() < 10000));
    const [visibleToast, setVisibleToast] = useState<{ message: string, id: string } | null>(null);

    useEffect(() => {
        if (latestUrgent) {
            setVisibleToast({ message: latestUrgent.message, id: latestUrgent.id });
        }
    }, [latestUrgent]);

    const handleToastClose = () => {
        if (visibleToast) {
            markAsRead(visibleToast.id);
            setVisibleToast(null);
        }
    };

    return (
        <NotificationContext.Provider value={{
            notifications,
            unreadCount,
            isDrawerOpen,
            toggleDrawer,
            markAsRead,
            clearAll,
            refreshSignal
        }}>
            {children}
            {visibleToast && (
                <div style={{ position: 'fixed', top: 20, right: 20, zIndex: 9999 }}>
                    {/* Dynamic import or direct usage if imported */}
                    <NotificationToast
                        message={visibleToast.message}
                        type="urgent"
                        onClose={handleToastClose}
                    />
                </div>
            )}
        </NotificationContext.Provider>
    );
}

export function useNotification() {
    const context = useContext(NotificationContext);
    if (context === undefined) {
        throw new Error('useNotification must be used within a NotificationProvider');
    }
    return context;
}
