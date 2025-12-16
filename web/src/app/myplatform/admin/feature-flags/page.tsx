"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import Text from "@/components/ui/text";
import useSWR, { mutate } from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { useState } from "react";
import SvgSliders from "@/icons/sliders";

interface FeatureFlag {
    id: number;
    name: string;
    description: string | null;
    enabled_by_default: boolean;
    enabled_for_all: boolean;
}

export default function FeatureFlagsPage() {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [enabledByDefault, setEnabledByDefault] = useState(false);

    const { data: flags } = useSWR<FeatureFlag[]>(
        "/api/admin/feature-flags/",
        errorHandlingFetcher
    );

    const handleCreate = async () => {
        const res = await fetch("/api/admin/feature-flags/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name,
                description: description || undefined,
                enabled_by_default: enabledByDefault,
            }),
        });
        if (res.ok) {
            setIsModalOpen(false);
            setName("");
            setDescription("");
            mutate("/api/admin/feature-flags/");
        }
    };

    const handleToggle = async (flagName: string, enabledForAll: boolean) => {
        await fetch(`/api/admin/feature-flags/${flagName}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enabled_for_all: !enabledForAll }),
        });
        mutate("/api/admin/feature-flags/");
    };

    const handleDelete = async (flagName: string) => {
        if (!confirm(`Delete flag "${flagName}"?`)) return;
        await fetch(`/api/admin/feature-flags/${flagName}`, { method: "DELETE" });
        mutate("/api/admin/feature-flags/");
    };

    return (
        <div className="mx-auto container">
            <AdminPageTitle title="Feature Flags" icon={SvgSliders} />

            <Text className="mb-4">
                Control feature rollout with flags. Enable features globally or target
                specific tenants, groups, or users.
            </Text>

            <button
                onClick={() => setIsModalOpen(true)}
                className="mb-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
                Create Feature Flag
            </button>

            {isModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white p-6 rounded-lg w-96">
                        <h2 className="text-xl font-bold mb-4">Create Feature Flag</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">Flag Name</label>
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    className="w-full border rounded px-3 py-2"
                                    placeholder="e.g., new_chat_ui"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Description</label>
                                <input
                                    type="text"
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    className="w-full border rounded px-3 py-2"
                                    placeholder="What does this flag control?"
                                />
                            </div>
                            <label className="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    checked={enabledByDefault}
                                    onChange={(e) => setEnabledByDefault(e.target.checked)}
                                />
                                Enabled by default
                            </label>
                            <div className="flex gap-2">
                                <button
                                    onClick={handleCreate}
                                    disabled={!name}
                                    className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
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
                        <th className="border p-2 text-left">Flag Name</th>
                        <th className="border p-2 text-left">Description</th>
                        <th className="border p-2 text-left">Default</th>
                        <th className="border p-2 text-left">Status</th>
                        <th className="border p-2 text-left">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {flags?.map((flag) => (
                        <tr key={flag.id}>
                            <td className="border p-2 font-mono">{flag.name}</td>
                            <td className="border p-2">{flag.description || "-"}</td>
                            <td className="border p-2">{flag.enabled_by_default ? "Yes" : "No"}</td>
                            <td className="border p-2">
                                <button
                                    onClick={() => handleToggle(flag.name, flag.enabled_for_all)}
                                    className={`px-2 py-1 rounded text-xs ${flag.enabled_for_all
                                            ? "bg-green-100 text-green-800"
                                            : "bg-gray-100"
                                        }`}
                                >
                                    {flag.enabled_for_all ? "All Users" : "Targeted"}
                                </button>
                            </td>
                            <td className="border p-2">
                                <button
                                    onClick={() => handleDelete(flag.name)}
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
