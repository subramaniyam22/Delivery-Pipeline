'use client';

import { useEffect, useState } from 'react';
import { policiesAPI } from '@/lib/api';
import Navigation from '@/components/Navigation';
import RequireCapability from '@/components/RequireCapability';
import PageHeader from '@/components/PageHeader';

type PolicyValue = {
    reminder_cadence_hours?: number;
    max_reminders?: number;
    idle_minutes?: number;
    build_retry_cap?: number;
    defect_validation_cycle_cap?: number;
    pass_threshold_percent?: number;
    lighthouse_thresholds_json?: Record<string, number>;
    axe_policy_json?: Record<string, unknown>;
    proof_pack_soft_mb?: number;
    proof_pack_hard_mb?: number;
};

export default function AdminPoliciesPage() {
    const [value, setValue] = useState<PolicyValue>({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');

    useEffect(() => {
        policiesAPI.get()
            .then((r) => {
                const v = r.data?.value_json;
                if (v && typeof v === 'object') setValue(v as PolicyValue);
            })
            .catch(() => setValue({}))
            .finally(() => setLoading(false));
    }, []);

    const handleSave = async () => {
        setSaving(true);
        setMessage('');
        try {
            await policiesAPI.put(value);
            setMessage('Policies saved.');
        } catch (e: unknown) {
            setMessage((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Save failed');
        } finally {
            setSaving(false);
        }
    };

    const update = (key: keyof PolicyValue, val: number | Record<string, unknown> | undefined) => {
        setValue((prev) => ({ ...prev, [key]: val }));
    };

    if (loading) {
        return (
            <>
                <Navigation />
                <main className="p-6"><p>Loading policies...</p></main>
            </>
        );
    }

    return (
        <RequireCapability cap="configure_system">
            <Navigation />
            <main className="p-6 max-w-2xl">
                <PageHeader title="Settings → Policies" />
                <p className="text-sm text-gray-600 mb-4">
                    Configure pipeline thresholds and limits. These override defaults.
                </p>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-1">Reminder cadence (hours)</label>
                        <input
                            type="number"
                            min={1}
                            value={value.reminder_cadence_hours ?? 24}
                            onChange={(e) => update('reminder_cadence_hours', parseInt(e.target.value, 10) || 24)}
                            className="border rounded px-2 py-1 w-24"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">Max reminders</label>
                        <input
                            type="number"
                            min={1}
                            max={20}
                            value={value.max_reminders ?? 10}
                            onChange={(e) => update('max_reminders', parseInt(e.target.value, 10) || 10)}
                            className="border rounded px-2 py-1 w-24"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">Idle minutes</label>
                        <input
                            type="number"
                            min={5}
                            value={value.idle_minutes ?? 30}
                            onChange={(e) => update('idle_minutes', parseInt(e.target.value, 10) || 30)}
                            className="border rounded px-2 py-1 w-24"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">Build retry cap</label>
                        <input
                            type="number"
                            min={1}
                            value={value.build_retry_cap ?? 3}
                            onChange={(e) => update('build_retry_cap', parseInt(e.target.value, 10) || 3)}
                            className="border rounded px-2 py-1 w-24"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">Defect validation cycle cap</label>
                        <input
                            type="number"
                            min={1}
                            value={value.defect_validation_cycle_cap ?? 5}
                            onChange={(e) => update('defect_validation_cycle_cap', parseInt(e.target.value, 10) || 5)}
                            className="border rounded px-2 py-1 w-24"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">Pass threshold (%)</label>
                        <input
                            type="number"
                            min={80}
                            max={100}
                            value={value.pass_threshold_percent ?? 98}
                            onChange={(e) => update('pass_threshold_percent', parseInt(e.target.value, 10) || 98)}
                            className="border rounded px-2 py-1 w-24"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">Proof pack soft limit (MB)</label>
                        <input
                            type="number"
                            min={10}
                            value={value.proof_pack_soft_mb ?? 50}
                            onChange={(e) => update('proof_pack_soft_mb', parseInt(e.target.value, 10) || 50)}
                            className="border rounded px-2 py-1 w-24"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">Proof pack hard limit (MB)</label>
                        <input
                            type="number"
                            min={50}
                            value={value.proof_pack_hard_mb ?? 200}
                            onChange={(e) => update('proof_pack_hard_mb', parseInt(e.target.value, 10) || 200)}
                            className="border rounded px-2 py-1 w-24"
                        />
                    </div>
                </div>
                <div className="mt-6 flex items-center gap-4">
                    <button
                        type="button"
                        onClick={handleSave}
                        disabled={saving}
                        className="bg-indigo-600 text-white px-4 py-2 rounded disabled:opacity-50"
                    >
                        {saving ? 'Saving...' : 'Save'}
                    </button>
                    {message && <span className="text-sm text-gray-600">{message}</span>}
                </div>
            </main>
        </RequireCapability>
    );
}
