"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import Text from "@/components/ui/text";
import useSWR, { mutate } from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { useState } from "react";
import SvgShield from "@/icons/shield";

interface TokenLimit {
    id: number;
    scope: string;
    enabled: boolean;
    token_budget: number;
    period_hours: number;
    name: string | null;
}

export default function TokenLimitsPage() {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [scope, setScope] = useState("global");
    const [tokenBudget, setTokenBudget] = useState("100000");
    const [periodHours, setPeriodHours] = useState("24");

    const { data: limits } = useSWR<TokenLimit[]>(
        "/api/admin/token-limits/?include_disabled=true",
        errorHandlingFetcher
    );

    const handleCreate = async () => {
        const res = await fetch("/api/admin/token-limits/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                scope,
                token_budget: parseInt(tokenBudget),
                period_hours: parseInt(periodHours),
            }),
        });
        if (res.ok) {
            setIsModalOpen(false);
            mutate("/api/admin/token-limits/?include_disabled=true");
        }
    };

    const handleToggle = async (id: number, enabled: boolean) => {
        await fetch(`/api/admin/token-limits/${id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled: !enabled }),
        });
        mutate("/api/admin/token-limits/?include_disabled=true");
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Delete this limit?")) return;
        await fetch(`/api/admin/token-limits/${id}`, { method: "DELETE" });
        mutate("/api/admin/token-limits/?include_disabled=true");
    };

    return (
        <div className="mx-auto container">
            <AdminPageTitle title="Token Rate Limits" icon={SvgShield} />

            <Text className="mb-4">
                Control token consumption with rate limits at global, group, or user level.
            </Text>

            <button
                onClick={() => setIsModalOpen(true)}
                className="mb-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
                Create Token Limit
            </button>

            {isModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white p-6 rounded-lg w-96">
                        <h2 className="text-xl font-bold mb-4">Create Token Limit</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">Scope</label>
                                <select
                                    value={scope}
                                    onChange={(e) => setScope(e.target.value)}
                                    className="w-full border rounded px-3 py-2"
                                >
                                    <option value="global">Global</option>
                                    <option value="group">Group</option>
                                    <option value="user">User</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">
                                    Token Budget
                                </label>
                                <input
                                    type="number"
                                    value={tokenBudget}
                                    onChange={(e) => setTokenBudget(e.target.value)}
                                    className="w-full border rounded px-3 py-2"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">
                                    Period (hours)
                                </label>
                                <input
                                    type="number"
                                    value={periodHours}
                                    onChange={(e) => setPeriodHours(e.target.value)}
                                    className="w-full border rounded px-3 py-2"
                                />
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={handleCreate}
                                    className="px-4 py-2 bg-blue-600 text-white rounded"
                                >
                                    Create
                                </button>
                                <button
                                    onClick={() => setIsModalOpen(false)}
                                    className="px-4 py-2 border rounded"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <table className="w-full border-collapse border">
                <thead>
                    <tr className="bg-gray-100">
                        <th className="border p-2 text-left">Name</th>
                        <th className="border p-2 text-left">Scope</th>
                        <th className="border p-2 text-left">Budget</th>
                        <th className="border p-2 text-left">Period</th>
                        <th className="border p-2 text-left">Status</th>
                        <th className="border p-2 text-left">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {limits?.map((limit) => (
                        <tr key={limit.id}>
                            <td className="border p-2">{limit.name || `Limit #${limit.id}`}</td>
                            <td className="border p-2 capitalize">{limit.scope}</td>
                            <td className="border p-2">{limit.token_budget.toLocaleString()}</td>
                            <td className="border p-2">{limit.period_hours}h</td>
                            <td className="border p-2">
                                <button
                                    onClick={() => handleToggle(limit.id, limit.enabled)}
                                    className={`px-2 py-1 rounded text-xs ${limit.enabled
                                            ? "bg-green-100 text-green-800"
                                            : "bg-gray-100"
                                        }`}
                                >
                                    {limit.enabled ? "Enabled" : "Disabled"}
                                </button>
                            </td>
                            <td className="border p-2">
                                <button
                                    onClick={() => handleDelete(limit.id)}
                                    className="px-2 py-1 text-red-600 hover:bg-red-50 rounded"
                                >
                                    Delete
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
