'use client';

import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { getCurrentUser, isAuthenticated } from '@/lib/auth';

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
        const saved = localStorage.getItem('notifications');
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                const restored = parsed.map((n: any) => ({ ...n, timestamp: new Date(n.timestamp) }));
                setNotifications(restored);
                setUnreadCount(restored.filter((n: any) => !n.read).length);
            } catch (e) {
                console.error('Failed to load notifications', e);
            }
        }
    }, []);

    useEffect(() => {
        localStorage.setItem('notifications', JSON.stringify(notifications));
        setUnreadCount(notifications.filter(n => !n.read).length);
    }, [notifications]);

    useEffect(() => {
        // Only run on client side and if authenticated
        if (typeof window === 'undefined' || !isAuthenticated()) return;

        const user = getCurrentUser();
        if (!user?.id) return;

        let baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        if (baseUrl.startsWith('https')) {
            baseUrl = baseUrl.replace(/^https/, 'wss');
        } else if (baseUrl.startsWith('http')) {
            baseUrl = baseUrl.replace(/^http/, 'ws');
        }

        const wsUrl = `${baseUrl}/api/ai/ws/notifications/${user.id}`;
        console.log('Connecting to Global Notification WS:', wsUrl);

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

                if (data.type === 'REFRESH_PROJECTS') {
                    console.log('Received Refresh Signal');
                    setRefreshSignal(prev => prev + 1);
                } else if (data.type === 'URGENT_ALERT') {
                    console.log('Received Urgent Alert');
                    const newNotification: Notification = {
                        id: Date.now().toString(),
                        message: data.message,
                        type: 'urgent',
                        timestamp: new Date(),
                        read: false,
                        projectId: data.project_id
                    };

                    setNotifications(prev => [newNotification, ...prev]);
                    // Persistent audio or visual cue could be added here
                    setRefreshSignal(prev => prev + 1);
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

    const markAsRead = (id: string) => {
        setNotifications(prev => prev.map(n =>
            n.id === id ? { ...n, read: true } : n
        ));
    };

    const clearAll = () => {
        setNotifications([]);
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
