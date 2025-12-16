"use client";

import { AdminPageTitle } from "@/components/admin/Title";
import Text from "@/components/ui/text";
import useSWR, { mutate } from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { useState } from "react";
import SvgUsers from "@/icons/users";

interface UserGroup {
    id: number;
    name: string;
    description: string | null;
    user_count: number;
    is_active: boolean;
}

export default function GroupsPage() {
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [isModalOpen, setIsModalOpen] = useState(false);

    const { data: groups, error } = useSWR<UserGroup[]>(
        "/api/admin/groups/",
        errorHandlingFetcher
    );

    const handleCreate = async () => {
        const res = await fetch("/api/admin/groups/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, description }),
        });
        if (res.ok) {
            setName("");
            setDescription("");
            setIsModalOpen(false);
            mutate("/api/admin/groups/");
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Delete this group?")) return;
        await fetch(`/api/admin/groups/${id}`, { method: "DELETE" });
        mutate("/api/admin/groups/");
    };

    return (
        <div className="mx-auto container">
            <AdminPageTitle title="User Groups" icon={SvgUsers} />

            <Text className="mb-4">
                Manage user groups to control access to document sets, assistants, and
                connectors.
            </Text>

            <button
                onClick={() => setIsModalOpen(true)}
                className="mb-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
                Create Group
            </button>

            {isModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white p-6 rounded-lg w-96">
                        <h2 className="text-xl font-bold mb-4">Create User Group</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">Name</label>
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    className="w-full border rounded px-3 py-2"
                                    placeholder="e.g., Engineering Team"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">
                                    Description
                                </label>
                                <input
                                    type="text"
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    className="w-full border rounded px-3 py-2"
                                    placeholder="Optional"
                                />
                            </div>
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

            {error && <div className="text-red-500 mb-4">Failed to load groups</div>}

            <table className="w-full border-collapse border">
                <thead>
                    <tr className="bg-gray-100">
                        <th className="border p-2 text-left">Name</th>
                        <th className="border p-2 text-left">Description</th>
                        <th className="border p-2 text-left">Users</th>
                        <th className="border p-2 text-left">Status</th>
                        <th className="border p-2 text-left">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {groups?.map((group) => (
                        <tr key={group.id}>
                            <td className="border p-2 font-medium">{group.name}</td>
                            <td className="border p-2">{group.description || "-"}</td>
                            <td className="border p-2">{group.user_count}</td>
                            <td className="border p-2">
                                <span
                                    className={`px-2 py-1 rounded text-xs ${group.is_active
                                            ? "bg-green-100 text-green-800"
                                            : "bg-gray-100"
                                        }`}
                                >
                                    {group.is_active ? "Active" : "Inactive"}
                                </span>
                            </td>
                            <td className="border p-2">
                                <button
                                    onClick={() => handleDelete(group.id)}
                                    className="px-2 py-1 text-red-600 hover:bg-red-50 rounded"
                                >
                                    Delete
                                </button>
                            </td>
                        </tr>
                    ))}
                    {groups?.length === 0 && (
                        <tr>
                            <td colSpan={5} className="border p-8 text-center text-gray-500">
                                No groups yet. Create your first group!
                            </td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>
    );
}
